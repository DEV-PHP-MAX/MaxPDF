"""Ferramenta: Imagens → PDF.

Converte uma sequência ordenada de imagens (JPG, JPEG, PNG, WEBP, BMP,
TIFF) em um único arquivo PDF, preservando a ordem apresentada pelo
usuário. Imagens com transparência recebem um fundo branco antes da
conversão, conforme especificado.
"""

from __future__ import annotations

import io
import threading
import time
from pathlib import Path
from typing import Callable, List

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from ..utils.batch import BatchError, BatchResult, CancelToken
from ..utils.naming import unique_path
from ..utils.paths import ensure_dir

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
DEFAULT_OUTPUT_NAME = "Imagens_Convertidas.pdf"


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    """Garante um resultado RGB, aplicando fundo branco em imagens com
    canal alfa/transparência (RGBA, LA, ou paleta com transparência)."""
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.convert("RGBA").split()[-1]
        background.paste(img.convert("RGBA"), mask=alpha)
        return background
    if img.mode == "P" and "transparency" in img.info:
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _image_to_pdf_bytes(image_path: Path) -> bytes:
    with Image.open(image_path) as raw:
        raw.load()
        transposed = ImageOps.exif_transpose(raw)
        img = _flatten_to_rgb(transposed if transposed is not None else raw)
        buffer = io.BytesIO()
        img.save(buffer, format="PDF")
        return buffer.getvalue()


class ImagesToPdfRunner(threading.Thread):
    def __init__(
        self,
        image_paths: List[Path],
        output_path: Path,
        on_progress: Callable[[int, int, str], None],
        on_done: Callable[[BatchResult], None],
    ) -> None:
        super().__init__(daemon=True)
        self._image_paths = image_paths
        self._output_path = output_path
        self._on_progress = on_progress
        self._on_done = on_done
        self._cancel_token = CancelToken()

    def cancel(self) -> None:
        self._cancel_token.cancel()

    def run(self) -> None:
        start = time.monotonic()
        total = len(self._image_paths)
        result = BatchResult(total=total, output_dir=str(self._output_path.parent))
        writer = PdfWriter()

        for index, image_path in enumerate(self._image_paths, start=1):
            if self._cancel_token.is_cancelled():
                result.cancelled = True
                break

            self._on_progress(index, total, image_path.name)

            try:
                pdf_bytes = _image_to_pdf_bytes(image_path)
                reader = PdfReader(io.BytesIO(pdf_bytes))
                for page in reader.pages:
                    writer.add_page(page)
                result.succeeded += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(BatchError(item_label=image_path.name, message=str(exc)))

        if result.succeeded > 0:
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


def run_images_to_pdf(
    image_paths: List[Path],
    output_path: Path,
    on_progress,
    on_done,
) -> ImagesToPdfRunner:
    runner = ImagesToPdfRunner(
        image_paths=image_paths, output_path=output_path, on_progress=on_progress, on_done=on_done
    )
    runner.start()
    return runner
