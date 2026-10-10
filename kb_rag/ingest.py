"""自动入库：解析 → 分类打标 → 切片 → 向量化 → 写入本地库。"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Iterable

from kb_rag import store
from kb_rag.chunker import chunk_document
from kb_rag.classifier import classify_document
from kb_rag.embedder import embed_texts, get_embedder
from kb_rag.text_extractor import extract_text, is_supported


def _doc_id(path: Path) -> str:
    st = path.stat()
    raw = f"{path.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def _archive_doc(cfg: dict, src: Path, doc_id: str) -> Path:
    docs_dir = Path(cfg["kb_path"]) / "docs" / doc_id
    docs_dir.mkdir(parents=True, exist_ok=True)
    dest = docs_dir / src.name
    shutil.copy2(src, dest)
    return dest


def _index_append(cfg: dict, entry: dict) -> None:
    index_path = Path(cfg["kb_path"]) / "index.json"
    records = []
    if index_path.exists():
        try:
            records = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            records = []
    records.append(entry)
    index_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _collect_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_file():
            if is_supported(p):
                files.append(p)
            else:
                print(f"[warn] 不支持的文件类型: {p}")
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and is_supported(child):
                    files.append(child)
    return files


def run_ingest(cfg: dict, paths: list[Path], trusted: bool = False, force_domain: str | None = None) -> dict:
    files = _collect_files(paths)
    if not files:
        return {"status": "no-files", "processed": 0, "notes": ["没有找到可解析文档"]}

    model = get_embedder(cfg["embedding_model"])
    now = dt.datetime.now().isoformat(timespec="seconds")
    summary = {"status": "ok", "processed": 0, "docs": [], "total_chunks": 0}

    for src in files:
        text = extract_text(src)
        if not text.strip():
            summary["docs"].append({"file": str(src), "status": "empty", "reason": "无可提取文本（扫描件需OCR）"})
            continue

        tags = classify_document(src, text, cfg, embed_model=model, force_domain=force_domain)
        doc_id = _doc_id(src)
        archived = _archive_doc(cfg, src, doc_id)

        if not tags["domain"]:
            print(f"[warn] {src.name}: 领域自动判定不确定，进入待审核")
        if tags["security_level"] == "机密":
            print(f"[warn] {src.name}: 检测到机密关键词，请人工复核密级")

        chunks = chunk_document(text, tags["domain"], cfg.get("chunking", {}))
        if not chunks:
            summary["docs"].append({"file": str(src), "status": "empty", "reason": "切片为空"})
            continue

        ids: list[str] = []
        docs: list[str] = []
        metadatas: list[dict] = []
        for i, chunk in enumerate(chunks):
            cid = f"{doc_id}:{i}"
            ids.append(cid)
            docs.append(chunk)
            meta = {
                "source_doc_id": doc_id,
                "file_name": src.name,
                "source_path": str(archived),
                "chunk_index": i,
                "inserted_at": now,
                "status": "active" if trusted else "pending",
            }
            meta.update(tags)
            metadatas.append(meta)

        embeddings = embed_texts(model, docs)
        store.upsert(cfg, ids, docs, embeddings, metadatas)

        index_entry = {
            "doc_id": doc_id,
            "file_name": src.name,
            "source_path": str(archived),
            "domain": tags["domain"],
            "domain_label": tags["domain_label"],
            "chunks": len(chunks),
            "status": "active" if trusted else "pending",
            "inserted_at": now,
        }
        _index_append(cfg, index_entry)

        summary["processed"] += 1
        summary["total_chunks"] += len(chunks)
        summary["docs"].append({
            "file": str(src),
            "status": "ok" if tags["domain"] else "pending-review-domain",
            "domain": tags["domain"] or "未定",
            "audience": tags["audience"] or "未定",
            "security_level": tags["security_level"] or "未定",
            "chunks": len(chunks),
        })
    return summary