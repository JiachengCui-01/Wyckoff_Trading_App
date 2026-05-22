from typing import Any, Literal

from pydantic import BaseModel, Field


IntentName = Literal["rag", "stock_analysis", "fallback"]
StockIntent = Literal["price", "phase", "state", "risk", "summary"]
RangeLabel = Literal["1M", "3M", "6M", "1Y", "2Y"]


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=12)


class RagContext(BaseModel):
    question: str
    answer: str
    label: str = "General"
    score: float = 0.0
    source: str = "hybrid"


class ToolCall(BaseModel):
    name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: IntentName
    confidence: float = 0.0
    context: list[RagContext] = Field(default_factory=list)
    tools: list[ToolCall] = Field(default_factory=list)
    version: str = "llama-lora-three-route-agent-v2"


class IntentResult(BaseModel):
    intent: IntentName
    confidence: float = 0.0
    ticker: str | None = None
    range: RangeLabel = "1Y"
    stock_intent: StockIntent = "summary"
