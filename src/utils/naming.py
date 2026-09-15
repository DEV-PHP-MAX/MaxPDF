"""Geração segura de nomes de arquivo, evitando sobrescrever resultados.

Nunca sobrescreve um arquivo existente: se "Lei001.pdf" já existir no
destino, o próximo será "Lei001_1.pdf", depois "Lei001_2.pdf", etc.
"""

from __future__ import annotations

from pathlib import Path


def unique_path(desired_path: Path) -> Path:
    """Retorna um Path que não colide com nenhum arquivo existente.

    Se `desired_path` não existir, é retornado sem alterações. Caso
    contrário, um sufixo numérico incremental é adicionado antes da
    extensão até encontrar um nome livre.
    """
    if not desired_path.exists():
        return desired_path

    parent = desired_path.parent
    stem = desired_path.stem
    suffix = desired_path.suffix

    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def unique_dir(desired_path: Path) -> Path:
    """Equivalente a `unique_path`, mas para diretórios (sem extensão)."""
    if not desired_path.exists():
        return desired_path
    parent = desired_path.parent
    name = desired_path.name
    counter = 1
    while True:
        candidate = parent / f"{name}_{counter}"
        if not candidate.exists():
            return candidate
        counter += 1
