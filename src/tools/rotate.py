"""Ferramenta: Girar páginas.

Gira todas as páginas (ou páginas específicas) de um ou vários PDFs em
90°, 180° ou 270°, sem rasterizar — usa a rotação nativa de páginas do
pypdf (`Page.rotate`), que apenas ajusta os metadados de exibição.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pypdf import PdfReader, PdfWriter

from ..utils.batch import BatchRunner, CancelToken, raise_if_cancelled
from ..utils.file_scanner import PdfFile
from ..utils.naming import unique_path
from ..utils.output_paths import compute_output_path, has_multiple_roots
from ..utils.page_ranges import parse_page_ranges
from ..utils.paths import ensure_dir

DEFAULT_OUTPUT_FOLDER_NAME = "PDFs_Girados"
VALID_ANGLES = (90, 180, 270)


def _open_reader(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("PDF protegido por senha") from exc
    return reader


def rotate_one(
    pdf_file: PdfFile,
    dest_root: Path,
    angle: int,
    pages_spec: Optional[str],
    keep_structure: bool,
    multiple_roots: bool,
    token: CancelToken,
) -> Path:
    raise_if_cancelled(token)

    if angle not in VALID_ANGLES:
        raise RuntimeError(f"Ângulo inválido: {angle}")

    try:
        reader = _open_reader(pdf_file.path)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Não foi possível abrir o PDF: {exc}") from exc

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise RuntimeError("O PDF não possui páginas.")

    if pages_spec and pages_spec.strip():
        pages_to_rotate = set(parse_page_ranges(pages_spec, total_pages))
    else:
        pages_to_rotate = set(range(1, total_pages + 1))

    writer = PdfWriter()
    for index, page in enumerate(reader.pages, start=1):
        raise_if_cancelled(token)
        if index in pages_to_rotate:
            page.rotate(angle)
        writer.add_page(page)

    out_path = compute_output_path(pdf_file, dest_root, keep_structure, multiple_roots)
    ensure_dir(out_path.parent)
    out_path = unique_path(out_path)

    with open(out_path, "wb") as handle:
        writer.write(handle)

    return out_path


def run_rotate_batch(
    files: List[PdfFile],
    dest_root: Path,
    angle: int,
    pages_spec: Optional[str],
    keep_structure: bool,
    on_progress,
    on_done,
) -> BatchRunner:
    """Cria e inicia um BatchRunner para a ferramenta Girar páginas."""
    multiple_roots = has_multiple_roots(files)
    ensure_dir(dest_root)

    def process_one(pdf_file: PdfFile, token: CancelToken) -> None:
        rotate_one(pdf_file, dest_root, angle, pages_spec, keep_structure, multiple_roots, token)

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
