# Wyckoff Trading

Wyckoff trading analysis web app with a Vercel frontend and an optional local/GPU LLaMA+LoRA chat backend.

## Architecture

- Vercel serves the existing `index.html` UI and lightweight serverless API.
- `api/chat.js` first proxies chat requests to `LLAMA_BACKEND_URL` when it is configured.
- If the LLaMA backend is unavailable, `api/chat.js` keeps the lightweight CSV/stock fallback so the hosted demo still works.
- `ai_backend/` is the main AI path: LLaMA + LoRA intent routing, hybrid RAG, rerank, and `stock_analysis` skill.
- `api/analyze.js` and `api/skills/stockAnalysis.js` keep the current Vercel stock-analysis page working.

Vercel is the display/proxy layer. LLaMA+LoRA runs in Python on a local machine, lab server, or cloud GPU host.

## Chat Flow

1. User asks a question in the existing ChatBot UI.
2. Vercel `/api/chat` proxies to FastAPI when `LLAMA_BACKEND_URL` is available.
3. FastAPI uses LLaMA+LoRA to classify intent:
   - `rag`: hybrid BM25 + dense embedding retrieval, top-k, rerank, LLaMA answer generation.
   - `stock_analysis`: structured ticker/range/intent input, Python stock skill, LLaMA answer generation.
   - `fallback`: open-ended LLaMA answer generation for general questions.
4. The UI displays the returned answer without layout changes.

## Training

Default inference does not require retraining. Users should load the already trained LoRA adapter when it is available.

To train or reproduce the LoRA adapter on a GPU machine:

```bash
python scripts/train_lora.py \
  --base-model meta-llama/Llama-2-7b-hf \
  --output-dir models/llama_wyckoff_lora \
  --epochs 2 \
  --batch-size 1 \
  --gradient-accumulation-steps 8
```

The script reads `data/wyckoff_all_labels_combined.csv`, creates RAG-answer and intent-classification samples, and saves the adapter to `models/llama_wyckoff_lora/`.

For Colab, save the output to Google Drive:

```bash
python scripts/train_lora.py \
  --output-dir /content/drive/MyDrive/wyckoff_models/llama_wyckoff_lora
```

## Chat_Bot Interface
With LLaMA:
<img width="975" height="528" alt="image" src="https://github.com/user-attachments/assets/4a45f6c7-5574-4beb-a801-638ee08702a6" />

Without LLaMA:
<img width="1280" height="698" alt="image" src="https://github.com/user-attachments/assets/4393e678-a94e-4c5a-97dc-5c2275deeb76" />

## Stock Analysis Interface
<img width="1280" height="697" alt="image" src="https://github.com/user-attachments/assets/446fed7e-0f66-4975-a0de-6870bf4853ed" />
<img width="1280" height="697" alt="image" src="https://github.com/user-attachments/assets/7d1e09ac-3547-4d6b-95c3-de3e0d4af618" />
<img width="1280" height="696" alt="image" src="https://github.com/user-attachments/assets/89222f6d-a633-437a-ad4e-65f10d3869fb" />
<img width="1280" height="699" alt="image" src="https://github.com/user-attachments/assets/19d7e907-bd9e-45ed-aac1-e6c2b1e2efac" />

## Notes

This app is for educational analysis only and is not financial advice.
