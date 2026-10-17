"""Cria a janela nativa do Max PDF e conecta a interface web à `Api`."""

from __future__ import annotations

import logging
from pathlib import Path

import webview
from webview.dom import DOMEventHandler

from .. import version
from ..utils.helpers import app_data_dir, resource_path
from .api import Api

logger = logging.getLogger("maxpdf")

WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 800


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


def run(debug: bool = False) -> None:
    api = Api()
    index = resource_path("src/web/index.html")
    window = webview.create_window(
        f"{version.APP_NAME} — {version.APP_SUBTITLE}",
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
    webview.start(debug=debug, private_mode=False, storage_path=str(app_data_dir() / "webview"))
