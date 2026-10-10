"""从常见办公文档提取纯文本。"""
from __future__ import annotations

import re
from pathlib import Path

SUPPORTED_SUFFIXES = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".md",
    ".markdown",
    ".txt",
    ".csv",
    ".html",
    ".htm",
    ".json",
    ".yaml",
    ".yml",
}
MAX_TEXT_CHARS = 500_000


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_pdf(path: Path, max_chars: int) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[str] = []
    used = 0
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if used >= max_chars:
            break
        take = min(len(text), max_chars - used)
        pages.append(f"\n[第{i}页]\n{text[:take]}")
        used += take
    return "\n".join(pages)


def _extract_docx(path: Path, max_chars: int) -> str:
    from docx import Document

    doc = Document(str(path))
    blocks: list[str] = []
    used = 0
    for para in doc.paragraphs:
        t = para.text.strip()
        if not t or used >= max_chars:
            continue
        take = min(len(t), max_chars - used)
        blocks.append(t[:take])
        used += take
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells and used < max_chars:
                line = " | ".join(cells)
                take = min(len(line), max_chars - used)
                blocks.append(line[:take])
                used += take
    return "\n".join(blocks)


def _extract_xlsx(path: Path, max_chars: int) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), read_only=True, data_only=True)
    blocks: list[str] = []
    used = 0
    for sheet in wb.worksheets:
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            vals = ["" if v is None else str(v).strip() for v in row]
            if any(vals):
                rows.append(" | ".join(vals))
        text = f"\n[工作表:{sheet.title}]\n" + "\n".join(rows)
        if used >= max_chars:
            break
        take = min(len(text), max_chars - used)
        blocks.append(text[:take])
        used += take
    return "\n".join(blocks)


def _extract_pptx(path: Path, max_chars: int) -> str:
    from pptx import Presentation

    prs = Presentation(str(path))
    blocks: list[str] = []
    used = 0
    for idx, slide in enumerate(prs.slides, start=1):
        lines: list[str] = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            t = "\n".join(p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip())
            if t:
                lines.append(t)
        if not lines:
            continue
        text = f"\n[幻灯片{idx}]\n" + "\n".join(lines)
        if used >= max_chars:
            break
        take = min(len(text), max_chars - used)
        blocks.append(text[:take])
        used += take
    return "\n".join(blocks)


def _extract_plain(path: Path, max_chars: int) -> str:
    text = _read_text(path)
    if path.suffix.lower() in (".html", ".htm"):
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
    return text[:max_chars]


def extract_text(path: Path, max_chars: int = MAX_TEXT_CHARS) -> str:
    """返回可检索纯文本；不支持或解析失败时返回空字符串。"""
    suffix = path.suffix.lower()
    try:
        if not path.exists() or not path.is_file():
            return ""
        if not path.read_bytes():
            return ""
        if suffix == ".pdf":
            return _extract_pdf(path, max_chars)
        if suffix == ".docx":
            return _extract_docx(path, max_chars)
        if suffix == ".xlsx":
            return _extract_xlsx(path, max_chars)
        if suffix == ".pptx":
            return _extract_pptx(path, max_chars)
        return _extract_plain(path, max_chars)
    except Exception as exc:  # 单个坏文档不影响整个批次
        print(f"[warn] 无法解析 {path.name}: {exc}")
        return ""


def is_supported(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES