from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT_DIR / "data" / "wyckoff_all_labels_combined.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "models" / "llama_wyckoff_lora"
DEFAULT_BASE_MODEL = os.getenv("LLAMA_BASE_MODEL", "meta-llama/Llama-2-7b-hf")


def build_rag_prompt(question: str, answer: str, label: str) -> str:
    return f"""
You are a Wyckoff methodology assistant fine-tuned with LoRA.
Answer in English using only the retrieved context. If the context is insufficient, say so briefly.
Do not provide financial advice.

Retrieved context:
[1] Label: {label}
Q: {question}
A: {answer}

User question: {question}

Answer:
""".strip()


def build_intent_prompt(question: str) -> str:
    return f"""
Classify this Wyckoff trading assistant request.

Return only JSON with:
{{
  "intent": "rag" | "stock_analysis" | "fallback",
  "confidence": number,
  "ticker": string or null,
  "range": "1M" | "3M" | "6M" | "1Y" | "2Y",
  "stock_intent": "price" | "phase" | "state" | "risk" | "summary"
}}

Use stock_analysis only when the user asks about a concrete ticker, price, phase, state, risk, entry, or trend.
Use rag for Wyckoff methodology questions.
Use fallback for small talk or unrelated questions.

Question: {question}
""".strip()


def build_training_samples(data_path: Path, max_rows: int | None) -> list[dict[str, str]]:
    frame = pd.read_csv(data_path)
    frame = frame.dropna(subset=["Questions", "Answers"])
    if max_rows and max_rows > 0:
        frame = frame.sample(min(max_rows, len(frame)), random_state=42)

    samples: list[dict[str, str]] = []
    for row in frame.itertuples(index=False):
        question = str(row.Questions).strip()
        answer = str(row.Answers).strip()
        label = str(getattr(row, "Label", "Wyckoff")).strip()
        samples.append({"prompt": build_rag_prompt(question, answer, label), "completion": answer})
        samples.append(
            {
                "prompt": build_intent_prompt(question),
                "completion": json.dumps(
                    {
                        "intent": "rag",
                        "confidence": 0.9,
                        "ticker": None,
                        "range": "1Y",
                        "stock_intent": "summary",
                    },
                    separators=(",", ":"),
                ),
            }
        )

    stock_questions = [
        ("AAPL price now?", "AAPL", "price"),
        ("What phase is NVDA in?", "NVDA", "phase"),
        ("TSLA current Wyckoff state", "TSLA", "state"),
        ("Can I buy MSFT now?", "MSFT", "risk"),
        ("Analyze SPY for the last 6 months", "SPY", "summary"),
        ("What is AMD trend risk?", "AMD", "risk"),
    ]
    for question, ticker, stock_intent in stock_questions:
        samples.append(
            {
                "prompt": build_intent_prompt(question),
                "completion": json.dumps(
                    {
                        "intent": "stock_analysis",
                        "confidence": 0.92,
                        "ticker": ticker,
                        "range": "6M" if "6 months" in question else "1Y",
                        "stock_intent": stock_intent,
                    },
                    separators=(",", ":"),
                ),
            }
        )

    fallback_questions = ["hello", "thanks", "what is the weather?", "write me a poem", "who won the game?"]
    for question in fallback_questions:
        samples.append(
            {
                "prompt": build_intent_prompt(question),
                "completion": json.dumps(
                    {
                        "intent": "fallback",
                        "confidence": 0.25,
                        "ticker": None,
                        "range": "1Y",
                        "stock_intent": "summary",
                    },
                    separators=(",", ":"),
                ),
            }
        )

    random.Random(42).shuffle(samples)
    return samples


class PromptCompletionDataset(Dataset):
    def __init__(self, samples: list[dict[str, str]], tokenizer, max_length: int) -> None:
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        sample = self.samples[index]
        prompt = sample["prompt"].strip()
        completion = sample["completion"].strip() + self.tokenizer.eos_token
        prompt_ids = self.tokenizer(prompt, add_special_tokens=True, truncation=True, max_length=self.max_length).input_ids
        full_ids = self.tokenizer(
            prompt + "\n" + completion,
            add_special_tokens=True,
            truncation=True,
            max_length=self.max_length,
        ).input_ids
        labels = full_ids.copy()
        prompt_len = min(len(prompt_ids), len(labels))
        labels[:prompt_len] = [-100] * prompt_len
        return {
            "input_ids": torch.tensor(full_ids, dtype=torch.long),
            "attention_mask": torch.ones(len(full_ids), dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


@dataclass
class CausalCollator:
    tokenizer: Any

    def __call__(self, features: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
        max_len = max(item["input_ids"].shape[0] for item in features)
        batch = {"input_ids": [], "attention_mask": [], "labels": []}
        for item in features:
            pad_len = max_len - item["input_ids"].shape[0]
            batch["input_ids"].append(
                torch.cat([item["input_ids"], torch.full((pad_len,), self.tokenizer.pad_token_id, dtype=torch.long)])
            )
            batch["attention_mask"].append(torch.cat([item["attention_mask"], torch.zeros(pad_len, dtype=torch.long)]))
            batch["labels"].append(torch.cat([item["labels"], torch.full((pad_len,), -100, dtype=torch.long)]))
        return {key: torch.stack(value) for key, value in batch.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a QLoRA adapter for the Wyckoff LLaMA backend.")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-rows", type=int, default=0, help="Use 0 for all rows.")
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for this QLoRA training script. Use Colab T4 or another NVIDIA GPU.")

    samples = build_training_samples(args.data_path, args.max_rows or None)
    print(f"Training samples: {len(samples)}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=False, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = PromptCompletionDataset(samples, tokenizer, args.max_length)
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
        optim="paged_adamw_8bit",
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=CausalCollator(tokenizer),
    )
    trainer.train()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"LoRA adapter saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
