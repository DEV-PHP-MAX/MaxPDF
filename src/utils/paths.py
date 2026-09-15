"""Utilitários de manipulação de caminhos.

Centraliza normalização de caminhos absolutos (para detecção de
duplicados) e cálculo seguro de caminhos relativos, usando sempre
`pathlib` para evitar problemas específicos de plataforma.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def normalize_path(path: "os.PathLike[str] | str") -> str:
    """Normaliza um caminho para comparação/detecção de duplicados.

    Resolve o caminho (sem exigir que exista), aplica normcase (que em
    Windows torna a comparação case-insensitive e uniformiza barras) e
    retorna uma string estável para uso como chave em um `set`/`dict`.
    """
    p = Path(path).expanduser()
    try:
        resolved = p.resolve(strict=False)
    except OSError:
        resolved = p.absolute()
    return os.path.normcase(str(resolved))


def safe_relative_to(path: Path, root: Path) -> Optional[Path]:
    """Retorna `path` relativo a `root`, ou None se não for possível.

    Nunca lança exceção: caso `path` não esteja dentro de `root`
    (por exemplo, por diferenças de unidade em Windows), retorna None
    e o chamador deve usar um caminho alternativo (ex.: apenas o nome).
    """
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (ValueError, OSError):
        return None


def relative_display_path(path: Path, root: Optional[Path]) -> str:
    """Caminho amigável para exibição na interface.

    Se `root` for informado e `path` estiver dentro dele, retorna o
    caminho relativo (ex.: "Janeiro/Lei 001.pdf"). Caso contrário,
    retorna apenas o nome do arquivo.
    """
    if root is not None:
        rel = safe_relative_to(path, root)
        if rel is not None:
            return str(rel)
    return path.name


def ensure_dir(path: Path) -> Path:
    """Cria o diretório (e pais) se não existir. Retorna o próprio path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def root_folder_name(root: Path) -> str:
    """Nome de exibição de uma pasta raiz (para o caso de múltiplas pastas)."""
    name = root.name
    return name if name else str(root)
