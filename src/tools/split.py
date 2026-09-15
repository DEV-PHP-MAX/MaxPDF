"""Ferramenta: Separar PDF.

Oferece dois modos:
  1. Uma página por arquivo (pagina_001.pdf, pagina_002.pdf, ...).
  2. Extração de páginas/intervalos específicos (ex.: "1-3,5,8-10") em
     um único arquivo de saída "<Documento>_separado.pdf".

O documento original nunca é modificado.
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

from pypdf import PdfReader, PdfWriter

from ..utils.batch import BatchError, BatchResult, CancelToken
from ..utils.naming import unique_dir, unique_path
from ..utils.page_ranges import parse_page_ranges
from ..utils.paths import ensure_dir


class SplitMode(str, Enum):
    ONE_PAGE_PER_FILE = "one_page_per_file"
    RANGES = "ranges"


def _open_reader(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("PDF protegido por senha") from exc
    return reader


class SplitRunner(threading.Thread):
    def __init__(
        self,
        input_path: Path,
        dest_root: Path,
        mode: SplitMode,
        pages_spec: Optional[str],
        on_progress: Callable[[int, int, str], None],
        on_done: Callable[[BatchResult], None],
    ) -> None:
        super().__init__(daemon=True)
        self._input_path = input_path
        self._dest_root = dest_root
        self._mode = mode
        self._pages_spec = pages_spec
        self._on_progress = on_progress
        self._on_done = on_done
        self._cancel_token = CancelToken()

    def cancel(self) -> None:
        self._cancel_token.cancel()

    def run(self) -> None:
        start = time.monotonic()
        try:
            reader = _open_reader(self._input_path)
        except Exception as exc:  # noqa: BLE001
            result = BatchResult(total=1, elapsed_seconds=0.0)
            result.errors.append(BatchError(item_label=self._input_path.name, message=str(exc)))
            self._on_done(result)
            return

        total_pages = len(reader.pages)
        if total_pages == 0:
            result = BatchResult(total=1, elapsed_seconds=time.monotonic() - start)
            result.errors.append(
                BatchError(item_label=self._input_path.name, message="O PDF não possui páginas.")
            )
            self._on_done(result)
            return

        if self._mode == SplitMode.ONE_PAGE_PER_FILE:
            result = self._run_one_page_per_file(reader, total_pages)
        else:
            result = self._run_ranges(reader, total_pages)

        result.elapsed_seconds = time.monotonic() - start
        self._on_done(result)

    def _run_one_page_per_file(self, reader: PdfReader, total_pages: int) -> BatchResult:
        result = BatchResult(total=total_pages)
        out_folder = unique_dir(self._dest_root / f"{self._input_path.stem}_separado")
        ensure_dir(out_folder)
        result.output_dir = str(out_folder)
        width = max(3, len(str(total_pages)))

        for index in range(1, total_pages + 1):
            if self._cancel_token.is_cancelled():
                result.cancelled = True
                break

            name = f"pagina_{index:0{width}d}.pdf"
            self._on_progress(index, total_pages, name)

            try:
                writer = PdfWriter()
                writer.add_page(reader.pages[index - 1])
                out_path = unique_path(out_folder / name)
                with open(out_path, "wb") as handle:
                    writer.write(handle)
                result.succeeded += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(BatchError(item_label=name, message=str(exc)))

        return result

    def _run_ranges(self, reader: PdfReader, total_pages: int) -> BatchResult:
        try:
            pages = parse_page_ranges(self._pages_spec or "", total_pages)
        except Exception as exc:  # noqa: BLE001
            result = BatchResult(total=1)
            result.errors.append(BatchError(item_label=self._input_path.name, message=str(exc)))
            return result

        result = BatchResult(total=len(pages))
        writer = PdfWriter()

        for index, page_number in enumerate(pages, start=1):
            if self._cancel_token.is_cancelled():
                result.cancelled = True
                break
            self._on_progress(index, len(pages), f"página {page_number}")
            try:
                writer.add_page(reader.pages[page_number - 1])
                result.succeeded += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(BatchError(item_label=f"página {page_number}", message=str(exc)))

        if result.succeeded > 0:
            try:
                ensure_dir(self._dest_root)
                out_path = unique_path(self._dest_root / f"{self._input_path.stem}_separado.pdf")
                with open(out_path, "wb") as handle:
                    writer.write(handle)
                result.output_dir = str(out_path.parent)
            except OSError as exc:
                result.errors.append(BatchError(item_label=self._input_path.name, message=str(exc)))

        return result


def run_split(
    input_path: Path,
    dest_root: Path,
    mode: SplitMode,
    pages_spec: Optional[str],
    on_progress,
    on_done,
) -> SplitRunner:
    runner = SplitRunner(
        input_path=input_path,
        dest_root=dest_root,
        mode=mode,
        pages_spec=pages_spec,
        on_progress=on_progress,
        on_done=on_done,
    )
    runner.start()
    return runner
