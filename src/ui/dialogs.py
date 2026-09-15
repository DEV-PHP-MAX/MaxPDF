"""Diálogos reutilizáveis: resumo de processamento e lista de erros."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import customtkinter as ctk

from ..utils.batch import BatchResult
from ..utils.helpers import format_duration, open_folder
from . import theme


class ErrorListDialog(ctk.CTkToplevel):
    def __init__(self, master, result: BatchResult) -> None:
        super().__init__(master)
        self.title("Arquivos com erro")
        self.geometry("560x420")
        self.configure(fg_color=theme.COLOR_BACKGROUND)
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=f"{len(result.errors)} arquivo(s) com erro",
            font=theme.font(15, "bold"),
            text_color=theme.COLOR_TEXT_PRIMARY,
        ).pack(anchor="w", padx=20, pady=(18, 8))

        box = ctk.CTkScrollableFrame(self, fg_color=theme.COLOR_CARD, corner_radius=12)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        for error in result.errors:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(
                row, text=error.item_label, font=theme.font(12, "bold"),
                text_color=theme.COLOR_TEXT_PRIMARY, anchor="w", justify="left",
            ).pack(fill="x")
            ctk.CTkLabel(
                row, text=error.message, font=theme.font(11),
                text_color=theme.COLOR_ERROR, anchor="w", justify="left", wraplength=480,
            ).pack(fill="x")

        ctk.CTkButton(
            self, text="FECHAR", fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self.destroy,
        ).pack(pady=(0, 18))


class SummaryDialog(ctk.CTkToplevel):
    def __init__(self, master, result: BatchResult, item_noun: str = "arquivo") -> None:
        super().__init__(master)
        noun_plural = f"{item_noun}s"
        self.title("Processamento concluído")
        self.geometry("460x360")
        self.configure(fg_color=theme.COLOR_BACKGROUND)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        title = "PROCESSAMENTO CANCELADO" if result.cancelled else "PROCESSAMENTO CONCLUÍDO"
        title_color = theme.COLOR_ERROR if result.cancelled else theme.COLOR_SUCCESS

        ctk.CTkLabel(self, text=title, font=theme.font(17, "bold"), text_color=title_color).pack(
            pady=(24, 16)
        )

        card = ctk.CTkFrame(self, fg_color=theme.COLOR_CARD, corner_radius=12)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        def add_line(text: str, color: str = theme.COLOR_TEXT_PRIMARY) -> None:
            ctk.CTkLabel(
                card, text=text, font=theme.font(13), text_color=color, anchor="w"
            ).pack(fill="x", padx=18, pady=4)

        add_line(f"{result.total} {noun_plural} encontrado(s)")
        add_line(f"{result.succeeded} processado(s) com sucesso", theme.COLOR_SUCCESS)
        if result.errors:
            add_line(f"{result.failed} {noun_plural} com erro", theme.COLOR_ERROR)
        if result.cancelled:
            add_line(f"{result.processed} de {result.total} concluídos antes do cancelamento")
        add_line(f"Tempo total: {format_duration(result.elapsed_seconds)}")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=(0, 22))

        if result.output_dir:
            ctk.CTkButton(
                buttons,
                text="ABRIR PASTA",
                fg_color=theme.COLOR_PRIMARY,
                hover_color=theme.COLOR_PRIMARY_HOVER,
                command=lambda: open_folder(Path(result.output_dir)),
            ).pack(side="left", padx=(0, 10))

        if result.errors:
            ctk.CTkButton(
                buttons,
                text="VER ERROS",
                fg_color=theme.COLOR_BACKGROUND,
                text_color=theme.COLOR_TEXT_PRIMARY,
                hover_color=theme.COLOR_BORDER,
                command=lambda: ErrorListDialog(self, result),
            ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            buttons, text="FECHAR", fg_color=theme.COLOR_TEXT_SECONDARY, hover_color="#4B5563",
            command=self.destroy,
        ).pack(side="right")


def show_summary(master, result: BatchResult, item_noun: str = "arquivo") -> None:
    SummaryDialog(master, result, item_noun=item_noun)


class MessageDialog(ctk.CTkToplevel):
    """Diálogo simples de mensagem amigável (erro/aviso/informação)."""

    def __init__(self, master, title: str, message: str, kind: str = "info") -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("420x200")
        self.configure(fg_color=theme.COLOR_BACKGROUND)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        color = {
            "error": theme.COLOR_ERROR,
            "success": theme.COLOR_SUCCESS,
        }.get(kind, theme.COLOR_TEXT_PRIMARY)

        ctk.CTkLabel(self, text=title, font=theme.font(15, "bold"), text_color=color).pack(
            pady=(22, 8)
        )
        ctk.CTkLabel(
            self, text=message, font=theme.font(12), text_color=theme.COLOR_TEXT_PRIMARY,
            wraplength=360, justify="center",
        ).pack(fill="x", padx=20)

        ctk.CTkButton(
            self, text="OK", fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self.destroy, width=100,
        ).pack(pady=18)


def show_error(master, message: str, title: str = "Ops, algo deu errado") -> None:
    MessageDialog(master, title, message, kind="error")


def show_info(master, message: str, title: str = "Informação") -> None:
    MessageDialog(master, title, message, kind="info")
