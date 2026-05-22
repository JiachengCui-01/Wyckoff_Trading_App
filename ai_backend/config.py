from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAG_INDEX_DIR = DATA_DIR / "rag_index"
QA_DATA_PATH = DATA_DIR / "wyckoff_all_labels_combined.csv"

LLAMA_BASE_MODEL = os.getenv("LLAMA_BASE_MODEL", "meta-llama/Llama-2-7b-hf")
LLAMA_LORA_PATH = os.getenv("LLAMA_LORA_PATH", str(ROOT_DIR / "models" / "llama_wyckoff_lora"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-MiniLM-L6-v2")
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RETRIEVAL_POOL = int(os.getenv("RAG_RETRIEVAL_POOL", "16"))
MAX_CONTEXT_ITEMS = int(os.getenv("RAG_MAX_CONTEXT_ITEMS", "5"))
MAX_NEW_TOKENS = int(os.getenv("LLAMA_MAX_NEW_TOKENS", "180"))
TEMPERATURE = float(os.getenv("LLAMA_TEMPERATURE", "0.2"))
