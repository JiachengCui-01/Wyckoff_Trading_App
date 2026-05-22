from __future__ import annotations

import csv
import json
import pickle
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from ai_backend.config import EMBEDDING_MODEL, QA_DATA_PATH, RAG_INDEX_DIR


TOKEN_RE = re.compile(r"[a-z0-9.-]+", re.I)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text).lower())


def main() -> None:
    RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    documents = []
    with QA_DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            question = row.get("Questions") or row.get("question") or ""
            answer = row.get("Answers") or row.get("answer") or ""
            label = row.get("Label") or row.get("label") or "General"
            if not question.strip() or not answer.strip():
                continue
            documents.append(
                {
                    "id": f"qa_{idx}",
                    "question": question.strip(),
                    "answer": answer.strip(),
                    "label": label.strip() or "General",
                }
            )

    texts = [f"{doc['question']} {doc['answer']} {doc['label']}" for doc in documents]
    tokenized = [tokenize(text) for text in texts]
    bm25 = BM25Okapi(tokenized)
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    (RAG_INDEX_DIR / "documents.json").write_text(json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(RAG_INDEX_DIR / "embeddings.npy", embeddings)
    with (RAG_INDEX_DIR / "bm25.pkl").open("wb") as handle:
        pickle.dump(bm25, handle)

    print(f"Built RAG index with {len(documents)} documents at {RAG_INDEX_DIR}")


if __name__ == "__main__":
    main()

