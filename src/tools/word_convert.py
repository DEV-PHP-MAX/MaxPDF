"""Ferramentas: Word → PDF e PDF → Word.

As duas conversões usam o Microsoft Word instalado no computador,
controlado em segundo plano por automação COM (pywin32). É o único jeito
de converter com fidelidade (fontes, tabelas, imagens) sem enviar nada
para a internet. Sem o Word instalado, as ferramentas ficam
indisponíveis na interface.

Cuidados com o Word "invisível":
- Usamos uma instância própria (`DispatchEx`), sem mexer em documentos
  que o usuário tenha abertos no Word.
- Se um arquivo travar o Word (diálogo escondido, documento corrompido),
  um vigia encerra só a nossa instância após `FILE_TIMEOUT_SECONDS`,
  registra o erro e abre um Word novo para os próximos arquivos.
- O aviso "O Word converterá seu PDF em um documento editável" seria
  um diálogo invisível que trava a conversão PDF → Word; ele é
  desativado só durante a conversão e a preferência original do
  usuário é restaurada no final.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, List, Optional, Set

from ..utils.batch import BatchError, BatchResult, CancelToken
from ..utils.file_scanner import PdfFile, is_pdf_filename
from ..utils.naming import unique_path
from ..utils.output_paths import compute_output_path, has_multiple_roots
from ..utils.paths import ensure_dir

logger = logging.getLogger("maxpdf")

TO_PDF = "to_pdf"
TO_WORD = "to_word"

WORD_EXTENSIONS = (".docx", ".doc", ".docm", ".dotx", ".dot", ".rtf", ".odt")
TO_PDF_FOLDER_NAME = "PDFs_Convertidos"
TO_WORD_FOLDER_NAME = "Word_Convertidos"
FILE_TIMEOUT_SECONDS = 300

# Constantes do modelo de objetos do Word
_WD_FORMAT_DOCX = 16
_WD_EXPORT_PDF = 17
_WD_EXPORT_OPTIMIZE_PRINT = 0
_WD_EXPORT_HEADING_BOOKMARKS = 1
_WD_DO_NOT_SAVE = 0
_WD_ALERTS_NONE = 0
# Senha falsa: se o documento for protegido, o Word dá erro em vez de
# abrir um diálogo pedindo a senha (que travaria a automação).
_DUMMY_PASSWORD = "maxpdf-sem-senha"


def is_word_file(name: str) -> bool:
    lower = name.lower()
    return lower.endswith(WORD_EXTENSIONS) and not name.startswith("~$")


def _installed_word_version() -> str:
    """Versão do Word registrada (ex.: "16.0"), lida sem abrir o Word."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CurVer") as key:
            cur = winreg.QueryValueEx(key, "")[0]  # "Word.Application.16"
        return f"{int(cur.rsplit('.', 1)[-1])}.0"
    except (OSError, ValueError):
        return "16.0"


