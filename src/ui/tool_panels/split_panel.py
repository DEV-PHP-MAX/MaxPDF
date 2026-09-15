"""Painel da ferramenta Separar PDF."""

from __future__ import annotations

import time
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

from ...tools.split import SplitMode, run_split
from ...utils.batch import BatchResult
from .. import dialogs, theme
from ..progress import ProgressPanel
from . import common


class SplitPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._selected_file: Optional[Path] = None
        self._runner = None
        self._start_time = 0.0

        common.section_title(self, "Separar PDF").pack(anchor="w", padx=4, pady=(0, 2))
        common.section_description(
            self, "Divida um PDF em uma página por arquivo, ou extraia páginas/intervalos específicos."
        ).pack(anchor="w", padx=4, pady=(0, 14))

        selection_card = common.card(self)
        selection_card.pack(fill="x", pady=(0, 14))

        pick_row = ctk.CTkFrame(selection_card, fg_color="transparent")
        pick_row.pack(fill="x", padx=16, pady=(16, 8))
        common.primary_button(pick_row, "+ SELECIONAR PDF", self._pick_file, width=210).pack(side="left")

        self._file_label = ctk.CTkLabel(
            selection_card,
            text="Nenhum arquivo selecionado.",
            font=theme.font(12),
            text_color=theme.COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self._file_label.pack(fill="x", padx=16, pady=(0, 12))

        self._mode_var = ctk.StringVar(value=SplitMode.ONE_PAGE_PER_FILE.value)
        ctk.CTkRadioButton(
            selection_card,
            text="Uma página por arquivo",
            variable=self._mode_var,
            value=SplitMode.ONE_PAGE_PER_FILE.value,
            fg_color=theme.COLOR_PRIMARY,
            command=self._update_pages_entry_state,
        ).pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkRadioButton(
            selection_card,
            text="Selecionar páginas/intervalos:",
            variable=self._mode_var,
            value=SplitMode.RANGES.value,
            fg_color=theme.COLOR_PRIMARY,
            command=self._update_pages_entry_state,
        ).pack(anchor="w", padx=16, pady=(0, 4))

        self._pages_entry = ctk.CTkEntry(
            selection_card, placeholder_text="ex.: 1-3,5,8-10", width=240, state="disabled"
        )
        self._pages_entry.pack(anchor="w", padx=16, pady=(0, 16))

        self._progress = ProgressPanel(self, on_cancel=self._on_cancel)
        self._progress.pack(fill="x", pady=(0, 14))

        self._run_button = common.primary_button(self, "SEPARAR PDF", self._start, width=200)
        self._run_button.pack(anchor="w")
        self._update_run_button_state()

    def _update_pages_entry_state(self) -> None:
        specific = self._mode_var.get() == SplitMode.RANGES.value
        self._pages_entry.configure(state="normal" if specific else "disabled")

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar PDF", filetypes=common.PDF_FILETYPES, initialdir=common.get_last_directory()
        )
        if not path:
            return
        self._selected_file = Path(path)
        common.set_last_directory(self._selected_file.parent)
        self._file_label.configure(text=str(self._selected_file.name))
        self._update_run_button_state()

    def _update_run_button_state(self) -> None:
        running = self._runner is not None
        enabled = self._selected_file is not None and not running
        common.set_button_enabled(
            self._run_button, enabled, fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER
        )

    def _start(self) -> None:
        if self._selected_file is None or self._runner is not None:
            return

        mode = SplitMode(self._mode_var.get())
        pages_spec = self._pages_entry.get().strip() if mode == SplitMode.RANGES else None
        if mode == SplitMode.RANGES and not pages_spec:
            dialogs.show_error(self, "Informe as páginas ou intervalos (ex.: 1-3,5,8-10).")
            return

        destination = common.pick_destination_folder(self, "Escolher pasta de destino")
        if destination is None:
            return

        common.set_button_enabled(
            self._run_button, False, fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER
        )
        self._progress.start()
        self._start_time = time.monotonic()

        on_progress = common.bounce_to_ui(self, self._handle_progress)
        on_done = common.bounce_to_ui(self, self._handle_done)

        self._runner = run_split(
            input_path=self._selected_file,
            dest_root=destination,
            mode=mode,
            pages_spec=pages_spec,
            on_progress=on_progress,
            on_done=on_done,
        )

    def _handle_progress(self, current: int, total: int, label: str) -> None:
        elapsed = time.monotonic() - self._start_time
        self._progress.update_progress(current, total, label, elapsed)

    def _handle_done(self, result: BatchResult) -> None:
        self._runner = None
        summary = "Cancelado." if result.cancelled else f"{result.succeeded} página(s) processada(s)."
        self._progress.finish(summary)
        self._update_run_button_state()
        dialogs.show_summary(self, result, item_noun="página")

    def _on_cancel(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
