from pathlib import Path

from src.utils.file_scanner import FileQueue, PdfFile, find_pdfs_in_folder, is_pdf_filename


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4")


def test_is_pdf_filename_case_insensitive():
    assert is_pdf_filename("Lei001.pdf")
    assert is_pdf_filename("Lei001.PDF")
    assert not is_pdf_filename("Lei001.txt")


def test_is_pdf_filename_ignores_temp_files():
    assert not is_pdf_filename("~$Lei001.pdf")
    assert not is_pdf_filename("Lei001.pdf.tmp")


def test_find_pdfs_recursive(tmp_path):
    _touch(tmp_path / "Lei 001.pdf")
    _touch(tmp_path / "Lei 002.pdf")
    _touch(tmp_path / "Janeiro" / "Lei 003.pdf")
    _touch(tmp_path / "Janeiro" / "Lei 004.pdf")
    _touch(tmp_path / "Fevereiro" / "Lei 005.pdf")
    _touch(tmp_path / "Fevereiro" / "Antigos" / "Lei 006.pdf")
    _touch(tmp_path / "Fevereiro" / "Antigos" / "Lei 007.pdf")
    _touch(tmp_path / "nao_e_pdf.txt")

    found = list(find_pdfs_in_folder(tmp_path, recursive=True))
    assert len(found) == 7


def test_find_pdfs_non_recursive(tmp_path):
    _touch(tmp_path / "Lei 001.pdf")
    _touch(tmp_path / "Sub" / "Lei 002.pdf")

    found = list(find_pdfs_in_folder(tmp_path, recursive=False))
    assert len(found) == 1


def test_file_queue_deduplicates_manual_then_folder(tmp_path):
    pdf_path = tmp_path / "Lei001.pdf"
    _touch(pdf_path)

    queue = FileQueue()
    queue.add_manual_files([pdf_path])
    assert len(queue) == 1

    # Adicionar novamente através de uma "pasta" não deve duplicar.
    added = queue.add(PdfFile(path=pdf_path, root=tmp_path))
    assert added is False
    assert len(queue) == 1


def test_file_queue_add_many_counts_only_new():
    queue = FileQueue()
    a = PdfFile(path=Path("/tmp/a.pdf"))
    b = PdfFile(path=Path("/tmp/b.pdf"))
    assert queue.add_many([a, b, a]) == 2
    assert len(queue) == 2


def test_file_queue_remove_and_clear():
    queue = FileQueue()
    queue.add_many([PdfFile(path=Path(f"/tmp/{i}.pdf")) for i in range(5)])
    queue.remove_indices([1, 3])
    assert len(queue) == 3
    queue.clear()
    assert len(queue) == 0


def test_file_queue_move_to():
    queue = FileQueue()
    queue.add_many([PdfFile(path=Path(f"/tmp/{i}.pdf")) for i in range(5)])
    queue.move_to(4, 0)
    names = [f.path.name for f in queue.items]
    assert names == ["4.pdf", "0.pdf", "1.pdf", "2.pdf", "3.pdf"]


def test_pdf_file_relative_display_path_preserves_structure(tmp_path):
    root = tmp_path / "Documentos"
    nested = root / "Janeiro" / "Lei001.pdf"
    _touch(nested)

    pdf_file = PdfFile(path=nested, root=root)
    assert pdf_file.display_path == str(Path("Janeiro") / "Lei001.pdf")
    assert pdf_file.root_label == "Documentos"


def test_pdf_file_manual_display_path_is_just_name(tmp_path):
    path = tmp_path / "Lei001.pdf"
    _touch(path)
    pdf_file = PdfFile(path=path, root=None)
    assert pdf_file.display_path == "Lei001.pdf"
