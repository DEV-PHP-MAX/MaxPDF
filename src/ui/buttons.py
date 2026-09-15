"""Botões padronizados do Max PDF.

Centraliza a aparência de botões primários, secundários e de perigo,
incluindo o estado desabilitado — que passa a usar um cinza neutro em
vez da versão "lavada" da cor original (problema visual do estado
`disabled` padrão do CustomTkinter, que só troca a cor do texto e
deixa o fundo colorido, dando a impressão de um botão quebrado).
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from . import theme


def primary_button(master, text: str, command: Callable[[], None], **kwargs) -> ctk.CTkButton:
    defaults = dict(
        fg_color=theme.COLOR_PRIMARY,
        hover_color=theme.COLOR_PRIMARY_HOVER,
        text_color="#FFFFFF",
        font=theme.font(13, "bold"),
        height=42,
        corner_radius=10,
        border_width=0,
    )
    defaults.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **defaults)


def secondary_button(master, text: str, command: Callable[[], None], **kwargs) -> ctk.CTkButton:
    """Botão neutro com contorno visível — usado para ações secundárias
    (ex.: "Selecionar pasta", "Remover selecionado", "Subir"/"Descer").
    Usa fundo branco (não a cor de fundo da página) para não se
    confundir com o restante da tela.
    """
    defaults = dict(
        fg_color=theme.COLOR_CARD,
        text_color=theme.COLOR_TEXT_PRIMARY,
        hover_color=theme.COLOR_BACKGROUND,
        border_width=1,
        border_color=theme.COLOR_BORDER,
        font=theme.font(13, "bold"),
        height=38,
        corner_radius=10,
    )
    defaults.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **defaults)


def danger_button(master, text: str, command: Callable[[], None], **kwargs) -> ctk.CTkButton:
    defaults = dict(
        fg_color=theme.COLOR_ERROR,
        hover_color=theme.COLOR_ERROR_HOVER,
        text_color="#FFFFFF",
        font=theme.font(13, "bold"),
        height=38,
        corner_radius=10,
        border_width=0,
    )
    defaults.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, **defaults)


def set_button_enabled(
    button: ctk.CTkButton,
    enabled: bool,
    *,
    fg_color: str,
    hover_color: str,
    text_color: str = "#FFFFFF",
) -> None:
    """Habilita/desabilita um botão trocando explicitamente as cores.

    Ao desabilitar, o botão passa a usar um cinza neutro (em vez de
    manter a cor de fundo original com o texto apenas apagado), para
    que o estado indisponível fique visualmente óbvio. Ao habilitar,
    as cores originais (`fg_color`/`hover_color`/`text_color`) são
    restauradas.
    """
    if enabled:
        button.configure(
            state="normal", fg_color=fg_color, hover_color=hover_color, text_color=text_color
        )
    else:
        button.configure(
            state="disabled",
            fg_color=theme.COLOR_BORDER,
            hover_color=theme.COLOR_BORDER,
            text_color=theme.COLOR_TEXT_SECONDARY,
        )
