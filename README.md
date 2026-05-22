# Wyckoff Trading

Wyckoff trading analysis web app with a Vercel frontend and an optional local/GPU LLaMA+LoRA chat backend.

## Architecture

- Vercel serves the existing `index.html` UI and lightweight serverless API.
- `api/chat.js` first proxies chat requests to `LLAMA_BACKEND_URL` when it is configured.
- If the LLaMA backend is unavailable, `api/chat.js` keeps the lightweight CSV/stock fallback so the hosted demo still works.
- `ai_backend/` is the main AI path: LLaMA + LoRA intent routing, hybrid RAG, rerank, and `stock_analysis` skill.
- `api/analyze.js` and `api/skills/stockAnalysis.js` keep the current Vercel stock-analysis page working.

Vercel is the display/proxy layer. LLaMA+LoRA runs in Python on a local machine, lab server, or cloud GPU host.

## Inference Setup

Install the Python backend dependencies:

```bash
pip install -r requirements-ai.txt
```

Prepare model files:

- Base model: configure `LLAMA_BASE_MODEL`, for example `meta-llama/Llama-2-7b-hf`.
- LoRA adapter: place the trained adapter at `models/llama_wyckoff_lora/` or set `LLAMA_LORA_PATH`.
- Do not commit base model or adapter weights to GitHub.

Build the offline RAG index once:

```bash
python scripts/build_rag_index.py
```

This creates:

- `data/rag_index/documents.json`
- `data/rag_index/embeddings.npy`
- `data/rag_index/bm25.pkl`

Run the LLaMA backend:

```bash
uvicorn ai_backend.main:app --host 127.0.0.1 --port 8000
```

For a structure-only smoke test without loading LLaMA, use:

```bash
set WYCKOFF_LLM_MOCK=1
uvicorn ai_backend.main:app --host 127.0.0.1 --port 8000
```

## Vercel / Frontend

Set the proxy target when running locally or deploying:

```bash
set LLAMA_BACKEND_URL=http://127.0.0.1:8000
```

The frontend still calls `/api/chat`. The Vercel function forwards to the LLaMA backend first, then falls back to the lightweight implementation if needed.

## Chat Flow

1. User asks a question in the existing ChatBot UI.
2. Vercel `/api/chat` proxies to FastAPI when `LLAMA_BACKEND_URL` is available.
3. FastAPI uses LLaMA+LoRA to classify intent:
   - `rag`: hybrid BM25 + dense embedding retrieval, top-k, rerank, LLaMA answer generation.
   - `stock_analysis`: structured ticker/range/intent input, Python stock skill, LLaMA answer generation.
   - `fallback`: English fallback message.
4. The UI displays the returned answer without layout changes.

## Training

Default inference does not require retraining. Users should load the already trained LoRA adapter.

Training or reproducing the LoRA adapter is a separate workflow and should output adapter files into `models/llama_wyckoff_lora/`.

## Notes

This app is for educational analysis only and is not financial advice.
