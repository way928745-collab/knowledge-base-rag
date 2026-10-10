"""自动分类和打标：领域 + 用途 + 受众 + 密级 + 时间/版本。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from kb_rag.embedder import cosine_similarity


def _count_keywords(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in lower)


def classify_domain(text: str, cfg: dict, embed_model=None) -> tuple[str, str]:
    """返回 (domain_key, domain_label)；无把握时为空字符串。"""
    domains = cfg["domains"]
    kw_scores = {key: _count_keywords(text, info.get("keywords", [])) for key, info in domains.items()}
    domain = max(kw_scores, key=kw_scores.get)
    max_kw = kw_scores[domain]

    if max_kw >= 2:
        return domain, domains[domain]["label"]

    # 关键词证据不足时，用向量模型和领域描述做相似度判断
    if embed_model is not None and text.strip():
        desc_texts = [f"{info['label']}：{info['description']}" for info in domains.values()]
        try:
            doc_vec = next(embed_model.embed([text[:2000]]))
            desc_vecs = list(embed_model.embed(desc_texts))
            scores = {
                key: cosine_similarity(np.asarray(doc_vec), np.asarray(vec))
                for key, vec in zip(domains, desc_vecs)
            }
            best = max(scores, key=scores.get)
            if scores[best] >= 0.30:
                return best, domains[best]["label"]
        except Exception as exc:
            print(f"[warn] 领域向量分类失败: {exc}")
    return domain if max_kw >= 1 else "", (domains.get(domain, {}).get("label", "") if max_kw >= 1 else "")


def _best_tag(text: str, mapping: dict[str, list[str]]) -> str:
    best_key = ""
    best_score = 0
    for key, keywords in mapping.items():
        score = _count_keywords(text, keywords)
        if score > best_score:
            best_key, best_score = key, score
    return best_key


def _extract_dates(text: str, patterns: list[str]) -> list[str]:
    found: list[str] = []
    for pat in patterns:
        for m in re.finditer(pat, text[:4000]):
            groups = [g for g in m.groups() if g]
            if len(groups) == 3:
                found.append(f"{int(groups[0]):04d}-{int(groups[1]):02d}-{int(groups[2]):02d}")
            elif len(groups) == 2:
                found.append(f"{int(groups[0]):04d}-{int(groups[1]):02d}")
    return found


def auto_tag(text: str, filename: str, cfg: dict) -> dict[str, str]:
    auto = cfg.get("auto_tags", {})
    usage = _best_tag(text, auto.get("usage_type", {}))
    audience = _best_tag(text, auto.get("audience", {}))
    security = _best_tag(text, auto.get("security_level", {}))

    dates = _extract_dates(text, cfg.get("date_patterns", []))
    effective = dates[0] if dates else ""
    expire = ""

    ver_match = re.search(cfg.get("version_pattern", r"[vV](\d+\.\d+\.\d+)"), filename + " " + text[:2000])
    version = ver_match.group(1) if ver_match else ""

    return {
        "usage_type": usage,
        "audience": audience,
        "security_level": security,
        "effective_time": effective,
        "expire_time": expire,
        "product_line": "",
        "doc_version": version,
    }


def classify_document(path: Path, text: str, cfg: dict, embed_model=None, force_domain: str | None = None) -> dict:
    domain, label = classify_domain(text, cfg, embed_model)
    if force_domain and force_domain in cfg["domains"]:
        domain, label = force_domain, cfg["domains"][force_domain]["label"]
    tags = auto_tag(text, path.name, cfg)
    tags["domain"] = domain
    tags["domain_label"] = label
    return tags