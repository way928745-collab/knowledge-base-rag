"""按领域配置切分文本。"""
from __future__ import annotations

import re


def _normalize(text: str) -> str:
    return re.sub(r"\r\n?", "\n", text).strip()


def chunk_text(text: str, max_chars: int, overlap: int = 0) -> list[str]:
    text = _normalize(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        # 尽量在小标题/换行处断开，避免长段落被切得很碎
        next_start = max(end - overlap, start + 1)
        if next_start >= end:
            break
        start = next_start
    return chunks


def chunk_document(text: str, domain: str, chunking: dict) -> list[str]:
    small_domains = set(chunking.get("small_domains", []))
    if domain in small_domains:
        return chunk_text(text, int(chunking["small_max_chars"]), int(chunking["small_overlap"]))
    return chunk_text(text, int(chunking["large_max_chars"]), int(chunking["large_overlap"]))