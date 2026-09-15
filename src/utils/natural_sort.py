"""Ordenação natural (natural sorting) para nomes de arquivos.

Garante que "Lei 2.pdf" venha antes de "Lei 10.pdf", ao contrário da
ordenação alfabética padrão, que trataria "10" como menor que "2".
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Iterable, List, TypeVar

_DIGIT_RE = re.compile(r"(\d+)")

T = TypeVar("T")


def natural_sort_key(value: str):
    """Gera uma chave de ordenação natural, case-insensitive.

    Divide a string em blocos de dígitos e não-dígitos, convertendo os
    blocos numéricos em inteiros para que "2" < "10" corretamente.
    """
    if value is None:
        value = ""
    parts = _DIGIT_RE.split(value)
    key = []
    for part in parts:
        if part == "":
            continue
        if part.isdigit():
            key.append((1, int(part), ""))
        else:
            key.append((0, 0, part.casefold()))
    return key


def sort_natural(
    items: Iterable[T],
    key: Callable[[T], str] = str,
    reverse: bool = False,
) -> List[T]:
    """Ordena `items` usando ordenação natural aplicada a `key(item)`."""
    return sorted(items, key=lambda item: natural_sort_key(key(item)), reverse=reverse)


def sort_paths_natural(paths: Iterable[Path], reverse: bool = False) -> List[Path]:
    """Atalho para ordenar objetos Path pelo nome, usando ordenação natural."""
    return sort_natural(paths, key=lambda p: p.name, reverse=reverse)
