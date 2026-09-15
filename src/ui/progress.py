"""Painel reutilizável de progresso para operações em lote.

Mostra a operação atual, uma barra de progresso, tempo decorrido e um
botão de cancelar. Todo o estado é atualizado com segurança a partir da
thread principal da UI (o chamador deve agendar as atualizações com
`after`, o que já é feito pelos painéis de ferramenta).
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from ..utils.helpers import format_elapsed_clock
from . import theme


class ProgressPanel(ctk.CTkFrame):
    def __init__(self, master, on_cancel: Optional[Callable[[], None]] = None, **kwargs) -> None:
        super().__init__(master, fg_color=theme.COLOR_CARD, corner_radius=12, **kwargs)
        self._on_cancel = on_cancel

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))

        self._status_label = ctk.CTkLabel(
            top, text="Pronto.", font=theme.font(13), text_color=theme.COLOR_TEXT_PRIMARY, anchor="w"
        )
        self._status_label.pack(side="left", fill="x", expand=True)

        self._elapsed_label = ctk.CTkLabel(
            top, text="", font=theme.font(12), text_color=theme.COLOR_TEXT_SECONDARY
        )
        self._elapsed_label.pack(side="right")

        self._bar = ctk.CTkProgressBar(
            self, progress_color=theme.COLOR_PRIMARY, fg_color=theme.COLOR_BACKGROUND
        )
        self._bar.set(0)
        self._bar.pack(fill="x", padx=16, pady=(4, 10))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 14))

        self._cancel_button = ctk.CTkButton(
            bottom,
            text="CANCELAR",
            fg_color=theme.COLOR_ERROR,
            hover_color=theme.COLOR_ERROR_HOVER,
            width=120,
            command=self._handle_cancel,
            state="disabled",
        )
        self._cancel_button.pack(side="right")

    def reset(self) -> None:
        self._bar.set(0)
        self._status_label.configure(text="Pronto.")
        self._elapsed_label.configure(text="")
        self._cancel_button.configure(state="disabled")

    def start(self) -> None:
        self._bar.set(0)
        self._status_label.configure(text="Iniciando...")
        self._cancel_button.configure(state="normal")

    def update_progress(self, current: int, total: int, label: str, elapsed_seconds: float = 0.0) -> None:
        fraction = (current / total) if total else 0
        self._bar.set(min(1.0, max(0.0, fraction)))
        self._status_label.configure(text=f"Processando {current} de {total}: {label}")
        if elapsed_seconds:
            self._elapsed_label.configure(text=f"Tempo decorrido: {format_elapsed_clock(elapsed_seconds)}")

    def set_status(self, text: str) -> None:
        self._status_label.configure(text=text)

    def finish(self, text: str) -> None:
        self._bar.set(1.0)
        self._status_label.configure(text=text)
        self._cancel_button.configure(state="disabled")

    def _handle_cancel(self) -> None:
        self._cancel_button.configure(state="disabled")
        self._status_label.configure(text="Cancelando... aguarde o arquivo atual terminar.")
        if self._on_cancel:
            self._on_cancel()
