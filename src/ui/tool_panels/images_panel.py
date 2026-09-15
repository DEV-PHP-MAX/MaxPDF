"""Painel da ferramenta Imagens → PDF."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List

import customtkinter as ctk

from ...tools.images_to_pdf import DEFAULT_OUTPUT_NAME, is_supported_image, run_images_to_pdf
from ...utils.batch import BatchResult
from ...utils.file_scanner import FileQueue, PdfFile
from .. import dialogs, theme
from ..file_list import FileListWidget
from ..progress import ProgressPanel
from . import common


class ImagesPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._queue = FileQueue()
        self._runner = None
        self._start_time = 0.0

        common.section_title(self, "Imagens → PDF").pack(anchor="w", padx=4, pady=(0, 2))
        common.section_description(
            self,
            "Converta várias imagens (JPG, PNG, WEBP, BMP, TIFF) em um único PDF, "
            "na ordem apresentada abaixo. Imagens com transparência recebem fundo branco.",
        ).pack(anchor="w", padx=4, pady=(0, 14))

        selection_card = common.card(self)
        selection_card.pack(fill="x", pady=(0, 14))

        self._picker = common.FilePickerRow(
            selection_card,
            on_files_selected=self._on_files_selected,
            on_folder_selected=None,
            allow_folder=False,
            file_button_text="+ SELECIONAR IMAGENS",
            filetypes=common.IMAGE_FILETYPES,
        )
        self._picker.pack(fill="x", padx=16, pady=16)

        self._file_list = FileListWidget(
            self,
            title="Imagens selecionadas",
            show_reorder=True,
            path_column_title="Caminho",
            on_remove_selected=self._on_remove_selected,
            on_clear=self._on_clear,
            on_move=self._on_move,
        )
        self._file_list.pack(fill="x", pady=(0, 14))

        self._progress = ProgressPanel(self, on_cancel=self._on_cancel)
        self._progress.pack(fill="x", pady=(0, 14))

        self._run_button = common.primary_button(self, "GERAR PDF", self._start, width=200)
        self._run_button.pack(anchor="w")
        self._update_run_button_state()

    # -- seleção ------------------------------------------------------
    def _on_files_selected(self, paths: List[Path]) -> None:
        valid = [p for p in paths if is_supported_image(p)]
        skipped = len(paths) - len(valid)
        self._queue.add_many([PdfFile(path=p, root=None) for p in valid])
        self._refresh_list()
        if skipped:
            dialogs.show_error(
                self,
                f"{skipped} arquivo(s) ignorado(s) por não serem imagens compatíveis.",
                title="Alguns arquivos foram ignorados",
            )

    def _on_remove_selected(self, indices: List[int]) -> None:
        self._queue.remove_indices(indices)
        self._refresh_list()

    def _on_clear(self) -> None:
        self._queue.clear()
        self._refresh_list()

    def _on_move(self, old_index: int, new_index: int) -> None:
        self._queue.move_to(old_index, new_index)
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

        output_path = common.pick_save_file(self, "Salvar PDF como", DEFAULT_OUTPUT_NAME)
        if output_path is None:
            return

        common.set_button_enabled(
            self._run_button, False, fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER
        )
        self._progress.start()
        self._start_time = time.monotonic()

        on_progress = common.bounce_to_ui(self, self._handle_progress)
        on_done = common.bounce_to_ui(self, self._handle_done)

        image_paths = [f.path for f in self._queue.items]
        self._runner = run_images_to_pdf(
            image_paths=image_paths, output_path=output_path, on_progress=on_progress, on_done=on_done
        )

    def _handle_progress(self, current: int, total: int, label: str) -> None:
        elapsed = time.monotonic() - self._start_time
        self._progress.update_progress(current, total, label, elapsed)

    def _handle_done(self, result: BatchResult) -> None:
        self._runner = None
        summary = "Cancelado." if result.cancelled else "PDF gerado com sucesso."
        self._progress.finish(summary)
        self._update_run_button_state()
        dialogs.show_summary(self, result, item_noun="imagem")

    def _on_cancel(self) -> None:
        if self._runner is not None:
            self._runner.cancel()
