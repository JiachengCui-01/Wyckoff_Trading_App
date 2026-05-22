from __future__ import annotations

import json
import math
import pickle
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import EMBEDDING_MODEL, RAG_INDEX_DIR, RETRIEVAL_POOL
from .schemas import RagContext


TOKEN_RE = re.compile(r"[a-z0-9.-]+", re.I)


@dataclass
class RagDocument:
    id: str
    question: str
    answer: str
    label: str


class HybridRagStore:
    def __init__(self, index_dir: Path = RAG_INDEX_DIR) -> None:
        self.index_dir = index_dir
        self.documents: list[RagDocument] = []
        self.embeddings: np.ndarray | None = None
        self.bm25 = None
        self.embedder = None
        self.reranker = None
        self.loaded = False

    def load(self) -> None:
        if self.loaded:
            return
        docs_path = self.index_dir / "documents.json"
        embeddings_path = self.index_dir / "embeddings.npy"
        bm25_path = self.index_dir / "bm25.pkl"
        if not docs_path.exists() or not embeddings_path.exists() or not bm25_path.exists():
            raise RuntimeError(
                "RAG index is missing. Run `python scripts/build_rag_index.py` before starting the LLaMA backend."
            )

        raw_docs = json.loads(docs_path.read_text(encoding="utf-8"))
        self.documents = [RagDocument(**item) for item in raw_docs]
        self.embeddings = np.load(embeddings_path)
        with bm25_path.open("rb") as handle:
            self.bm25 = pickle.load(handle)
        self.loaded = True

    def search(self, query: str, top_k: int = 5) -> list[RagContext]:
        self.load()
        assert self.embeddings is not None
        assert self.bm25 is not None

        bm25_candidates = self._bm25_search(query, RETRIEVAL_POOL)
        dense_candidates = self._dense_search(query, RETRIEVAL_POOL)
        scores: dict[int, float] = {}

        for rank, (idx, score) in enumerate(bm25_candidates):
            scores[idx] = max(scores.get(idx, 0.0), normalize_score(score) * 0.45 + rank_bonus(rank))
        for rank, (idx, score) in enumerate(dense_candidates):
            scores[idx] = scores.get(idx, 0.0) + normalize_score(score) * 0.45 + rank_bonus(rank)

        overlap_tokens = set(tokenize(query))
        for idx in list(scores):
            doc = self.documents[idx]
            doc_tokens = set(tokenize(f"{doc.question} {doc.answer} {doc.label}"))
            if overlap_tokens:
                scores[idx] += len(overlap_tokens & doc_tokens) / len(overlap_tokens) * 0.1

        reranked = self._cross_encoder_rerank(query, scores)
        return [self._to_context(idx, score) for idx, score in reranked[:top_k]]

    def _bm25_search(self, query: str, limit: int) -> list[tuple[int, float]]:
        tokenized = tokenize(query)
        scores = self.bm25.get_scores(tokenized)
        indices = np.argsort(scores)[::-1][:limit]
        return [(int(idx), float(scores[idx])) for idx in indices if scores[idx] > 0]

    def _dense_search(self, query: str, limit: int) -> list[tuple[int, float]]:
        if self.embedder is None:
            from sentence_transformers import SentenceTransformer

            self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        query_embedding = self.embedder.encode([query], normalize_embeddings=True)[0]
        dense = self.embeddings
        if dense.ndim != 2:
            return []
        scores = dense @ query_embedding
        indices = np.argsort(scores)[::-1][:limit]
        return [(int(idx), float(scores[idx])) for idx in indices]

    def _cross_encoder_rerank(self, query: str, scores: dict[int, float]) -> list[tuple[int, float]]:
        if not scores:
            return []
        try:
            if self.reranker is None:
                from sentence_transformers import CrossEncoder
                from .config import RERANK_MODEL

                self.reranker = CrossEncoder(RERANK_MODEL)
            indices = list(scores)
            pairs = [(query, self.documents[idx].question) for idx in indices]
            cross_scores = self.reranker.predict(pairs)
            for idx, cross_score in zip(indices, cross_scores):
                scores[idx] = scores[idx] * 0.55 + float(cross_score) * 0.45
        except Exception:
            pass
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)

    def _to_context(self, idx: int, score: float) -> RagContext:
        doc = self.documents[idx]
        return RagContext(
            question=doc.question,
            answer=doc.answer,
            label=doc.label,
            score=round(float(score), 4),
        )


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text).lower())


def normalize_score(score: float) -> float:
    if not math.isfinite(score):
        return 0.0
    return 1 / (1 + math.exp(-score))


def rank_bonus(rank: int) -> float:
    return 0.08 / (rank + 1)


rag_store = HybridRagStore()

