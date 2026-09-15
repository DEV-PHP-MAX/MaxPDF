"""Cálculo do caminho de saída de um PDF processado, preservando (quando
solicitado) a estrutura de subpastas original — inclusive quando os
arquivos vêm de múltiplas pastas raiz diferentes (seção 56 do escopo).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .file_scanner import PdfFile
from .paths import safe_relative_to


def has_multiple_roots(pdf_files: Iterable[PdfFile]) -> bool:
    roots = {str(f.root) for f in pdf_files if f.root is not None}
    return len(roots) > 1


def compute_output_path(
    pdf_file: PdfFile,
    dest_root: Path,
    keep_structure: bool,
    multiple_roots: bool = False,
) -> Path:
    """Calcula o caminho de destino de `pdf_file` dentro de `dest_root`.

    - Se `keep_structure` é True e o arquivo veio de uma pasta, o
      caminho relativo à pasta raiz é preservado.
    - Se os arquivos vêm de mais de uma pasta raiz distinta, o nome da
      pasta raiz é usado como subpasta adicional, evitando colisões
      entre arquivos de mesmo nome relativo vindos de raízes diferentes.
    - Caso contrário (arquivo adicionado manualmente, ou estrutura
      desativada), o arquivo vai direto para `dest_root` usando apenas
      o nome do arquivo.
    """
    if keep_structure and pdf_file.root is not None:
        rel = safe_relative_to(pdf_file.path, pdf_file.root)
        if rel is not None:
            if multiple_roots:
                return dest_root / pdf_file.root.name / rel
            return dest_root / rel
    return dest_root / pdf_file.path.name
