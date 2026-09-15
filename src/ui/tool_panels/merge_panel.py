"""Painel da ferramenta Juntar PDFs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List

import customtkinter as ctk

from ...tools.merge import DEFAULT_OUTPUT_NAME, run_merge
from ...utils.batch import BatchResult
from ...utils.file_scanner import FileQueue, PdfFile
from ...utils.natural_sort import natural_sort_key
from .. import dialogs, theme
from ..file_list import FileListWidget
from ..progress import ProgressPanel
from . import common

SORT_NAME_ASC = "Nome A → Z"
SORT_NAME_DESC = "Nome Z → A"
SORT_PATH = "Caminho/pasta"
SORT_MODIFIED = "Data de modificação"
SORT_CUSTOM = "Ordem personalizada"

SORT_OPTIONS = [SORT_NAME_ASC, SORT_NAME_DESC, SORT_PATH, SORT_MODIFIED, SORT_CUSTOM]


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


class MergePanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._queue = FileQueue()
        self._runner = None
        self._start_time = 0.0

        common.section_title(self, "Juntar PDFs").pack(anchor="w", padx=4, pady=(0, 2))
        common.section_description(
            self, "Una vários PDFs em um único arquivo, respeitando exatamente a ordem definida abaixo."
        ).pack(anchor="w", padx=4, pady=(0, 14))

        selection_card = common.card(self)
        selection_card.pack(fill="x", pady=(0, 14))

        self._picker = common.FilePickerRow(
            selection_card,
            on_files_selected=self._on_files_selected,
            on_folder_selected=self._on_folder_selected,
            file_button_text="+ SELECIONAR PDFs",
        )
        self._picker.pack(fill="x", padx=16, pady=16)

        sort_row = ctk.CTkFrame(selection_card, fg_color="transparent")
        sort_row.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkLabel(
            sort_row, text="Ordenar por:", font=theme.font(12, "bold"), text_color=theme.COLOR_TEXT_PRIMARY
        ).pack(side="left", padx=(0, 10))
        self._sort_var = ctk.StringVar(value=SORT_NAME_ASC)
        ctk.CTkOptionMenu(
            sort_row,
            values=SORT_OPTIONS,
            variable=self._sort_var,
            command=lambda _choice: self._apply_sort(),
            fg_color=theme.COLOR_PRIMARY,
            button_color=theme.COLOR_PRIMARY,
            button_hover_color=theme.COLOR_PRIMARY_HOVER,
        ).pack(side="left")

        self._file_list = FileListWidget(
            self,
            show_reorder=True,
            on_remove_selected=self._on_remove_selected,
            on_clear=self._on_clear,
            on_move=self._on_move,
        )
        self._file_list.pack(fill="both", expand=True, pady=(0, 14))

        self._progress = ProgressPanel(self, on_cancel=self._on_cancel)
        self._progress.pack(fill="x", pady=(0, 14))

        self._run_button = common.primary_button(self, "JUNTAR PDFs", self._start, width=200)
        self._run_button.pack(anchor="w")
        self._update_run_button_state()

    # -- seleção ------------------------------------------------------
    def _on_files_selected(self, paths: List[Path]) -> None:
        self._queue.add_manual_files(paths)
        self._after_files_changed()

    def _on_folder_selected(self, folder: Path) -> None:
        common.scan_folder_async(self, [folder], self._picker, self._on_scan_found)

    def _on_scan_found(self, files: List[PdfFile]) -> None:
        self._queue.add_many(files)
        self._after_files_changed()

    def _after_files_changed(self) -> None:
        if self._sort_var.get() != SORT_CUSTOM:
            self._apply_sort()
        else:
            self._refresh_list()

    def _on_remove_selected(self, indices: List[int]) -> None:
        self._queue.remove_indices(indices)
        self._refresh_list()

    def _on_clear(self) -> None:
        self._queue.clear()
        self._refresh_list()

    def _on_move(self, old_index: int, new_index: int) -> None:
        self._queue.move_to(old_index, new_index)
        self._sort_var.set(SORT_CUSTOM)
        self._refresh_list()

    def _apply_sort(self) -> None:
        mode = self._sort_var.get()
        items = self._queue.items
        if mode == SORT_NAME_ASC:
            items = sorted(items, key=lambda f: natural_sort_key(f.path.name))
        elif mode == SORT_NAME_DESC:
            items = sorted(items, key=lambda f: natural_sort_key(f.path.name), reverse=True)
        elif mode == SORT_PATH:
            items = sorted(items, key=lambda f: natural_sort_key(str(f.path)))
        elif mode == SORT_MODIFIED:
            items = sorted(items, key=lambda f: _safe_mtime(f.path))
        # SORT_CUSTOM: mantém a ordem atual (definida manualmente pelo usuário)
        self._queue.replace_all(items)
        self._refresh_list()

    def _refresh_list(self) -> None:
        rows = [(f.display_name, f.display_path) for f in self._queue.items]
        self._file_list.refresh(rows)
        self._update_run_button_state()

    def _update_run_button_state(self) -> None:
        running = self._runner is not None
        self._run_button.configure(state="disabled" if (len(self._queue) < 1 or running) else "normal")

    # -- processamento --------------------------------------------------
    def _start(self) -> None:
        if len(self._queue) == 0 or self._runner is not None:
            return

        output_path = common.pick_save_file(self, "Salvar PDF unido como", DEFAULT_OUTPUT_NAME)
        if output_path is None:
            return

        self._run_button.configure(state="disabled")
        self._progress.start()
        self._start_time = time.monotonic()

        on_progress = common.bounce_to_ui(self, self._handle_progress)
        on_done = common.bounce_to_ui(self, self._handle_done)

        self._runner = run_merge(
            files=list(self._queue.items),
            output_path=output_path,
            on_progress=on_progress,
            on_done=on_done,
        )

    def _handle_progress(self, current: int, total: int, label: str) -> None:
        elapsed = time.monotonic() - self._start_time
        self._progress.update_progress(current, total, label, elapsed)

    def _handle_done(self, result: BatchResult) -> None:
        self._runner = None
        summary = "Cancelado." if result.cancelled else "PDF unido com sucesso."
        self._progress.finish(summary)
        self._update_run_button_state()
        dialogs.show_summary(self, result)

    def _on_cancel(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
