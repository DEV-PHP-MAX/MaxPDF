from src.utils.natural_sort import natural_sort_key, sort_natural, sort_paths_natural
from pathlib import Path


def test_natural_sort_basic_numbers():
    names = ["Lei 1.pdf", "Lei 10.pdf", "Lei 2.pdf", "Lei 20.pdf", "Lei 3.pdf"]
    expected = ["Lei 1.pdf", "Lei 2.pdf", "Lei 3.pdf", "Lei 10.pdf", "Lei 20.pdf"]
    assert sort_natural(names) == expected


def test_natural_sort_is_case_insensitive():
    names = ["banana.pdf", "Apple.pdf", "cherry.pdf"]
    assert sort_natural(names) == ["Apple.pdf", "banana.pdf", "cherry.pdf"]


def test_natural_sort_reverse():
    names = ["Lei 1.pdf", "Lei 2.pdf", "Lei 10.pdf"]
    assert sort_natural(names, reverse=True) == ["Lei 10.pdf", "Lei 2.pdf", "Lei 1.pdf"]


def test_natural_sort_key_orders_numeric_blocks_correctly():
    assert natural_sort_key("Lei 2.pdf") < natural_sort_key("Lei 10.pdf")
    assert natural_sort_key("Lei 002.pdf") < natural_sort_key("Lei 10.pdf")


def test_sort_paths_natural():
    paths = [Path("Lei 10.pdf"), Path("Lei 2.pdf"), Path("Lei 1.pdf")]
    result = sort_paths_natural(paths)
    assert [p.name for p in result] == ["Lei 1.pdf", "Lei 2.pdf", "Lei 10.pdf"]


def test_natural_sort_mixed_with_no_numbers():
    names = ["Fevereiro.pdf", "Janeiro.pdf", "Dezembro.pdf"]
    assert sort_natural(names) == ["Dezembro.pdf", "Fevereiro.pdf", "Janeiro.pdf"]
