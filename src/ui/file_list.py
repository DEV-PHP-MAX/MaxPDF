"""Componente reutilizável de lista de arquivos.

Usado por todas as ferramentas que trabalham com múltiplos arquivos
(PDFs ou imagens). Baseado em `ttk.Treeview`, que continua eficiente
mesmo com centenas ou milhares de linhas — ao contrário de criar um
widget individual para cada item.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Sequence

import customtkinter as ctk

from . import theme
from .buttons import danger_button, secondary_button


class FileListWidget(ctk.CTkFrame):
    """Lista de arquivos com contador, seleção múltipla, remoção,
    limpeza e (opcionalmente) reordenação manual via botões SUBIR/DESCER
    e arrastar-e-soltar (drag-and-drop) diretamente na lista.
    """

    def __init__(
        self,
        master,
        title: str = "Arquivos selecionados",
        show_reorder: bool = False,
        path_column_title: str = "Caminho",
        on_remove_selected: Optional[Callable[[List[int]], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_move: Optional[Callable[[int, int], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color=theme.COLOR_CARD, corner_radius=12, **kwargs)

        self._on_remove_selected = on_remove_selected
        self._on_clear = on_clear
        self._on_move = on_move
        self._show_reorder = show_reorder
        self._drag_start_iid: Optional[str] = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            header, text=title, font=theme.font(14, "bold"), text_color=theme.COLOR_TEXT_PRIMARY
        ).pack(side="left")
        self._count_label = ctk.CTkLabel(
            header, text="0 arquivos", font=theme.font(12), text_color=theme.COLOR_TEXT_SECONDARY
        )
        self._count_label.pack(side="right")

        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._configure_style()

        columns = ("index", "name", "path")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style="MaxPDF.Treeview",
            selectmode="extended",
        )
        self._tree.heading("index", text="#")
        self._tree.heading("name", text="Nome")
        self._tree.heading("path", text=path_column_title)
        self._tree.column("index", width=42, anchor="center", stretch=False)
        self._tree.column("name", width=240, anchor="w")
        self._tree.column("path", width=280, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        if show_reorder:
            self._tree.bind("<ButtonPress-1>", self._on_drag_start)
            self._tree.bind("<B1-Motion>", self._on_drag_motion)
            self._tree.bind("<ButtonRelease-1>", self._on_drag_release)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 14))

        if show_reorder:
            secondary_button(
                actions, "↑ SUBIR", lambda: self._move_selected(-1), width=90, height=34
            ).pack(side="left", padx=(0, 8))
            secondary_button(
                actions, "↓ DESCER", lambda: self._move_selected(1), width=90, height=34
            ).pack(side="left", padx=(0, 8))

        secondary_button(
            actions, "REMOVER SELECIONADO", self._remove_selected, height=34
        ).pack(side="left", padx=(0, 8))

        danger_button(actions, "LIMPAR LISTA", self._clear, height=34).pack(side="left")

    # -- estilo -----------------------------------------------------
    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "MaxPDF.Treeview",
            background=theme.COLOR_CARD,
            fieldbackground=theme.COLOR_CARD,
            foreground=theme.COLOR_TEXT_PRIMARY,
            rowheight=26,
            borderwidth=0,
            font=(theme._resolve_font_family(), 11),
        )
        style.configure(
            "MaxPDF.Treeview.Heading",
            background=theme.COLOR_BACKGROUND,
            foreground=theme.COLOR_TEXT_SECONDARY,
            font=(theme._resolve_font_family(), 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "MaxPDF.Treeview",
            background=[("selected", theme.COLOR_PRIMARY)],
            foreground=[("selected", "#FFFFFF")],
        )

    # -- API pública --------------------------------------------------
    def refresh(self, rows: Sequence[Sequence[str]]) -> None:
        """Atualiza a lista. `rows` é uma sequência de (nome, caminho)."""
        self._tree.delete(*self._tree.get_children())
        for i, (name, path) in enumerate(rows, start=1):
            self._tree.insert("", "end", iid=str(i - 1), values=(i, name, path))
        count = len(rows)
        self._count_label.configure(text="1 arquivo" if count == 1 else f"{count} arquivos")

    def get_selected_indices(self) -> List[int]:
        return sorted(int(iid) for iid in self._tree.selection())

    # -- ações internas -------------------------------------------------
    def _remove_selected(self) -> None:
        indices = self.get_selected_indices()
        if indices and self._on_remove_selected:
            self._on_remove_selected(indices)

    def _clear(self) -> None:
        if self._on_clear:
            self._on_clear()

    def _move_selected(self, delta: int) -> None:
        indices = self.get_selected_indices()
        if len(indices) == 1 and self._on_move:
            self._on_move(indices[0], indices[0] + delta)

    # -- drag and drop ------------------------------------------------
    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_start_iid = self._tree.identify_row(event.y)

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._drag_start_iid is None:
            return
        target_iid = self._tree.identify_row(event.y)
        if target_iid and target_iid != self._drag_start_iid:
            self._tree.selection_set(self._drag_start_iid)

    def _on_drag_release(self, event: tk.Event) -> None:
        if self._drag_start_iid is None:
            return
        target_iid = self._tree.identify_row(event.y)
        start_iid = self._drag_start_iid
        self._drag_start_iid = None
        if not target_iid or target_iid == start_iid:
            return
        if self._on_move:
            self._on_move(int(start_iid), int(target_iid))
