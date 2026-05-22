#!/usr/bin/env bash
set -euo pipefail

cd /app

python3 - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu")
PY

if [ ! -f "data/rag_index/embeddings.npy" ] || [ ! -f "data/rag_index/documents.json" ] || [ ! -f "data/rag_index/bm25.pkl" ]; then
  echo "RAG index missing; building offline index..."
  python3 scripts/build_rag_index.py
fi

exec uvicorn ai_backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
