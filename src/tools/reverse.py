"""Ferramenta: Inverter páginas.

Inverte a ordem das páginas de um ou vários PDFs, sem rasterizar e sem
perda de qualidade — os objetos de página do pypdf são reaproveitados
diretamente.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pypdf import PdfReader, PdfWriter

from ..utils.batch import BatchRunner, CancelToken, raise_if_cancelled
from ..utils.file_scanner import PdfFile
from ..utils.naming import unique_path
from ..utils.output_paths import compute_output_path, has_multiple_roots
from ..utils.paths import ensure_dir

DEFAULT_OUTPUT_FOLDER_NAME = "PDFs_Invertidos"


def _open_reader(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("PDF protegido por senha") from exc
    return reader


def reverse_one(
    pdf_file: PdfFile,
    dest_root: Path,
    keep_structure: bool,
    multiple_roots: bool,
    token: CancelToken,
) -> Path:
    raise_if_cancelled(token)

    try:
        reader = _open_reader(pdf_file.path)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Não foi possível abrir o PDF: {exc}") from exc

    if len(reader.pages) == 0:
        raise RuntimeError("O PDF não possui páginas.")

    writer = PdfWriter()
    for page in reversed(reader.pages):
        raise_if_cancelled(token)
        writer.add_page(page)

    out_path = compute_output_path(pdf_file, dest_root, keep_structure, multiple_roots)
    ensure_dir(out_path.parent)
    out_path = unique_path(out_path)

    with open(out_path, "wb") as handle:
        writer.write(handle)

    return out_path


def run_reverse_batch(
    files: List[PdfFile],
    dest_root: Path,
    keep_structure: bool,
    on_progress,
    on_done,
) -> BatchRunner:
    """Cria e inicia um BatchRunner para a ferramenta Inverter páginas."""
    multiple_roots = has_multiple_roots(files)
    ensure_dir(dest_root)

    def process_one(pdf_file: PdfFile, token: CancelToken) -> None:
        reverse_one(pdf_file, dest_root, keep_structure, multiple_roots, token)

    runner: BatchRunner = BatchRunner(
        items=files,
        process_one=process_one,
        label_of=lambda f: f.display_path,
        on_progress=on_progress,
        on_done=on_done,
        output_dir=str(dest_root),
    )
    runner.start()
    return runner
