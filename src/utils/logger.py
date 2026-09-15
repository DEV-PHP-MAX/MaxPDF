"""Configuração de logging local do Max PDF.

Os logs ajudam a diagnosticar problemas sem comprometer a privacidade:
nunca registramos o conteúdo dos PDFs, e evitamos registrar caminhos
pessoais completos quando não são necessários para o diagnóstico.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from .helpers import app_data_dir

_LOGGER_NAME = "maxpdf"
_configured = False


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """Configura (uma única vez) e retorna o logger da aplicação."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)

    if _configured:
        return logger

    logger.setLevel(level)

    try:
        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "maxpdf.log"

        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except OSError:
        # Se não for possível criar o arquivo de log (ex.: sem
        # permissão de escrita), continuamos sem logging em arquivo em
        # vez de impedir o uso do aplicativo.
        pass

    _configured = True
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)
