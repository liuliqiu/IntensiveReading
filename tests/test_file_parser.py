"""Tests for services/file_parser.py"""

import pytest
from services.file_parser import strip_markdown, get_parser


def test_strip_markdown_headers():
    result = strip_markdown("# Heading\n\nText")
    assert "Heading" in result
    assert "#" not in result


def test_strip_markdown_bold():
    result = strip_markdown("This is **bold** text")
    assert "**" not in result
    assert "bold" in result


def test_strip_markdown_links():
    result = strip_markdown("Click [here](http://example.com)")
    assert "here" in result
    assert "http://example.com" not in result
    assert "[" not in result


def test_strip_markdown_code():
    result = strip_markdown("Use `print()` function")
    assert "print()" in result
    assert "`" not in result


def test_strip_markdown_list():
    result = strip_markdown("- Item 1\n- Item 2")
    assert "Item 1" in result
    assert "Item 2" in result
    assert "-" not in result


def test_strip_markdown_image():
    result = strip_markdown("![alt](img.png)")
    assert "img.png" not in result


def test_strip_markdown_empty():
    result = strip_markdown("")
    assert result == ""


def test_get_parser_markdown():
    fn = get_parser(".md")
    assert fn is strip_markdown


def test_get_parser_markdown_uppercase():
    fn = get_parser(".MD")
    assert fn is strip_markdown


def test_get_parser_unsupported_format():
    for ext in [".pdf", ".docx", ".xlsx", ".pptx"]:
        with pytest.raises(ValueError, match="格式暂未支持"):
            get_parser(ext)


def test_get_parser_unknown():
    with pytest.raises(ValueError, match="不支持的文件格式"):
        get_parser(".xyz")
