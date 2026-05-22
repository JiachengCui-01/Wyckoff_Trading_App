from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .llm import llm_engine
from .rag import rag_store
from .router import classify_intent
from .schemas import ChatRequest, ChatResponse, RagContext, ToolCall
from .skills.stock_analysis import run_stock_analysis


VERSION = "llama-lora-hybrid-rag-v1"
FALLBACK = "I could not find a high-confidence Wyckoff match. Please ask about Wyckoff methodology, market phases, or a concrete stock ticker in English."

app = FastAPI(title="Wyckoff LLaMA Chat Backend", version=VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    question = " ".join(request.question.split())
    intent = classify_intent(question)

    if intent.intent == "stock_analysis" and intent.ticker:
        tool_input = {
            "ticker": intent.ticker,
            "range": intent.range,
            "intent": intent.stock_intent,
        }
        output = run_stock_analysis(tool_input)
        answer = generate_stock_answer(question, output)
        return ChatResponse(
            answer=answer,
            intent="stock_analysis",
            confidence=intent.confidence,
            tools=[ToolCall(name="stock_analysis", input=tool_input, output=output)],
            version=VERSION,
        )

    if intent.intent == "rag":
        contexts = rag_store.search(question, top_k=request.top_k)
        answer = generate_rag_answer(question, contexts)
        return ChatResponse(
            answer=answer,
            intent="rag",
            confidence=intent.confidence,
            context=contexts,
            version=VERSION,
        )

    return ChatResponse(answer=FALLBACK, intent="fallback", confidence=intent.confidence, version=VERSION)


def generate_rag_answer(question: str, contexts: list[RagContext]) -> str:
    context_text = "\n\n".join(
        f"[{idx + 1}] Label: {item.label}\nQ: {item.question}\nA: {item.answer}"
        for idx, item in enumerate(contexts)
    )
    prompt = f"""
You are a Wyckoff methodology assistant fine-tuned with LoRA.
Answer in English using only the retrieved context. If the context is insufficient, say so briefly.
Do not provide financial advice.

Retrieved context:
{context_text}

User question: {question}

Answer:
"""
    return llm_engine.generate(prompt).strip()


def generate_stock_answer(question: str, output: dict) -> str:
    prompt = f"""
You are a Wyckoff stock-analysis assistant fine-tuned with LoRA.
Use the stock_analysis JSON to answer in English.
Mention the data date, current price, Wyckoff phase, bias, and recent events when relevant.
Do not give deterministic buy or sell instructions. State that this is educational analysis, not financial advice.

User question: {question}
stock_analysis JSON:
{json.dumps(output, ensure_ascii=False)}

Answer:
"""
    return llm_engine.generate(prompt).strip()

