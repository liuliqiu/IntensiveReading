"""File format parsers: markdown stripping and reserved format handlers."""

import mistune

_UNSUPPORTED_FORMATS = {
    ".pdf": "PDF",
    ".docx": "Word",
    ".xlsx": "Excel",
    ".pptx": "PPT",
}


def strip_markdown(md_text: str) -> str:
    """Remove markdown formatting, returning plain text."""
    html = mistune.html(md_text)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def get_parser(extension: str):
    """Return a format-specific parse function (text -> plain_text),
    or raise ValueError for unsupported formats."""
    ext = extension.lower()
    if ext == ".md":
        return strip_markdown
    if ext in _UNSUPPORTED_FORMATS:
        raise ValueError(f"{_UNSUPPORTED_FORMATS[ext]} 格式暂未支持")
    raise ValueError(f"不支持的文件格式: {ext}")


# ── Reserved: future format handlers ──

def extract_text_from_pdf(file_path: str) -> str:
    """Extract plain text from a PDF file. (not implemented)"""
    raise NotImplementedError("PDF 格式暂未支持")


def extract_text_from_docx(file_path: str) -> str:
    """Extract plain text from a Word document. (not implemented)"""
    raise NotImplementedError("Word 格式暂未支持")


def extract_text_from_xlsx(file_path: str) -> str:
    """Extract plain text from an Excel spreadsheet. (not implemented)"""
    raise NotImplementedError("Excel 格式暂未支持")


def extract_text_from_pptx(file_path: str) -> str:
    """Extract plain text from a PowerPoint presentation. (not implemented)"""
    raise NotImplementedError("PPT 格式暂未支持")
