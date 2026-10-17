"""Busca recursiva de PDFs em pastas e gerenciamento de filas de arquivos.

Este módulo é usado por todas as ferramentas que trabalham com múltiplos
PDFs. Ele não depende da interface gráfica: os componentes de UI é que
decidem como/quando disparar a busca em uma thread separada e como
atualizar os widgets com segurança (via `after()`).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from .paths import normalize_path, relative_display_path, root_folder_name

_TEMP_PREFIXES = ("~$",)
_TEMP_SUFFIXES = (".tmp",)


@dataclass(frozen=True)
class PdfFile:
    """Representa um PDF na fila de uma ferramenta.

    `root` é a pasta raiz selecionada pelo usuário que originou este
    arquivo (usada para reconstruir o caminho relativo e a estrutura de
    subpastas no destino). É None quando o arquivo foi adicionado
    manualmente (não através de "Selecionar pasta").
    """

    path: Path
    root: Optional[Path] = None

    @property
    def display_name(self) -> str:
        return self.path.name

    @property
    def display_path(self) -> str:
        return relative_display_path(self.path, self.root)

    @property
    def root_label(self) -> Optional[str]:
        return root_folder_name(self.root) if self.root is not None else None


def is_pdf_filename(name: str) -> bool:
    """True se `name` parece um arquivo PDF válido (case-insensitive)."""
    lower = name.lower()
    if not lower.endswith(".pdf"):
        return False
    if name.startswith(_TEMP_PREFIXES):
        return False
    if any(lower.endswith(suf) for suf in _TEMP_SUFFIXES):
        return False
    return True


def find_pdfs_in_folder(
    folder: Path,
    recursive: bool = True,
    matcher: Callable[[str], bool] = is_pdf_filename,
):
    """Gera Paths de todos os PDFs encontrados em `folder`.

    `matcher` decide quais nomes de arquivo entram (padrão: PDFs); as
    ferramentas de Word passam o próprio filtro.

    Continua funcionando mesmo se uma subpasta apresentar erro de
    permissão (o erro é simplesmente ignorado para aquela subpasta).
    """

    def _on_error(_exc: OSError) -> None:
        # Pasta inacessível: ignora e continua a busca nas demais.
        return None

    if not recursive:
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.is_file() and matcher(entry.name):
                        yield Path(entry.path)
        except OSError:
            return
        return

    for dirpath, _dirnames, filenames in os.walk(folder, onerror=_on_error):
        for filename in filenames:
            if matcher(filename):
                yield Path(dirpath) / filename


class FolderScanner(threading.Thread):
    """Executa a busca recursiva de PDFs em segundo plano.

    Os callbacks são invocados a partir da thread de busca; o chamador
    (camada de UI) é responsável por agendá-los com segurança na thread
    principal (por exemplo, envolvendo-os em `widget.after(0, ...)`).
    """

    def __init__(
        self,
        folders: List[Path],
        on_progress: Callable[[int], None],
        on_done: Callable[[List[PdfFile]], None],
        on_error: Optional[Callable[[Exception], None]] = None,
        recursive: bool = True,
        progress_every: int = 20,
        matcher: Callable[[str], bool] = is_pdf_filename,
    ) -> None:
        super().__init__(daemon=True)
        self._folders = folders
        self._on_progress = on_progress
        self._on_done = on_done
        self._on_error = on_error
        self._recursive = recursive
        self._progress_every = max(1, progress_every)
        self._cancel = threading.Event()
        self._matcher = matcher

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            found: List[PdfFile] = []
            for folder in self._folders:
                if self._cancel.is_set():
                    break
                for path in find_pdfs_in_folder(folder, recursive=self._recursive, matcher=self._matcher):
                    if self._cancel.is_set():
                        break
                    found.append(PdfFile(path=path, root=folder))
                    if len(found) % self._progress_every == 0:
                        self._on_progress(len(found))
            if not self._cancel.is_set():
                self._on_progress(len(found))
                self._on_done(found)
        except Exception as exc:  # pragma: no cover - proteção defensiva
            if self._on_error is not None:
                self._on_error(exc)
            else:
                raise


class FileQueue:
    """Fila de arquivos de uma ferramenta, com deduplicação automática.

    Reaproveitada por todas as ferramentas que aceitam múltiplos PDFs
    (Inverter, Juntar, Girar). Mantém a ordem de inserção e nunca
    duplica um mesmo arquivo (comparado pelo caminho absoluto
    normalizado), mesmo que ele tenha sido adicionado manualmente e
    depois novamente através da seleção de uma pasta (ou vice-versa).
    """

    def __init__(self) -> None:
        self._items: List[PdfFile] = []
        self._known: set[str] = set()

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    @property
    def items(self) -> List[PdfFile]:
        return list(self._items)

    def add(self, pdf_file: PdfFile) -> bool:
        """Adiciona um único arquivo. Retorna False se já existia (ignorado)."""
        key = normalize_path(pdf_file.path)
        if key in self._known:
            return False
        self._known.add(key)
        self._items.append(pdf_file)
        return True

    def add_many(self, pdf_files: List[PdfFile]) -> int:
        """Adiciona vários arquivos, retornando quantos foram efetivamente
        incluídos (descontando duplicados)."""
        added = 0
        for pdf_file in pdf_files:
            if self.add(pdf_file):
                added += 1
        return added

    def add_manual_files(self, paths: List[Path]) -> int:
        return self.add_many([PdfFile(path=Path(p), root=None) for p in paths])

    def remove_at(self, index: int) -> None:
        if 0 <= index < len(self._items):
            removed = self._items.pop(index)
            self._known.discard(normalize_path(removed.path))

    def remove_indices(self, indices: List[int]) -> None:
        for index in sorted(set(indices), reverse=True):
            self.remove_at(index)

    def clear(self) -> None:
        self._items.clear()
        self._known.clear()

    def replace_all(self, items: List[PdfFile]) -> None:
        """Substitui a fila inteira por `items` (mesmo conjunto, nova
        ordem). Usado pelas opções de ordenação da ferramenta Juntar
        PDFs. Não deve ser usado para adicionar arquivos novos."""
        self._items = list(items)
        self._known = {normalize_path(item.path) for item in self._items}

    def move_to(self, old_index: int, new_index: int) -> int:
        """Move o item de `old_index` para `new_index`, deslocando os
        demais. Usado tanto pelos botões SUBIR/DESCER (delta de 1)
        quanto pelo drag-and-drop na lista. Retorna o índice final."""
        if not (0 <= old_index < len(self._items)):
            return old_index
        new_index = max(0, min(new_index, len(self._items) - 1))
        if new_index == old_index:
            return old_index
        item = self._items.pop(old_index)
        self._items.insert(new_index, item)
        return new_index
