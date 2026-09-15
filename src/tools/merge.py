"""Ferramenta: Juntar PDFs.

Une vários PDFs em um único arquivo, respeitando exatamente a ordem
apresentada na fila (a ordenação — natural, por data, manual etc. — é
responsabilidade da camada de UI; esta ferramenta apenas concatena na
ordem recebida). Um arquivo de entrada corrompido não interrompe a
união: ele é registrado como erro e os demais continuam sendo unidos.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, List

from pypdf import PdfReader, PdfWriter

from ..utils.batch import BatchError, BatchResult, CancelToken, raise_if_cancelled
from ..utils.file_scanner import PdfFile
from ..utils.naming import unique_path
from ..utils.paths import ensure_dir

DEFAULT_OUTPUT_NAME = "PDF_Unido.pdf"


def _open_reader(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("PDF protegido por senha") from exc
    return reader


class MergeRunner(threading.Thread):
    """Executa a união dos PDFs em segundo plano.

    Diferente do `BatchRunner` genérico (que produz um arquivo de saída
    por item), a união produz um único arquivo de saída a partir de
    vários arquivos de entrada, mas segue o mesmo espírito: progresso
    real, cancelamento seguro e tolerância a erros individuais.
    """

    def __init__(
        self,
        files: List[PdfFile],
        output_path: Path,
        on_progress: Callable[[int, int, str], None],
        on_done: Callable[[BatchResult], None],
    ) -> None:
        super().__init__(daemon=True)
        self._files = files
        self._output_path = output_path
        self._on_progress = on_progress
        self._on_done = on_done
        self._cancel_token = CancelToken()

    def cancel(self) -> None:
        self._cancel_token.cancel()

    def run(self) -> None:
        start = time.monotonic()
        total = len(self._files)
        result = BatchResult(total=total, output_dir=str(self._output_path.parent))
        writer = PdfWriter()

        for index, pdf_file in enumerate(self._files, start=1):
            if self._cancel_token.is_cancelled():
                result.cancelled = True
                break

            self._on_progress(index, total, pdf_file.display_path)

            try:
                reader = _open_reader(pdf_file.path)
                if len(reader.pages) == 0:
                    raise RuntimeError("O PDF não possui páginas.")
                for page in reader.pages:
                    if self._cancel_token.is_cancelled():
                        raise RuntimeError("cancelado")
                    writer.add_page(page)
                result.succeeded += 1
            except Exception as exc:  # noqa: BLE001
                if self._cancel_token.is_cancelled():
                    result.cancelled = True
                    break
                result.errors.append(
                    BatchError(item_label=pdf_file.display_path, message=str(exc))
                )

        if result.succeeded > 0 and not (result.cancelled and result.succeeded == 0):
            try:
                ensure_dir(self._output_path.parent)
                final_path = unique_path(self._output_path)
                with open(final_path, "wb") as handle:
                    writer.write(handle)
                result.output_dir = str(final_path.parent)
            except OSError as exc:
                result.errors.append(BatchError(item_label=str(self._output_path), message=str(exc)))

        result.elapsed_seconds = time.monotonic() - start
        self._on_done(result)


def run_merge(
    files: List[PdfFile],
    output_path: Path,
    on_progress,
    on_done,
) -> MergeRunner:
    runner = MergeRunner(files=files, output_path=output_path, on_progress=on_progress, on_done=on_done)
    runner.start()
    return runner
