"""Ponte entre a interface web (HTML/JS) e as ferramentas de PDF.

Cada método público desta classe fica disponível no JavaScript como
`window.pywebview.api.<metodo>(...)`. Os métodos rodam em threads do
pywebview, então podem abrir diálogos e disparar os runners de
`tools/` diretamente. Eventos assíncronos (progresso, fim de busca,
fim de processamento) são enviados ao JS com `window.evaluate_js`.

Atributos internos começam com `_` para que o pywebview não tente
expô-los ao JavaScript.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import webview

from .. import version
from ..tools.images_to_pdf import DEFAULT_OUTPUT_NAME as IMAGES_OUTPUT_NAME
from ..tools.images_to_pdf import SUPPORTED_EXTENSIONS, is_supported_image, run_images_to_pdf
from ..tools.merge import DEFAULT_OUTPUT_NAME as MERGE_OUTPUT_NAME
from ..tools.merge import run_merge
from ..tools.reverse import DEFAULT_OUTPUT_FOLDER_NAME as REVERSE_FOLDER
from ..tools.reverse import run_reverse_batch
from ..tools.rotate import DEFAULT_OUTPUT_FOLDER_NAME as ROTATE_FOLDER
from ..tools.rotate import VALID_ANGLES, run_rotate_batch
from ..tools.split import SplitMode, run_split
from ..tools.word_convert import (
    TO_PDF,
    TO_PDF_FOLDER_NAME,
    TO_WORD,
    TO_WORD_FOLDER_NAME,
    WORD_EXTENSIONS,
    is_word_available,
    is_word_file,
    run_word_convert,
)
from ..utils.batch import BatchResult
from ..utils.file_scanner import FileQueue, FolderScanner, PdfFile, is_pdf_filename
from ..utils.helpers import bytes_to_human, format_duration, open_folder
from ..utils.naming import unique_dir
from ..utils.natural_sort import natural_sort_key
from ..utils.page_ranges import parse_page_ranges

logger = logging.getLogger("maxpdf")

QUEUE_TOOLS = ("reverse", "merge", "rotate", "images", "word2pdf", "pdf2word")
ALL_TOOLS = QUEUE_TOOLS + ("split",)
# Ferramentas que aceitam "Selecionar pasta" (busca recursiva)
FOLDER_TOOLS = ("reverse", "merge", "rotate", "word2pdf", "pdf2word")
WORD_TOOLS = {"word2pdf": TO_PDF, "pdf2word": TO_WORD}

SORT_MODES = ("name_asc", "name_desc", "path", "modified", "custom")

PDF_FILE_TYPES = ("Arquivos PDF (*.pdf;*.PDF)", "Todos os arquivos (*.*)")
IMAGE_FILE_TYPES = (
    "Imagens (" + ";".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS) + ")",
    "Todos os arquivos (*.*)",
)
WORD_FILE_TYPES = (
    "Documentos do Word (" + ";".join(f"*{ext}" for ext in WORD_EXTENSIONS) + ")",
    "Todos os arquivos (*.*)",
)


def _matcher(tool: str):
    """Filtro de nome de arquivo aceito por cada ferramenta."""
    if tool == "images":
        return lambda name: is_supported_image(Path(name))
    if tool == "word2pdf":
        return is_word_file
    return is_pdf_filename


def _file_types(tool: str):
    return {"images": IMAGE_FILE_TYPES, "word2pdf": WORD_FILE_TYPES}.get(tool, PDF_FILE_TYPES)

# Intervalo mínimo entre eventos de progresso enviados à interface,
# para não inundar o WebView em lotes com milhares de arquivos.
_PROGRESS_INTERVAL = 0.05


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


class Api:
    def __init__(self) -> None:
        self._window: Optional[webview.Window] = None
        self._queues: Dict[str, FileQueue] = {key: FileQueue() for key in QUEUE_TOOLS}
        self._sizes: Dict[str, int] = {}
        self._sort_mode = "name_asc"
        self._split_file: Optional[Path] = None
        self._runners: Dict[str, Any] = {}
        self._scanners: Dict[str, FolderScanner] = {}
        self._last_dir: str = ""
        self._active_tool = "reverse"
        self._lock = threading.RLock()

    # -- infraestrutura -----------------------------------------------
    def _attach(self, window: webview.Window) -> None:
        self._window = window

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        if self._window is None:
            return
        data = json.dumps({"event": event, "payload": payload}, ensure_ascii=False)
        try:
            self._window.evaluate_js(f"window.maxpdf && window.maxpdf.receive({data})")
        except Exception:  # noqa: BLE001 - janela fechando
            logger.debug("Falha ao enviar evento %s para a interface", event)

    def _dialog(self, kind: int, *, multiple: bool = False, file_types=(), save_name: str = ""):
        if self._window is None:
            return None
        result = self._window.create_file_dialog(
            kind,
            directory=self._last_dir,
            allow_multiple=multiple,
            save_filename=save_name,
            file_types=file_types,
        )
        if not result:
            return None
        if isinstance(result, str):
            result = [result]
        paths = [Path(p) for p in result]
        self._last_dir = str(paths[0] if kind == webview.FileDialog.FOLDER else paths[0].parent)
        return paths

    def _item_json(self, pdf_file: PdfFile) -> Dict[str, Any]:
        key = str(pdf_file.path)
        size = self._sizes.get(key)
        if size is None:
            size = _safe_size(pdf_file.path)
            self._sizes[key] = size
        return {
            "name": pdf_file.display_name,
            "path": pdf_file.display_path,
            "full": key,
            "size": bytes_to_human(size),
            "root": pdf_file.root_label,
        }

    def _state(self, tool: str) -> Dict[str, Any]:
        with self._lock:
            state: Dict[str, Any] = {"tool": tool, "running": tool in self._runners}
            if tool == "split":
                f = self._split_file
                state["file"] = (
                    {"name": f.name, "full": str(f), "size": bytes_to_human(_safe_size(f))} if f else None
                )
            else:
                state["items"] = [self._item_json(f) for f in self._queues[tool].items]
                if tool == "merge":
                    state["sort"] = self._sort_mode
            return state

    def _push_state(self, tool: str) -> None:
        self._emit("state", self._state(tool))

    def _apply_sort(self) -> None:
        queue = self._queues["merge"]
        items = queue.items
        mode = self._sort_mode
        if mode == "name_asc":
            items.sort(key=lambda f: natural_sort_key(f.path.name))
        elif mode == "name_desc":
            items.sort(key=lambda f: natural_sort_key(f.path.name), reverse=True)
        elif mode == "path":
            items.sort(key=lambda f: natural_sort_key(str(f.path)))
        elif mode == "modified":
            items.sort(key=lambda f: _safe_mtime(f.path))
        queue.replace_all(items)

    def _add_paths(self, tool: str, paths: List[Path]) -> Dict[str, int]:
        """Adiciona arquivos soltos à fila da ferramenta. Retorna contagens."""
        with self._lock:
            accepts = _matcher(tool)
            valid = [p for p in paths if accepts(p.name)]
            skipped = len(paths) - len(valid)
            added = self._queues[tool].add_many([PdfFile(path=p, root=None) for p in valid])
            if tool == "merge" and self._sort_mode != "custom":
                self._apply_sort()
            return {"added": added, "skipped": skipped, "duplicates": len(valid) - added}

    def _validate(self, tool: str) -> str:
        if tool not in ALL_TOOLS:
            raise ValueError(f"Ferramenta desconhecida: {tool}")
        return tool

    # -- chamadas vindas do JavaScript ------------------------------------
    def get_info(self) -> Dict[str, Any]:
        return {
            "name": version.APP_NAME,
            "subtitle": version.APP_SUBTITLE,
            "version": version.APP_VERSION,
            "wordAvailable": is_word_available(),
        }

    def get_state(self, tool: str) -> Dict[str, Any]:
        return self._state(self._validate(tool))

    def set_active(self, tool: str) -> None:
        self._active_tool = self._validate(tool)

    def pick_files(self, tool: str) -> Dict[str, Any]:
        tool = self._validate(tool)
        if tool == "split":
            paths = self._dialog(webview.FileDialog.OPEN, file_types=PDF_FILE_TYPES)
            if paths:
                self._split_file = paths[0]
            return {"state": self._state(tool), "added": 1 if paths else 0}
        paths = self._dialog(webview.FileDialog.OPEN, multiple=True, file_types=_file_types(tool))
        counts = self._add_paths(tool, paths or [])
        return {"state": self._state(tool), **counts}

    def pick_folder(self, tool: str) -> bool:
        tool = self._validate(tool)
        if tool not in FOLDER_TOOLS:
            return False
        paths = self._dialog(webview.FileDialog.FOLDER)
        if not paths:
            return False
        folder = paths[0]

        def progress(count: int) -> None:
            self._emit("scan", {"tool": tool, "count": count, "done": False})

        def done(files: List[PdfFile]) -> None:
            with self._lock:
                added = self._queues[tool].add_many(files)
                if tool == "merge" and self._sort_mode != "custom":
                    self._apply_sort()
                self._scanners.pop(tool, None)
            self._emit("scan", {"tool": tool, "count": len(files), "added": added, "done": True})
            self._push_state(tool)

        def on_error(exc: Exception) -> None:
            self._scanners.pop(tool, None)
            self._emit("scan", {"tool": tool, "error": str(exc), "done": True})

        scanner = FolderScanner([folder], progress, done, on_error=on_error, matcher=_matcher(tool))
        self._scanners[tool] = scanner
        self._emit("scan", {"tool": tool, "count": 0, "done": False, "folder": folder.name})
        scanner.start()
        return True

    def remove(self, tool: str, indices: List[int]) -> Dict[str, Any]:
        tool = self._validate(tool)
        with self._lock:
            if tool == "split":
                self._split_file = None
            else:
                self._queues[tool].remove_indices([int(i) for i in indices])
        return self._state(tool)

    def clear(self, tool: str) -> Dict[str, Any]:
        tool = self._validate(tool)
        with self._lock:
            if tool == "split":
                self._split_file = None
            else:
                self._queues[tool].clear()
        return self._state(tool)

    def move(self, tool: str, old_index: int, new_index: int) -> Dict[str, Any]:
        tool = self._validate(tool)
        with self._lock:
            self._queues[tool].move_to(int(old_index), int(new_index))
            if tool == "merge":
                self._sort_mode = "custom"
        return self._state(tool)

    def set_sort(self, mode: str) -> Dict[str, Any]:
        if mode not in SORT_MODES:
            raise ValueError(f"Ordenação inválida: {mode}")
        with self._lock:
            self._sort_mode = mode
            self._apply_sort()
        return self._state("merge")

    def validate_pages(self, spec: str) -> Dict[str, Any]:
        """Valida a sintaxe de um intervalo sem conhecer o total de páginas."""
        try:
            pages = parse_page_ranges(spec, 10**9)
            return {"ok": True, "count": len(pages)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": str(exc)}

    def open_folder(self, path: str) -> None:
        open_folder(Path(path))

    def cancel(self, tool: str) -> None:
        runner = self._runners.get(self._validate(tool))
        if runner is not None:
            runner.cancel()

    def run(self, tool: str, options: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._validate(tool)
        options = options or {}
        if tool in self._runners:
            return {"started": False, "message": "Já existe um processamento em andamento."}

        with self._lock:
            files = list(self._queues[tool].items) if tool in QUEUE_TOOLS else []
        if tool in QUEUE_TOOLS and not files:
            return {"started": False, "message": "Adicione pelo menos um arquivo."}
        if tool == "split" and self._split_file is None:
            return {"started": False, "message": "Selecione um PDF."}
        if tool in WORD_TOOLS and not is_word_available():
            return {"started": False, "message": "Esta conversão precisa do Microsoft Word instalado."}

        pages_spec = (options.get("pages") or "").strip() or None
        if options.get("pagesMode") == "specific" and not pages_spec:
            return {"started": False, "message": "Informe as páginas ou intervalos (ex.: 1-3,5,8-10)."}

        if tool in ("merge", "images"):
            default_name = MERGE_OUTPUT_NAME if tool == "merge" else IMAGES_OUTPUT_NAME
            chosen = self._dialog(
                webview.FileDialog.SAVE, save_name=default_name, file_types=("Arquivo PDF (*.pdf)",)
            )
            if not chosen:
                return {"started": False, "cancelled": True}
            output_path = chosen[0]
            if output_path.suffix.lower() != ".pdf":
                output_path = output_path.with_suffix(".pdf")
        else:
            chosen = self._dialog(webview.FileDialog.FOLDER)
            if not chosen:
                return {"started": False, "cancelled": True}
            destination = chosen[0]

        start_time = time.monotonic()
        last_emit = [0.0]

        def on_progress(current: int, total: int, label: str) -> None:
            now = time.monotonic()
            if current not in (1, total) and now - last_emit[0] < _PROGRESS_INTERVAL:
                return
            last_emit[0] = now
            self._emit(
                "progress",
                {
                    "tool": tool,
                    "current": current,
                    "total": total,
                    "label": label,
                    "elapsed": now - start_time,
                },
            )

        noun = {"split": "página", "images": "imagem", "word2pdf": "documento"}.get(tool, "arquivo")

        def on_done(result: BatchResult) -> None:
            self._runners.pop(tool, None)
            self._emit("done", {"tool": tool, "noun": noun, **self._result_json(result)})
            self._push_state(tool)

        keep_structure = bool(options.get("keepStructure", True))
        if tool == "reverse":
            runner = run_reverse_batch(
                files, unique_dir(destination / REVERSE_FOLDER), keep_structure, on_progress, on_done
            )
        elif tool == "rotate":
            angle = int(options.get("angle", 90))
            if angle not in VALID_ANGLES:
                return {"started": False, "message": f"Ângulo inválido: {angle}"}
            spec = pages_spec if options.get("pagesMode") == "specific" else None
            runner = run_rotate_batch(
                files,
                unique_dir(destination / ROTATE_FOLDER),
                angle,
                spec,
                keep_structure,
                on_progress,
                on_done,
            )
        elif tool in WORD_TOOLS:
            direction = WORD_TOOLS[tool]
            folder_name = TO_PDF_FOLDER_NAME if direction == TO_PDF else TO_WORD_FOLDER_NAME
            runner = run_word_convert(
                files, unique_dir(destination / folder_name), direction, keep_structure, on_progress, on_done
            )
        elif tool == "merge":
            runner = run_merge(files, output_path, on_progress, on_done)
        elif tool == "images":
            runner = run_images_to_pdf([f.path for f in files], output_path, on_progress, on_done)
        else:
            mode = SplitMode.RANGES if options.get("pagesMode") == "specific" else SplitMode.ONE_PAGE_PER_FILE
            runner = run_split(
                self._split_file,
                destination,
                mode,
                pages_spec if mode == SplitMode.RANGES else None,
                on_progress,
                on_done,
            )

        self._runners[tool] = runner
        logger.info("Ferramenta %s iniciada com %d item(ns)", tool, len(files) or 1)
        return {"started": True}

    @staticmethod
    def _result_json(result: BatchResult) -> Dict[str, Any]:
        return {
            "total": result.total,
            "succeeded": result.succeeded,
            "failed": result.failed,
            "processed": result.processed,
            "cancelled": result.cancelled,
            "elapsed": format_duration(result.elapsed_seconds),
            "outputDir": result.output_dir,
            "errors": [{"item": e.item_label, "message": e.message} for e in result.errors],
        }

    # -- arrastar e soltar (chamado pelo app.py) ---------------------------
    def _handle_drop(self, paths: List[Path]) -> None:
        tool = self._active_tool
        if tool in self._runners:
            return
        folders = [p for p in paths if p.is_dir()]
        files = [p for p in paths if p.is_file()]
        if tool == "split":
            pdfs = [p for p in files if is_pdf_filename(p.name)]
            if pdfs:
                self._split_file = pdfs[0]
                self._emit("dropped", {"tool": tool, "added": 1, "skipped": len(paths) - 1})
                self._push_state(tool)
            else:
                self._emit("dropped", {"tool": tool, "added": 0, "skipped": len(paths)})
            return

        counts = self._add_paths(tool, files) if files else {"added": 0, "skipped": 0, "duplicates": 0}
        if folders and tool not in FOLDER_TOOLS:
            counts["skipped"] += len(folders)
        self._emit("dropped", {"tool": tool, **counts})
        self._push_state(tool)

        if folders and tool in FOLDER_TOOLS:

            def progress(count: int) -> None:
                self._emit("scan", {"tool": tool, "count": count, "done": False})

            def done(found: List[PdfFile]) -> None:
                with self._lock:
                    added = self._queues[tool].add_many(found)
                    if tool == "merge" and self._sort_mode != "custom":
                        self._apply_sort()
                self._emit("scan", {"tool": tool, "count": len(found), "added": added, "done": True})
                self._push_state(tool)

            self._emit("scan", {"tool": tool, "count": 0, "done": False})
            FolderScanner(folders, progress, done, matcher=_matcher(tool)).start()
