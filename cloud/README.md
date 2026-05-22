# Cloud GPU LLaMA Backend

This folder contains provider-neutral instructions for running the `ai_backend` FastAPI service on a cloud GPU.

## Fastest Free Demo: Google Colab

Open the Colab notebook from GitHub:

```text
https://colab.research.google.com/github/JiachengCui-01/Wyckoff_Trading_App/blob/main/cloud/colab_llama_backend.ipynb
```

Use `Runtime > Change runtime type > T4 GPU`, run the notebook cells from top to bottom, and copy the generated Cloudflare tunnel URL into Vercel as `LLAMA_BACKEND_URL`.

Colab is good for demos, but the free runtime is temporary and the tunnel URL changes after restart. Use a paid GPU host for stable production service.

## Recommended GPU

- Minimum practical target for LLaMA 7B + LoRA 4-bit: NVIDIA GPU with 12GB VRAM.
- More comfortable: 16GB-24GB VRAM.
- Use Linux GPU hosts. Windows + bitsandbytes is less predictable.

## Required Secrets / Volumes

- `HF_TOKEN`: Hugging Face token with access to the selected LLaMA base model, if required.
- `LLAMA_BASE_MODEL`: default `meta-llama/Llama-2-7b-hf`.
- `LLAMA_LORA_PATH`: path to your trained LoRA adapter. Default inside the repo is `/app/models/llama_wyckoff_lora`.
- Mount or upload your LoRA adapter into the container at `/app/models/llama_wyckoff_lora`.

Do not commit base model or LoRA weights to GitHub.

## Build Image

From the repo root:

```bash
docker build -f Dockerfile.ai -t wyckoff-llama-backend .
```

## Run Container

```bash
docker run --gpus all -p 8000:8000 \
  -e HF_TOKEN=$HF_TOKEN \
  -e LLAMA_BASE_MODEL=meta-llama/Llama-2-7b-hf \
  -e LLAMA_LORA_PATH=/app/models/llama_wyckoff_lora \
  -v /path/to/llama_wyckoff_lora:/app/models/llama_wyckoff_lora \
  wyckoff-llama-backend
```

The startup script will:

1. Print CUDA availability.
2. Build `data/rag_index/*` if missing.
3. Start FastAPI on port `8000`.

## Connect Vercel

After the cloud host exposes the backend over HTTPS, set this Vercel environment variable:

```text
LLAMA_BACKEND_URL=https://your-gpu-backend.example.com
```

Then redeploy Vercel. The existing frontend still calls `/api/chat`; Vercel proxies that request to the LLaMA backend.

## Smoke Tests

```bash
curl https://your-gpu-backend.example.com/health

curl -X POST https://your-gpu-backend.example.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is a Spring in Wyckoff methodology?"}'

curl -X POST https://your-gpu-backend.example.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"AAPL price now?"}'
```
