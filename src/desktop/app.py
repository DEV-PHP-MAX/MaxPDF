"""Cria a janela nativa do Max PDF e conecta a interface web à `Api`."""

from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path

import webview
from webview.dom import DOMEventHandler

from .. import version
from ..utils.helpers import app_data_dir, resource_path
from .api import Api

logger = logging.getLogger("maxpdf")

WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 800
APP_USER_MODEL_ID = "MaxPDF.FerramentasParaPDF"


def _bind_drop(window: webview.Window, api: Api) -> None:
    """Recebe arquivos/pastas arrastados do Explorer com o caminho completo."""

    def on_drop(event) -> None:
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [Path(f["pywebviewFullPath"]) for f in files if f.get("pywebviewFullPath")]
        if paths:
            api._handle_drop(paths)

    def ignore(_event) -> None:
        return None

    document = window.dom.document
    document.events.dragover += DOMEventHandler(ignore, prevent_default=True)
    document.events.drop += DOMEventHandler(on_drop, prevent_default=True, stop_propagation=True)


def _set_app_user_model_id() -> None:
    """Dá ao processo uma identidade própria na barra de tarefas.

    Sem isso, rodando via `python src/main.py`, o Windows agrupa a janela
    sob o python.exe e mostra o ícone do Python.
    """
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:  # noqa: BLE001
        logger.debug("Não foi possível definir o AppUserModelID")


_ERROR_ALREADY_EXISTS = 183
_SW_RESTORE = 9
_instance_mutex = None


def _focus_existing_instance() -> bool:
    """Garante uma única janela aberta.

    Duas instâncias disputariam o mesmo perfil do WebView2 e a segunda
    fecharia sozinha. Se já houver uma aberta, traz ela para frente e
    retorna True.
    """
    global _instance_mutex
    if not sys.platform.startswith("win"):
        return False
    kernel32, user32 = ctypes.windll.kernel32, ctypes.windll.user32
    _instance_mutex = kernel32.CreateMutexW(None, False, f"Local\\{APP_USER_MODEL_ID}")
    if kernel32.GetLastError() != _ERROR_ALREADY_EXISTS:
        return False
    hwnd = user32.FindWindowW(None, _window_title())
    if hwnd:
        user32.ShowWindow(hwnd, _SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
    return True


def _window_title() -> str:
    return f"{version.APP_NAME} — {version.APP_SUBTITLE}"


def run(debug: bool = False) -> None:
    if _focus_existing_instance():
        logger.info("Já existe uma janela aberta; trazendo para frente")
        return
    _set_app_user_model_id()
    api = Api()
    index = resource_path("src/web/index.html")
    window = webview.create_window(
        _window_title(),
        url=str(index),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(960, 640),
        background_color="#0B0D14",
        text_select=False,
    )
    api._attach(window)
    window.events.loaded += lambda: _bind_drop(window, api)
    # Perfil próprio do WebView em %LOCALAPPDATA%\MaxPDF, só para lembrar
    # preferências da interface (tema). Nenhum arquivo do usuário vai para lá.
    window.events.closed += lambda: logger.info("Janela fechada")
    webview.start(
        debug=debug,
        private_mode=False,
        storage_path=str(app_data_dir() / "webview"),
        icon=str(resource_path("assets/icons/maxpdf.ico")),
    )
