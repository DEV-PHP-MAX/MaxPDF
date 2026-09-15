"""Identidade visual centralizada do Max PDF.

Todas as cores, fontes e ajustes de DPI usados pela interface devem
vir deste módulo, para manter consistência visual entre as telas.
"""

from __future__ import annotations

import ctypes
import sys

import customtkinter as ctk

# Paleta oficial -------------------------------------------------------
COLOR_PRIMARY = "#1E90FF"
COLOR_PRIMARY_HOVER = "#1676D2"
COLOR_BACKGROUND = "#F5F7FA"
COLOR_CARD = "#FFFFFF"
COLOR_TEXT_PRIMARY = "#1F2937"
COLOR_TEXT_SECONDARY = "#6B7280"
COLOR_SUCCESS = "#16A34A"
COLOR_SUCCESS_HOVER = "#128a3e"
COLOR_ERROR = "#DC2626"
COLOR_ERROR_HOVER = "#B91C1C"
COLOR_BORDER = "#D9E2EC"

# Cor de texto sobre o menu lateral azul (opção não selecionada)
COLOR_SIDEBAR_TEXT = "#FFFFFF"
COLOR_SIDEBAR_TEXT_MUTED = "#DCEBFF"

FONT_FAMILY = "Segoe UI"
_FALLBACK_FONT_FAMILY = "Helvetica"

WINDOW_WIDTH = 1120
WINDOW_HEIGHT = 780
SIDEBAR_WIDTH = 230


def enable_windows_dpi_awareness() -> None:
    """Ativa reconhecimento de DPI por monitor no Windows.

    Deve ser chamado antes de criar a janela principal. É seguro
    chamar em outras plataformas (a função simplesmente não faz nada).
    """
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
    except Exception:  # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


def configure_appearance() -> None:
    """Configura o modo de aparência global do CustomTkinter."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


_font_family_cache: str | None = None


def _resolve_font_family() -> str:
    global _font_family_cache
    if _font_family_cache is not None:
        return _font_family_cache
    try:
        import tkinter.font as tkfont

        available = set(tkfont.families())
        _font_family_cache = FONT_FAMILY if FONT_FAMILY in available else _FALLBACK_FONT_FAMILY
    except Exception:  # noqa: BLE001
        _font_family_cache = _FALLBACK_FONT_FAMILY
    return _font_family_cache


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    """Cria uma fonte Segoe UI (com fallback) no tamanho/peso pedidos."""
    return ctk.CTkFont(family=_resolve_font_family(), size=size, weight=weight)
