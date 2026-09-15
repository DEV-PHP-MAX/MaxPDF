"""Menu lateral azul com a navegação entre ferramentas."""

from __future__ import annotations

from typing import Callable, List, Tuple

import customtkinter as ctk

from ..version import get_display_version
from . import theme


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        tools: List[Tuple[str, str]],
        on_select: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(
            master, width=theme.SIDEBAR_WIDTH, corner_radius=0, fg_color=theme.COLOR_PRIMARY, **kwargs
        )
        self.grid_propagate(False)
        self._on_select = on_select
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._selected_key: str | None = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(28, 18))

        ctk.CTkLabel(
            header,
            text="MAX PDF",
            font=theme.font(22, "bold"),
            text_color=theme.COLOR_SIDEBAR_TEXT,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            header,
            text="Ferramentas para PDF",
            font=theme.font(12),
            text_color=theme.COLOR_SIDEBAR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="both", expand=True, padx=14)

        for key, label in tools:
            button = ctk.CTkButton(
                nav,
                text=label,
                anchor="w",
                corner_radius=10,
                height=44,
                font=theme.font(13, "bold"),
                fg_color="transparent",
                text_color=theme.COLOR_SIDEBAR_TEXT,
                hover_color=theme.COLOR_PRIMARY_HOVER,
                command=lambda k=key: self._handle_click(k),
            )
            button.pack(fill="x", pady=4)
            self._buttons[key] = button

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkLabel(
            footer,
            text=get_display_version(),
            font=theme.font(10),
            text_color=theme.COLOR_SIDEBAR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

    def _handle_click(self, key: str) -> None:
        self.select(key)
        self._on_select(key)

    def select(self, key: str) -> None:
        if self._selected_key == key:
            return
        if self._selected_key and self._selected_key in self._buttons:
            previous = self._buttons[self._selected_key]
            previous.configure(fg_color="transparent", text_color=theme.COLOR_SIDEBAR_TEXT)
        if key in self._buttons:
            current = self._buttons[key]
            current.configure(fg_color=theme.COLOR_CARD, text_color=theme.COLOR_PRIMARY)
        self._selected_key = key
