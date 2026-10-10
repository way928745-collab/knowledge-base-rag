"""本地向量模型封装（fastembed + ONNX，不依赖 torch）。"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

_model = None


def get_embedder(model_name: str):
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        print(f"[embed] 加载本地模型: {model_name}")
        _model = TextEmbedding(model_name=model_name)
    return _model


def embed_texts(model, texts: list[str], batch_size: int = 32) -> list[list[float]]:
    if not texts:
        return []
    out: list[list[float]] = []
    for vec in model.embed(texts, batch_size=batch_size):
        out.append(np.asarray(vec).tolist())
    return out


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (float(np.linalg.norm(a)) * float(np.linalg.norm(b))) or 1e-9
    return float(float(np.dot(a, b)) / denom)