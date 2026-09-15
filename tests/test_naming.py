from src.utils.naming import unique_dir, unique_path


def test_unique_path_returns_same_when_not_existing(tmp_path):
    target = tmp_path / "Lei001.pdf"
    assert unique_path(target) == target


def test_unique_path_increments_suffix(tmp_path):
    target = tmp_path / "Lei001.pdf"
    target.write_bytes(b"%PDF-1.4")

    first_alt = unique_path(target)
    assert first_alt == tmp_path / "Lei001_1.pdf"

    first_alt.write_bytes(b"%PDF-1.4")
    second_alt = unique_path(target)
    assert second_alt == tmp_path / "Lei001_2.pdf"


def test_unique_path_preserves_extension(tmp_path):
    target = tmp_path / "Documento.PDF"
    target.write_bytes(b"%PDF-1.4")
    alt = unique_path(target)
    assert alt.suffix == ".PDF"
    assert alt.stem == "Documento_1"


def test_unique_dir_increments(tmp_path):
    target = tmp_path / "PDFs_Invertidos"
    target.mkdir()
    alt = unique_dir(target)
    assert alt == tmp_path / "PDFs_Invertidos_1"
