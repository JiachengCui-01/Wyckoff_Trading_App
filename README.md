# Wyckoff Trading

AI-assisted Wyckoff trading analysis web app.

This repository now contains two runnable versions:

- `public/` + `api/`: Vercel-ready web app with a dark trading UI, chatbot retrieval, live stock analysis, Wyckoff event detection, phase detection, and simple backtesting.
- `app.py`: original Streamlit prototype kept for local experimentation with the heavier Python stack.

## Vercel App

The deployed app is served from `public/index.html` and uses Vercel serverless functions:

- `api/chat.js` reads `data/wyckoff_all_labels_combined.csv` and returns top matching Wyckoff Q&A context.
- `api/analyze.js` fetches Yahoo Finance chart data, detects Wyckoff events such as `SC`, `BC`, `SP`, `UT`, `SOS`, and `SOW`, estimates the current phase, and returns chart/backtest data.

## Local Check

```bash
npx vercel dev --listen 127.0.0.1:3000 --yes
```

Open `http://127.0.0.1:3000`.

## Deploy

```bash
npx vercel deploy --prod
```

The project is linked to Vercel project `wyckoff_trader_app`.

## Notes

This app is for educational analysis only and is not financial advice. The Vercel version intentionally avoids shipping the full LLaMA/LoRA runtime because serverless deployment cannot host a local 7B model. The architecture still follows the technical document's frontend/API/RAG/analysis flow, using a lightweight retrieval implementation that runs reliably on Vercel.
