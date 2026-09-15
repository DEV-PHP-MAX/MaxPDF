"""Painel da ferramenta Girar páginas."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List

import customtkinter as ctk

from ...tools.rotate import DEFAULT_OUTPUT_FOLDER_NAME, run_rotate_batch
from ...utils.batch import BatchResult
from ...utils.file_scanner import FileQueue, PdfFile
from ...utils.naming import unique_dir
from .. import dialogs, theme
from ..file_list import FileListWidget
from ..progress import ProgressPanel
from . import common

ANGLE_OPTIONS = ["90°", "180°", "270°"]


class RotatePanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._queue = FileQueue()
        self._runner = None
        self._start_time = 0.0

        common.section_title(self, "Girar páginas").pack(anchor="w", padx=4, pady=(0, 2))
        common.section_description(
            self, "Gire páginas de um ou vários PDFs em 90°, 180° ou 270°, sem rasterizar o conteúdo."
        ).pack(anchor="w", padx=4, pady=(0, 14))

        selection_card = common.card(self)
        selection_card.pack(fill="x", pady=(0, 14))

        self._picker = common.FilePickerRow(
            selection_card,
            on_files_selected=self._on_files_selected,
            on_folder_selected=self._on_folder_selected,
            file_button_text="+ SELECIONAR PDFs",
        )
        self._picker.pack(fill="x", padx=16, pady=(16, 8))

        options_row = ctk.CTkFrame(selection_card, fg_color="transparent")
        options_row.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            options_row, text="Ângulo:", font=theme.font(12, "bold"), text_color=theme.COLOR_TEXT_PRIMARY
        ).pack(side="left", padx=(0, 10))
        self._angle_var = ctk.StringVar(value=ANGLE_OPTIONS[0])
        ctk.CTkSegmentedButton(
            options_row,
            values=ANGLE_OPTIONS,
            variable=self._angle_var,
            selected_color=theme.COLOR_PRIMARY,
            selected_hover_color=theme.COLOR_PRIMARY_HOVER,
        ).pack(side="left")

        self._pages_mode_var = ctk.StringVar(value="all")
        pages_row = ctk.CTkFrame(selection_card, fg_color="transparent")
        pages_row.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkRadioButton(
            pages_row,
            text="Todas as páginas",
            variable=self._pages_mode_var,
            value="all",
            fg_color=theme.COLOR_PRIMARY,
            command=self._update_pages_entry_state,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            pages_row,
            text="Páginas específicas:",
            variable=self._pages_mode_var,
            value="specific",
            fg_color=theme.COLOR_PRIMARY,
            command=self._update_pages_entry_state,
        ).pack(side="left", padx=(0, 8))

        self._pages_entry = ctk.CTkEntry(
            selection_card, placeholder_text="ex.: 1-3,5,8", width=220, state="disabled"
        )
        self._pages_entry.pack(anchor="w", padx=16, pady=(0, 16))

        self._keep_structure_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            selection_card,
            text="Manter estrutura de pastas",
            variable=self._keep_structure_var,
            font=theme.font(12),
            text_color=theme.COLOR_TEXT_PRIMARY,
            fg_color=theme.COLOR_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(0, 16))

        self._file_list = FileListWidget(
            self, on_remove_selected=self._on_remove_selected, on_clear=self._on_clear
        )
        self._file_list.pack(fill="both", expand=True, pady=(0, 14))

        self._progress = ProgressPanel(self, on_cancel=self._on_cancel)
        self._progress.pack(fill="x", pady=(0, 14))

        self._run_button = common.primary_button(self, "GIRAR PÁGINAS", self._start, width=200)
        self._run_button.pack(anchor="w")
        self._update_run_button_state()

    def _update_pages_entry_state(self) -> None:
        self._pages_entry.configure(state="normal" if self._pages_mode_var.get() == "specific" else "disabled")

    # -- seleção ------------------------------------------------------
    def _on_files_selected(self, paths: List[Path]) -> None:
        self._queue.add_manual_files(paths)
        self._refresh_list()

    def _on_folder_selected(self, folder: Path) -> None:
        common.scan_folder_async(self, [folder], self._picker, self._on_scan_found)

    def _on_scan_found(self, files: List[PdfFile]) -> None:
        self._queue.add_many(files)
        self._refresh_list()

    def _on_remove_selected(self, indices: List[int]) -> None:
        self._queue.remove_indices(indices)
        self._refresh_list()

    def _on_clear(self) -> None:
        self._queue.clear()
        self._refresh_list()

    def _refresh_list(self) -> None:
        rows = [(f.display_name, f.display_path) for f in self._queue.items]
        self._file_list.refresh(rows)
        self._update_run_button_state()

    def _update_run_button_state(self) -> None:
        running = self._runner is not None
        enabled = len(self._queue) > 0 and not running
        common.set_button_enabled(
            self._run_button, enabled, fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER
        )

    # -- processamento --------------------------------------------------
    def _start(self) -> None:
        if len(self._queue) == 0 or self._runner is not None:
            return

        if self._pages_mode_var.get() == "specific" and not self._pages_entry.get().strip():
            dialogs.show_error(self, "Informe as páginas ou intervalos (ex.: 1-3,5,8).")
            return

        destination = common.pick_destination_folder(self, "Escolher pasta de destino")
        if destination is None:
            return

        dest_root = unique_dir(destination / DEFAULT_OUTPUT_FOLDER_NAME)
        angle = int(self._angle_var.get().replace("°", ""))
        pages_spec = self._pages_entry.get().strip() if self._pages_mode_var.get() == "specific" else None

        common.set_button_enabled(
            self._run_button, False, fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER
        )
        self._progress.start()
        self._start_time = time.monotonic()

        on_progress = common.bounce_to_ui(self, self._handle_progress)
        on_done = common.bounce_to_ui(self, self._handle_done)

        self._runner = run_rotate_batch(
            files=list(self._queue.items),
            dest_root=dest_root,
            angle=angle,
            pages_spec=pages_spec,
            keep_structure=self._keep_structure_var.get(),
            on_progress=on_progress,
            on_done=on_done,
        )

    def _handle_progress(self, current: int, total: int, label: str) -> None:
        elapsed = time.monotonic() - self._start_time
        self._progress.update_progress(current, total, label, elapsed)

    def _handle_done(self, result: BatchResult) -> None:
        self._runner = None
        summary = "Cancelado." if result.cancelled else f"{result.succeeded} PDF(s) processado(s)."
        self._progress.finish(summary)
        self._update_run_button_state()
        dialogs.show_summary(self, result)

    def _on_cancel(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
