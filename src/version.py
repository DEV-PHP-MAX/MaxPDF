"""Ponto único de versão do Max PDF.

Nenhuma outra parte do programa deve declarar a versão manualmente.
Sempre importe APP_VERSION a partir deste módulo.
"""

APP_NAME = "MAX PDF"
APP_SUBTITLE = "Ferramentas para PDF"

# Semantic Versioning: MAJOR.MINOR.PATCH
APP_VERSION = "1.0.0"


def get_display_version() -> str:
    """Retorna a string exibida discretamente na interface."""
    return f"Max PDF v{APP_VERSION}"