def is_word_available() -> bool:
    """True se o Microsoft Word estiver registrado para automação."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except OSError:
        return False


def _automation_word_pids() -> Set[int]:
    """PIDs de instâncias do Word abertas por automação (não as do usuário)."""
    try:
        import win32com.client

        wmi = win32com.client.GetObject("winmgmts:")
        rows = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='WINWORD.EXE'")
        return {int(r.ProcessId) for r in rows if r.CommandLine and "/automation" in r.CommandLine.lower()}
    except Exception:  # noqa: BLE001
        return set()


def _kill(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F"],
        capture_output=True,
        timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


class _WordSession:
    """Uma instância invisível do Word, com o PID conhecido para poder encerrá-la."""

    def __init__(self) -> None:
        import win32com.client

        before = _automation_word_pids()
        self.app = win32com.client.DispatchEx("Word.Application")
        self.app.Visible = False
        self.app.DisplayAlerts = _WD_ALERTS_NONE
        self.app.ScreenUpdating = False
        new = _automation_word_pids() - before
        self.pid: Optional[int] = next(iter(new)) if len(new) == 1 else None
        self.version: str = str(self.app.Version)

    def open(self, path: Path):
        return self.app.Documents.Open(
            str(path),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            PasswordDocument=_DUMMY_PASSWORD,
            Visible=False,
            NoEncodingDialog=True,
        )

    def quit(self) -> None:
        try:
            self.app.Quit(_WD_DO_NOT_SAVE)
        except Exception:  # noqa: BLE001
            self.kill()

    def kill(self) -> None:
        if self.pid is not None:
            _kill(self.pid)


@contextmanager
def _pdf_warning_disabled(word_version: str):
    """Desliga o aviso de conversão de PDF do Word e depois restaura."""
    import winreg

    key_path = rf"Software\Microsoft\Office\{word_version}\Word\Options"
    name = "DisableConvertPdfWarning"
    previous = None
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError:
        yield
        return
    try:
        try:
            previous = winreg.QueryValueEx(key, name)
        except OSError:
            previous = None
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1)
        yield
    finally:
        try:
            if previous is None:
                winreg.DeleteValue(key, name)
            else:
                winreg.SetValueEx(key, name, 0, previous[1], previous[0])
        except OSError:
            pass
        winreg.CloseKey(key)


def _open_dialog_text(pid: Optional[int]) -> Optional[str]:
    """Texto de um diálogo visível aberto pelo Word `pid`, se houver.

    Com o Word invisível, qualquer diálogo (senha, arquivo danificado,
    "este arquivo causou um erro grave"...) trava a automação para
    sempre. Detectá-lo permite encerrar na hora e mostrar a mensagem.
    """
    if pid is None:
        return None
    try:
        import win32gui
        import win32process
    except ImportError:
        return None
    found: List[str] = []

    def collect_child(child, texts):
        if win32gui.GetClassName(child) == "Static":
            text = win32gui.GetWindowText(child).strip()
            if text:
                texts.append(text)
        return True

    def check_top(hwnd, _):
        if (
            win32gui.IsWindowVisible(hwnd)
            and win32gui.GetClassName(hwnd) == "#32770"
            and win32process.GetWindowThreadProcessId(hwnd)[1] == pid
        ):
            texts: List[str] = []
            try:
                win32gui.EnumChildWindows(hwnd, collect_child, texts)
            except Exception:  # noqa: BLE001
                pass
            found.append(" ".join(texts) or win32gui.GetWindowText(hwnd) or "O Word abriu um aviso.")
        return True

    try:
        win32gui.EnumWindows(check_top, None)
    except Exception:  # noqa: BLE001
        return None
    return found[0] if found else None


@contextmanager
def _forget_disabled_items(word_version: str):
    """Remove os registros de "arquivo problemático" criados nesta conversão.

    Quando o Word é encerrado à força no meio de um arquivo, ele o anota
    em Resiliency\\DisabledItems e, na próxima vez, pergunta se deve
    abri-lo. Só são apagadas as entradas novas, criadas durante o lote.
    """
    import winreg

    key_path = rf"Software\Microsoft\Office\{word_version}\Word\Resiliency\DisabledItems"

    def names() -> Set[str]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                result, i = set(), 0
                while True:
                    try:
                        result.add(winreg.EnumValue(key, i)[0])
                    except OSError:
                        return result
                    i += 1
        except OSError:
            return set()

    before = names()
    try:
        yield
    finally:
        new = names() - before
        if new:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    for name in new:
                        winreg.DeleteValue(key, name)
            except OSError:
                pass


def _friendly_error(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "senha" in lowered or "password" in lowered:
        return "Documento protegido por senha."
    if "rpc" in lowered or "disconnected" in lowered or "desconectado" in lowered:
        return "O Word parou de responder ao converter este arquivo."
    # Erros COM do pywin32 trazem a mensagem do Word no meio de uma tupla;
    # a primeira linha basta (o resto são sugestões genéricas do Word).
    info = getattr(exc, "excepinfo", None)
    if info and len(info) > 2 and info[2]:
        text = str(info[2])
    return text.strip().splitlines()[0].strip() if text.strip() else "Erro desconhecido do Word."


class WordConvertRunner(threading.Thread):
    def __init__(
        self,
        files: List[PdfFile],
        dest_root: Path,
        direction: str,
        keep_structure: bool,
        on_progress: Callable[[int, int, str], None],
        on_done: Callable[[BatchResult], None],
    ) -> None:
        super().__init__(daemon=True)
        self._files = files
        self._dest_root = dest_root
        self._direction = direction
        self._keep_structure = keep_structure
        self._on_progress = on_progress
        self._on_done = on_done
        self._token = CancelToken()
        self._session: Optional[_WordSession] = None
        self._current_started: Optional[float] = None
        self._timed_out = False
        self._dialog_text: Optional[str] = None

    def cancel(self) -> None:
        self._token.cancel()
        # Um arquivo grande pode levar minutos; encerra o Word para parar já.
        session = self._session
        if session is not None and self._current_started is not None:
            session.kill()

    def _watchdog(self) -> None:
        while self.is_alive():
            started, session = self._current_started, self._session
            if started and session:
                dialog = _open_dialog_text(session.pid)
                if dialog:
                    self._dialog_text = dialog
                    session.kill()
                    self._current_started = None
                elif time.monotonic() - started > FILE_TIMEOUT_SECONDS:
                    self._timed_out = True
                    session.kill()
                    self._current_started = None
            time.sleep(1)

    def _new_session(self) -> _WordSession:
        self._session = _WordSession()
        return self._session

    def _convert_one(self, session: _WordSession, pdf_file: PdfFile, multiple_roots: bool) -> None:
        suffix = ".pdf" if self._direction == TO_PDF else ".docx"
        out = compute_output_path(pdf_file, self._dest_root, self._keep_structure, multiple_roots)
        out = out.with_suffix(suffix)
        ensure_dir(out.parent)
        out = unique_path(out)
        doc = session.open(pdf_file.path)
        try:
            if self._direction == TO_PDF:
                doc.ExportAsFixedFormat(
                    OutputFileName=str(out),
                    ExportFormat=_WD_EXPORT_PDF,
                    OpenAfterExport=False,
                    OptimizeFor=_WD_EXPORT_OPTIMIZE_PRINT,
                    CreateBookmarks=_WD_EXPORT_HEADING_BOOKMARKS,
                )
            else:
                doc.SaveAs2(str(out), FileFormat=_WD_FORMAT_DOCX)
        finally:
            try:
                doc.Close(_WD_DO_NOT_SAVE)
            except Exception:  # noqa: BLE001
                pass

    def run(self) -> None:
        import pythoncom

        start = time.monotonic()
        total = len(self._files)
        result = BatchResult(total=total, output_dir=str(self._dest_root))
        multiple_roots = has_multiple_roots(self._files)
        pythoncom.CoInitialize()
        threading.Thread(target=self._watchdog, daemon=True).start()
        # O Word só lê essa preferência ao iniciar, então ela é ajustada antes.
        version = _installed_word_version()
        warning_ctx = _pdf_warning_disabled(version) if self._direction == TO_WORD else _null_ctx()
        try:
            with _forget_disabled_items(version), warning_ctx:
                try:
                    self._convert_all(result, multiple_roots)
                finally:
                    # Fecha o Word antes de restaurar a preferência: ele pode
                    # regravar as opções no registro ao sair.
                    if self._session is not None:
                        self._session.quit()
                    self._session = None
        finally:
            pythoncom.CoUninitialize()
            result.elapsed_seconds = time.monotonic() - start
            self._on_done(result)

    def _convert_all(self, result: BatchResult, multiple_roots: bool) -> None:
        total = len(self._files)
        try:
            session = self._new_session()
        except Exception as exc:  # noqa: BLE001
            logger.error("Não foi possível iniciar o Word: %s", exc)
            result.errors.append(
                BatchError(item_label="Microsoft Word", message=f"Não foi possível abrir o Word: {_friendly_error(exc)}")
            )
            return
        for index, pdf_file in enumerate(self._files, start=1):
            if self._token.is_cancelled():
                result.cancelled = True
                break
            self._on_progress(index, total, pdf_file.display_path)
            self._timed_out = False
            self._dialog_text = None
            self._current_started = time.monotonic()
            try:
                self._convert_one(session, pdf_file, multiple_roots)
                result.succeeded += 1
            except Exception as exc:  # noqa: BLE001
                if self._token.is_cancelled():
                    result.cancelled = True
                    break
                if self._dialog_text:
                    message = f"O Word pediu confirmação e a conversão foi interrompida: {self._dialog_text}"
                elif self._timed_out:
                    message = "Tempo esgotado: o Word não terminou de converter este arquivo."
                else:
                    message = _friendly_error(exc)
                result.errors.append(BatchError(item_label=pdf_file.display_path, message=message))
                if self._dialog_text or self._timed_out or not _session_alive(session):
                    session.kill()
                    session = self._new_session()
            finally:
                self._current_started = None

def _session_alive(session: _WordSession) -> bool:
    try:
        _ = session.app.Documents.Count
        return True
    except Exception:  # noqa: BLE001
        return False


@contextmanager
def _null_ctx():
    yield


def accepts_input(direction: str, name: str) -> bool:
    return is_word_file(name) if direction == TO_PDF else is_pdf_filename(name)


def run_word_convert(
    files: List[PdfFile],
    dest_root: Path,
    direction: str,
    keep_structure: bool,
    on_progress,
    on_done,
) -> WordConvertRunner:
    ensure_dir(dest_root)
    runner = WordConvertRunner(files, dest_root, direction, keep_structure, on_progress, on_done)
    runner.start()
    return runner
