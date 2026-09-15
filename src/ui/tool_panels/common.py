"""Peças reutilizáveis entre os painéis de ferramenta.

Evita duplicar lógica de seleção de arquivos/pastas, busca recursiva
assíncrona, estilo de cards e botões entre as cinco ferramentas.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional, Sequence, Tuple

import customtkinter as ctk

from ...utils.file_scanner import FolderScanner, PdfFile
from .. import theme
from ..buttons import danger_button, primary_button, secondary_button, set_button_enabled

__all__ = [
    "danger_button",
    "primary_button",
    "secondary_button",
    "set_button_enabled",
    "get_last_directory",
    "set_last_directory",
    "card",
    "section_title",
    "section_description",
    "PDF_FILETYPES",
    "IMAGE_FILETYPES",
    "FilePickerRow",
    "scan_folder_async",
    "pick_destination_folder",
    "pick_save_file",
    "bounce_to_ui",
]

# Lembra o último diretório usado durante a sessão (apenas em memória;
# não é persistido em disco, conforme item 54 do escopo).
_last_directory: Optional[str] = None


def get_last_directory() -> Optional[str]:
    return _last_directory


def set_last_directory(path: Path) -> None:
    global _last_directory
    _last_directory = str(path)


def card(master, **kwargs) -> ctk.CTkFrame:
    kwargs.setdefault("fg_color", theme.COLOR_CARD)
    kwargs.setdefault("corner_radius", 12)
    return ctk.CTkFrame(master, **kwargs)


def section_title(master, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master, text=text, font=theme.font(18, "bold"), text_color=theme.COLOR_TEXT_PRIMARY, anchor="w"
    )


def section_description(master, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        master,
        text=text,
        font=theme.font(12),
        text_color=theme.COLOR_TEXT_SECONDARY,
        anchor="w",
        justify="left",
        wraplength=780,
    )


PDF_FILETYPES: Tuple[Tuple[str, str], ...] = (("Arquivos PDF", "*.pdf *.PDF"), ("Todos os arquivos", "*.*"))
IMAGE_FILETYPES: Tuple[Tuple[str, str], ...] = (
    ("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"),
    ("Todos os arquivos", "*.*"),
)


class FilePickerRow(ctk.CTkFrame):
    """Linha com botões de seleção de arquivos/pasta e um status de busca."""

    def __init__(
        self,
        master,
        on_files_selected: Callable[[List[Path]], None],
        on_folder_selected: Optional[Callable[[Path], None]] = None,
        file_button_text: str = "+ SELECIONAR PDFs",
        filetypes: Sequence[Tuple[str, str]] = PDF_FILETYPES,
        allow_folder: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_files_selected = on_files_selected
        self._on_folder_selected = on_folder_selected
        self._filetypes = list(filetypes)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        primary_button(row, file_button_text, self._pick_files, width=210).pack(
            side="left", padx=(0, 10)
        )
        if allow_folder and on_folder_selected is not None:
            secondary_button(row, "📁 SELECIONAR PASTA", self._pick_folder, width=210).pack(side="left")

        self._status_label = ctk.CTkLabel(
            self, text="", font=theme.font(12), text_color=theme.COLOR_TEXT_SECONDARY, anchor="w"
        )
        self._status_label.pack(fill="x", pady=(8, 0))

    def set_status(self, text: str) -> None:
        self._status_label.configure(text=text)

    def _pick_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecionar arquivos", filetypes=self._filetypes, initialdir=get_last_directory()
        )
        if paths:
            set_last_directory(Path(paths[0]).parent)
            self._on_files_selected([Path(p) for p in paths])

    def _pick_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecionar pasta", initialdir=get_last_directory())
        if folder and self._on_folder_selected:
            set_last_directory(Path(folder))
            self._on_folder_selected(Path(folder))


def scan_folder_async(
    widget: ctk.CTkBaseClass,
    folders: List[Path],
    status_row: FilePickerRow,
    on_found: Callable[[List[PdfFile]], None],
) -> FolderScanner:
    """Dispara a busca recursiva de PDFs em segundo plano, atualizando o
    `status_row` e, ao final, entregando os arquivos encontrados via
    `on_found` — tudo agendado com segurança na thread principal.
    """
    status_row.set_status("Procurando PDFs...")

    def progress(count: int) -> None:
        widget.after(0, lambda: status_row.set_status(f"Procurando PDFs... ({count} encontrados)"))

    def done(files: List[PdfFile]) -> None:
        def _apply() -> None:
            n = len(files)
            plural = "s" if n != 1 else ""
            status_row.set_status(f"{n} PDF{plural} encontrado{plural}.")
            on_found(files)

        widget.after(0, _apply)

    def on_error(exc: Exception) -> None:
        widget.after(0, lambda: status_row.set_status(f"Erro ao procurar PDFs: {exc}"))

    scanner = FolderScanner(folders, progress, done, on_error=on_error)
    scanner.start()
    return scanner


def pick_destination_folder(master, title: str = "Escolher pasta de destino") -> Optional[Path]:
    folder = filedialog.askdirectory(title=title, initialdir=get_last_directory())
    if not folder:
        return None
    path = Path(folder)
    set_last_directory(path)
    return path


def bounce_to_ui(widget: ctk.CTkBaseClass, fn: Callable) -> Callable:
    """Envolve `fn` para que, quando chamada (possivelmente a partir de
    uma thread de trabalho), sua execução real seja agendada com
    segurança na thread principal da interface via `widget.after`.
    """

    def wrapper(*args, **kwargs):
        widget.after(0, lambda: fn(*args, **kwargs))

    return wrapper


def pick_save_file(master, title: str, default_name: str) -> Optional[Path]:
    result = filedialog.asksaveasfilename(
        title=title,
        defaultextension=".pdf",
        filetypes=(("Arquivo PDF", "*.pdf"),),
        initialfile=default_name,
        initialdir=get_last_directory(),
    )
    if not result:
        return None
    path = Path(result)
    set_last_directory(path.parent)
    return path
