"""Interpretação de intervalos de páginas informados pelo usuário.

Aceita expressões como "1-3,5,8-10" e resolve para uma lista de
números de página (1-indexados), na ordem em que o usuário os
especificou, sem duplicatas.
"""

from __future__ import annotations

from typing import List


class PageRangeError(ValueError):
    """Erro de sintaxe ou intervalo inválido informado pelo usuário."""


def parse_page_ranges(spec: str, max_pages: int) -> List[int]:
    """Converte uma string de intervalos em uma lista de páginas (1-indexed).

    Regras:
    - Aceita números individuais ("5") e intervalos ("8-10").
    - Aceita espaços em branco livremente.
    - Intervalos invertidos (ex.: "10-8") são interpretados na ordem
      crescente (8, 9, 10) por tolerância ao usuário.
    - Duplicatas são removidas, preservando a primeira ocorrência.
    - Levanta PageRangeError com mensagem amigável para entradas
      inválidas ou fora do intervalo do documento.
    """
    if max_pages <= 0:
        raise PageRangeError("O documento não possui páginas.")

    spec = (spec or "").strip()
    if not spec:
        raise PageRangeError("Informe ao menos uma página ou intervalo (ex.: 1-3,5,8-10).")

    seen = set()
    result: List[int] = []

    for raw_token in spec.split(","):
        token = raw_token.strip()
        if not token:
            continue

        if "-" in token:
            pieces = token.split("-")
            if len(pieces) != 2:
                raise PageRangeError(f"Intervalo inválido: '{token}'.")
            start_str, end_str = pieces[0].strip(), pieces[1].strip()
            if not start_str.isdigit() or not end_str.isdigit():
                raise PageRangeError(f"Intervalo inválido: '{token}'.")
            start, end = int(start_str), int(end_str)
            if start > end:
                start, end = end, start
            for page in range(start, end + 1):
                _validate_page(page, max_pages, token)
                if page not in seen:
                    seen.add(page)
                    result.append(page)
        else:
            if not token.isdigit():
                raise PageRangeError(f"Valor inválido: '{token}'.")
            page = int(token)
            _validate_page(page, max_pages, token)
            if page not in seen:
                seen.add(page)
                result.append(page)

    if not result:
        raise PageRangeError("Nenhuma página válida foi informada.")

    return result


def _validate_page(page: int, max_pages: int, token: str) -> None:
    if page < 1 or page > max_pages:
        raise PageRangeError(
            f"A página {page} (em '{token}') está fora do intervalo do "
            f"documento (1-{max_pages})."
        )


def format_page_list(pages: List[int]) -> str:
    """Formata uma lista de páginas de volta para exibição, ex.: '1,2,3,5,8,9,10'."""
    return ",".join(str(p) for p in pages)
