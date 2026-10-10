"""ChromaDB 本地向量库存取。"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Iterable

import chromadb


def _client(cfg: dict) -> chromadb.ClientAPI:
    chroma_dir = Path(cfg["kb_path"]) / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_dir))


def collection(cfg: dict) -> chromadb.Collection:
    return _client(cfg).get_or_create_collection(
        cfg["collection_name"],
        metadata={"hnsw:space": "cosine"},
    )


def upsert(cfg: dict, ids: list[str], documents: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
    col = collection(cfg)
    col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)


def build_where(filters: dict[str, Any] | None) -> dict[str, Any] | None:
    if not filters:
        return {"status": "active"}
    conditions = []
    for key, value in filters.items():
        if value == "":
            continue
        conditions.append({key: {"$eq": value}})
    if not conditions:
        return {"status": "active"}
    if len(conditions) == 1:
        return {list(conditions[0].keys())[0]: {"$eq": list(conditions[0].values())[0]["$eq"]}}
    if "status" not in filters:
        conditions.append({"status": {"$eq": "active"}})
    return {"$and": conditions}


def query(cfg: dict, query_embeddings: list[list[float]], top_k: int, filters: dict | None = None):
    where = build_where(filters)
    col = collection(cfg)
    return col.query(
        query_embeddings=query_embeddings,
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )


def get_by_where(cfg: dict, where: dict, limit: int = 1000) -> dict:
    col = collection(cfg)
    return col.get(where=where, limit=limit, include=["documents", "metadatas"])


def get_by_ids(cfg: dict, ids: list[str]) -> dict:
    col = collection(cfg)
    return col.get(ids=ids, include=["metadatas"])


def update_metadata(cfg: dict, ids: list[str], metadata: dict) -> None:
    if not ids:
        return
    col = collection(cfg)
    current = col.get(ids=ids, include=["metadatas"])
    metas = []
    for i, cid in enumerate(ids):
        base = dict(current["metadatas"][i] or {}) if i < len(current["metadatas"]) else {}
        base.update(metadata)
        metas.append(base)
    col.update(ids=ids, metadatas=metas)


def delete(cfg: dict, ids: list[str]) -> None:
    if not ids:
        return
    collection(cfg).delete(ids=ids)


def stats(cfg: dict) -> dict:
    col = collection(cfg)
    total = col.count()
    out = {"total_chunks": total, "by_status": {}, "missing_metadata": 0}
    for status in ("pending", "active", "rejected"):
        rows = col.get(where={"status": {"$eq": status}}, include=["metadatas"])
        out["by_status"][status] = len(rows["ids"])
        for meta in rows["metadatas"]:
            if not meta.get("domain") or not meta.get("audience"):
                out["missing_metadata"] += 1
    return out