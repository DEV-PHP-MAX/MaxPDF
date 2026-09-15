"""Janela principal do Max PDF: monta o menu lateral e a área de conteúdo."""

from __future__ import annotations

from typing import Dict, List, Tuple

import customtkinter as ctk

from .. import version
from . import theme
from .sidebar import Sidebar
from .tool_panels.images_panel import ImagesPanel
from .tool_panels.merge_panel import MergePanel
from .tool_panels.reverse_panel import ReversePanel
from .tool_panels.rotate_panel import RotatePanel
from .tool_panels.split_panel import SplitPanel

TOOLS: List[Tuple[str, str]] = [
    ("reverse", "↕  Inverter páginas"),
    ("merge", "⊕  Juntar PDFs"),
    ("split", "✂  Separar PDF"),
    ("rotate", "⟳  Girar páginas"),
    ("images", "▣  Imagens → PDF"),
]

_PANEL_FACTORIES = {
    "reverse": ReversePanel,
    "merge": MergePanel,
    "split": SplitPanel,
    "rotate": RotatePanel,
    "images": ImagesPanel,
}


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title(f"{version.APP_NAME} — {version.APP_SUBTITLE}")
        self.geometry(f"{theme.WINDOW_WIDTH}x{theme.WINDOW_HEIGHT}")
        self.minsize(900, 600)
        self.configure(fg_color=theme.COLOR_BACKGROUND)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = Sidebar(self, tools=TOOLS, on_select=self._show_tool)
        self._sidebar.grid(row=0, column=0, sticky="ns")

        self._content = ctk.CTkFrame(self, fg_color=theme.COLOR_BACKGROUND, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._panels: Dict[str, ctk.CTkFrame] = {}
        self._current_key: str | None = None

        first_key = TOOLS[0][0]
        self._show_tool(first_key)
        self._sidebar.select(first_key)

    def _show_tool(self, key: str) -> None:
        if key == self._current_key:
            return

        if self._current_key is not None and self._current_key in self._panels:
            self._panels[self._current_key].grid_forget()

        if key not in self._panels:
            factory = _PANEL_FACTORIES[key]
            self._panels[key] = factory(self._content)

        self._panels[key].grid(row=0, column=0, sticky="nsew")
        self._current_key = key
