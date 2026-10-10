"""语义检索。"""
from __future__ import annotations

from kb_rag import store
from kb_rag.embedder import embed_texts, get_embedder


def run_query(cfg: dict, question: str, top_k: int | None = None, filters: dict | None = None) -> list[dict]:
    k = top_k or int(cfg.get("retrieval", {}).get("default_top_k", 5))
    model = get_embedder(cfg["embedding_model"])
    vectors = embed_texts(model, [question])
    result = store.query(cfg, vectors, top_k=k, filters=filters)

    items: list[dict] = []
    for i, doc_id in enumerate(result["ids"][0]):
        meta = result["metadatas"][0][i] or {}
        distance = float(result["distances"][0][i])
        items.append({
            "id": doc_id,
            "score": max(0.0, 1.0 - distance),
            "text": result["documents"][0][i],
            "source": meta.get("source_path", ""),
            "domain": meta.get("domain", ""),
            "domain_label": meta.get("domain_label", ""),
            "audience": meta.get("audience", ""),
            "security_level": meta.get("security_level", ""),
            "status": meta.get("status", ""),
            "doc_version": meta.get("doc_version", ""),
        })
    return items