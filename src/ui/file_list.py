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

        # Estado do arrastar-e-soltar. `_current_rows` guarda os dados
        # (nome, caminho) da última chamada a `refresh()`, e
        # `_live_order` é a ordem visual atual como uma lista de índices
        # ORIGINAIS (posição em `_current_rows`/na fila real) — permite
        # redesenhar a lista em tempo real durante o arraste sem
        # depender do chamador a cada movimento do mouse.
        self._current_rows: List[Sequence[str]] = []
        self._live_order: List[int] = []
        self._drag_original_index: Optional[int] = None

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
            # Altura fixa em número de linhas (não em pixels): garante um
            # tamanho previsível e razoável mesmo dentro do painel com
            # rolagem, independente da escala de DPI do Windows.
            height=7,
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
        self._current_rows = list(rows)
        self._live_order = list(range(len(self._current_rows)))
        self._redraw()
        count = len(self._current_rows)
        self._count_label.configure(text="1 arquivo" if count == 1 else f"{count} arquivos")

    def _redraw(self) -> None:
        """Redesenha a treeview a partir de `_live_order`, sem alterar
        os dados — usado tanto por `refresh()` quanto, continuamente,
        durante o arrastar-e-soltar."""
        self._tree.delete(*self._tree.get_children())
        for visual_pos, original_index in enumerate(self._live_order, start=1):
            name, path = self._current_rows[original_index]
            self._tree.insert("", "end", iid=str(original_index), values=(visual_pos, name, path))

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
    # A linha arrastada acompanha o cursor em tempo real (a lista é
    # redesenhada a cada movimento do mouse); o resultado só é
    # comunicado ao painel (via `on_move`) uma única vez, ao soltar o
    # botão do mouse. Soltar acima da primeira linha ou abaixo da
    # última move o item para o início/fim da lista, respectivamente.
    def _on_drag_start(self, event: tk.Event) -> None:
        iid = self._tree.identify_row(event.y)
        self._drag_original_index = int(iid) if iid else None
        if self._drag_original_index is not None:
            self._tree.selection_set(iid)

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._drag_original_index is None or not self._live_order:
            return

        target_pos = self._resolve_drop_position(event.y)
        current_pos = self._live_order.index(self._drag_original_index)
        target_pos = max(0, min(target_pos, len(self._live_order) - 1))

        if target_pos == current_pos:
            return

        self._live_order.pop(current_pos)
        self._live_order.insert(target_pos, self._drag_original_index)
        self._redraw()
        self._tree.selection_set(str(self._drag_original_index))

    def _on_drag_release(self, event: tk.Event) -> None:
        if self._drag_original_index is None:
            return

        original_index = self._drag_original_index
        self._drag_original_index = None
        final_pos = self._live_order.index(original_index)

        if final_pos != original_index and self._on_move:
            self._on_move(original_index, final_pos)

    def _resolve_drop_position(self, y: int) -> int:
        """Calcula em qual posição visual (0-indexada) o item deveria
        ficar, com base na posição vertical do cursor — inclusive
        quando o cursor está acima da primeira linha ou abaixo da
        última, o que antes fazia o arraste simplesmente não fazer
        nada."""
        children = self._tree.get_children()
        if not children:
            return 0

        hovered = self._tree.identify_row(y)
        if hovered:
            position = list(children).index(hovered)
            bbox = self._tree.bbox(hovered)
            if bbox:
                row_top, row_height = bbox[1], bbox[3]
                if y > row_top + row_height / 2:
                    position += 1
            return position

        first_bbox = self._tree.bbox(children[0])
        if first_bbox and y < first_bbox[1]:
            return 0
        return len(children)
