"""Infraestrutura comum para processamento em lote.

Todas as ferramentas (inverter, juntar, separar, girar, imagens->pdf)
seguem o mesmo padrão: recebem uma lista de itens, processam cada um
individualmente em uma thread de trabalho, relatam progresso, suportam
cancelamento seguro e produzem um `BatchResult` ao final — sem que um
único arquivo com erro interrompa o lote inteiro.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class BatchError:
    item_label: str
    message: str


@dataclass
class BatchResult:
    total: int = 0
    succeeded: int = 0
    errors: List[BatchError] = field(default_factory=list)
    cancelled: bool = False
    elapsed_seconds: float = 0.0
    output_dir: Optional[str] = None

    @property
    def failed(self) -> int:
        return len(self.errors)

    @property
    def processed(self) -> int:
        return self.succeeded + self.failed


class CancelToken:
    """Token de cancelamento compartilhado entre a UI e a thread de trabalho."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


class BatchRunner(Generic[T], threading.Thread):
    """Executa `process_one` para cada item de `items` em uma thread própria.

    - `on_progress(current, total, label)` é chamado antes de processar
      cada item (current é 1-indexado).
    - `on_done(result)` é chamado ao final, com sucesso, erro ou
      cancelamento.
    - Todos os callbacks são invocados a partir desta thread; o
      chamador deve agendá-los com segurança na thread principal da UI
      (por exemplo, com `widget.after(0, ...)`).
    """

    def __init__(
        self,
        items: List[T],
        process_one: Callable[[T, CancelToken], None],
        label_of: Callable[[T], str],
        on_progress: Callable[[int, int, str], None],
        on_done: Callable[[BatchResult], None],
        output_dir: Optional[str] = None,
    ) -> None:
        threading.Thread.__init__(self, daemon=True)
        self._items = items
        self._process_one = process_one
        self._label_of = label_of
        self._on_progress = on_progress
        self._on_done = on_done
        self._cancel_token = CancelToken()
        self._output_dir = output_dir

    def cancel(self) -> None:
        self._cancel_token.cancel()

    def run(self) -> None:
        start = time.monotonic()
        result = BatchResult(total=len(self._items), output_dir=self._output_dir)

        for index, item in enumerate(self._items, start=1):
            if self._cancel_token.is_cancelled():
                result.cancelled = True
                break

            label = self._label_of(item)
            self._on_progress(index, result.total, label)

            try:
                self._process_one(item, self._cancel_token)
                result.succeeded += 1
            except _SkippedByCancel:
                result.cancelled = True
                break
            except Exception as exc:  # noqa: BLE001 - isolamos erro por item
                result.errors.append(BatchError(item_label=label, message=str(exc)))

        result.elapsed_seconds = time.monotonic() - start
        self._on_done(result)


class _SkippedByCancel(Exception):
    """Sinaliza que o item atual foi interrompido por cancelamento."""


def raise_if_cancelled(token: CancelToken) -> None:
    """Interrompe o item atual de forma segura caso o usuário tenha cancelado."""
    if token.is_cancelled():
        raise _SkippedByCancel()
