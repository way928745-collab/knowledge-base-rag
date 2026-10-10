"""维护：健康检查与过期清理。"""
from __future__ import annotations

import datetime as dt

from kb_rag import store


def _today() -> str:
    return dt.date.today().isoformat()


def check(cfg: dict) -> dict:
    return store.stats(cfg)


def prune(cfg: dict) -> int:
    today = _today()
    where = {
        "$and": [
            {"status": {"$eq": "active"}},
            {"expire_time": {"$lte": today}},
        ]
    }
    rows = store.get_by_where(cfg, where, limit=10000)
    ids = rows["ids"]
    if ids:
        store.delete(cfg, ids)
    return len(ids)