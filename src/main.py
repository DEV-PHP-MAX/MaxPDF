"""Ponto de entrada do Max PDF.

Pode ser executado tanto em desenvolvimento (`python src/main.py`,
a partir da raiz do projeto) quanto como script principal empacotado
pelo PyInstaller. Use `--debug` para abrir as ferramentas de
desenvolvedor do WebView.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path, tanto em
# desenvolvimento quanto dentro do executável gerado pelo PyInstaller
# (onde `sys.argv[0]` e o diretório de trabalho podem variar).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.desktop import app  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402


def main() -> None:
    logger = setup_logger()
    logger.info("Max PDF iniciado")

    try:
        app.run(debug="--debug" in sys.argv)
    except Exception:
        logger.error("Erro fatal na aplicação:\n%s", traceback.format_exc())
        raise
    finally:
        logger.info("Max PDF encerrado")


if __name__ == "__main__":
    main()
