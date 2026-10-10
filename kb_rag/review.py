"""审核队列。"""
from __future__ import annotations

from kb_rag import store


def list_pending(cfg: dict, limit: int = 1000) -> list[dict]:
    result = store.get_by_where(cfg, {"status": {"$eq": "pending"}}, limit=limit)
    items = []
    for i, cid in enumerate(result["ids"]):
        meta = result["metadatas"][i] or {}
        items.append({
            "id": cid,
            "text": result["documents"][i][:400],
            "source": meta.get("source_path", ""),
            "domain": meta.get("domain", ""),
            "audience": meta.get("audience", ""),
            "security_level": meta.get("security_level", ""),
            "chunk_index": meta.get("chunk_index", ""),
        })
    return items


def set_status(cfg: dict, action: str, ids: list[str] | None) -> bool:
    if ids is None:
        pending = list_pending(cfg, limit=10000)
        ids = [it["id"] for it in pending]
    new_status = "active" if action == "approve" else "rejected"
    if not ids:
        print("没有匹配的切片")
        return True
    store.update_metadata(cfg, ids, {"status": new_status})
    print(f"已更新 {len(ids)} 条切片 -> {new_status}")
    return True