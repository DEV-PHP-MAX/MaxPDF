import pytest

from src.utils.page_ranges import PageRangeError, format_page_list, parse_page_ranges


def test_parse_simple_range():
    assert parse_page_ranges("1-3,5,8-10", max_pages=10) == [1, 2, 3, 5, 8, 9, 10]


def test_parse_single_pages():
    assert parse_page_ranges("1,2,3", max_pages=5) == [1, 2, 3]


def test_parse_removes_duplicates_preserving_first_occurrence():
    assert parse_page_ranges("1,1-3,2", max_pages=5) == [1, 2, 3]


def test_parse_handles_reversed_range():
    assert parse_page_ranges("5-3", max_pages=10) == [3, 4, 5]


def test_parse_ignores_extra_whitespace():
    assert parse_page_ranges(" 1 - 3 , 5 ", max_pages=10) == [1, 2, 3, 5]


def test_parse_rejects_out_of_bounds_page():
    with pytest.raises(PageRangeError):
        parse_page_ranges("1-3,99", max_pages=10)


def test_parse_rejects_empty_spec():
    with pytest.raises(PageRangeError):
        parse_page_ranges("", max_pages=10)


def test_parse_rejects_garbage():
    with pytest.raises(PageRangeError):
        parse_page_ranges("abc", max_pages=10)


def test_parse_rejects_zero_or_negative():
    with pytest.raises(PageRangeError):
        parse_page_ranges("0-2", max_pages=10)


def test_format_page_list():
    assert format_page_list([1, 2, 3, 5, 8, 9, 10]) == "1,2,3,5,8,9,10"
