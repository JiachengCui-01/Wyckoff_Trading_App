from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from .config import LLAMA_BASE_MODEL, LLAMA_LORA_PATH, MAX_NEW_TOKENS, TEMPERATURE


@dataclass
class GenerationConfig:
    max_new_tokens: int = MAX_NEW_TOKENS
    temperature: float = TEMPERATURE


class LlamaLoraEngine:
    """Lazy loader for the LLaMA base model plus LoRA adapter."""

    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self.mock = os.getenv("WYCKOFF_LLM_MOCK", "0") == "1"

    @property
    def initialized(self) -> bool:
        return self.mock or (self.model is not None and self.tokenizer is not None)

    def initialize(self) -> None:
        if self.initialized:
            return

        if not os.path.exists(LLAMA_LORA_PATH):
            raise RuntimeError(
                f"LoRA adapter not found at {LLAMA_LORA_PATH}. "
                "Place the trained adapter there or set LLAMA_LORA_PATH."
            )

        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(
            LLAMA_LORA_PATH,
            trust_remote_code=True,
            use_fast=False,
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token

        if self.device == "cuda":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
            base_model = AutoModelForCausalLM.from_pretrained(
                LLAMA_BASE_MODEL,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True,
            )
        else:
            base_model = AutoModelForCausalLM.from_pretrained(
                LLAMA_BASE_MODEL,
                device_map="auto",
                torch_dtype=torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )

        self.model = PeftModel.from_pretrained(base_model, LLAMA_LORA_PATH)
        self.model.eval()

    def generate(self, prompt: str, config: GenerationConfig | None = None) -> str:
        if self.mock:
            return self._mock_generate(prompt)

        self.initialize()
        assert self.model is not None
        assert self.tokenizer is not None
        generation_config = config or GenerationConfig()
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        ).to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=generation_config.max_new_tokens,
                temperature=generation_config.temperature,
                top_p=0.9,
                do_sample=generation_config.temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return text[len(prompt):].strip() if text.startswith(prompt) else text.strip()

    def generate_json(self, prompt: str) -> dict[str, Any]:
        text = self.generate(prompt, GenerationConfig(max_new_tokens=160, temperature=0.0))
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"Model did not return JSON: {text[:200]}")
        return json.loads(text[start : end + 1])

    def _mock_generate(self, prompt: str) -> str:
        if '"intent"' in prompt and "stock_analysis" in prompt:
            return '{"intent":"rag","confidence":0.55,"ticker":null,"range":"1Y","stock_intent":"summary"}'
        return "This is a local mock response. Set WYCKOFF_LLM_MOCK=0 and provide LLAMA_LORA_PATH to use LLaMA+LoRA."


llm_engine = LlamaLoraEngine()
