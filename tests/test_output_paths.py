from pathlib import Path

from src.utils.file_scanner import PdfFile
from src.utils.output_paths import compute_output_path, has_multiple_roots


def test_compute_output_path_preserves_relative_structure(tmp_path):
    root = tmp_path / "Leis"
    file_path = root / "2026" / "Janeiro" / "Lei001.pdf"
    pdf_file = PdfFile(path=file_path, root=root)

    dest = tmp_path / "Saida" / "PDFs_Invertidos"
    result = compute_output_path(pdf_file, dest, keep_structure=True, multiple_roots=False)

    assert result == dest / "2026" / "Janeiro" / "Lei001.pdf"


def test_compute_output_path_flat_when_structure_disabled(tmp_path):
    root = tmp_path / "Leis"
    file_path = root / "Janeiro" / "Lei001.pdf"
    pdf_file = PdfFile(path=file_path, root=root)

    dest = tmp_path / "Saida"
    result = compute_output_path(pdf_file, dest, keep_structure=False, multiple_roots=False)

    assert result == dest / "Lei001.pdf"


def test_compute_output_path_manual_file_goes_to_root_of_dest(tmp_path):
    pdf_file = PdfFile(path=tmp_path / "Lei001.pdf", root=None)
    dest = tmp_path / "Saida"
    result = compute_output_path(pdf_file, dest, keep_structure=True, multiple_roots=False)
    assert result == dest / "Lei001.pdf"


def test_multiple_roots_are_namespaced_to_avoid_collisions(tmp_path):
    root_a = tmp_path / "Leis"
    root_b = tmp_path / "Portarias"
    file_a = PdfFile(path=root_a / "Doc.pdf", root=root_a)
    file_b = PdfFile(path=root_b / "Doc.pdf", root=root_b)

    assert has_multiple_roots([file_a, file_b]) is True

    dest = tmp_path / "Saida"
    out_a = compute_output_path(file_a, dest, keep_structure=True, multiple_roots=True)
    out_b = compute_output_path(file_b, dest, keep_structure=True, multiple_roots=True)

    assert out_a == dest / "Leis" / "Doc.pdf"
    assert out_b == dest / "Portarias" / "Doc.pdf"
    assert out_a != out_b


def test_has_multiple_roots_false_for_single_root(tmp_path):
    root = tmp_path / "Leis"
    files = [PdfFile(path=root / f"{i}.pdf", root=root) for i in range(3)]
    assert has_multiple_roots(files) is False
