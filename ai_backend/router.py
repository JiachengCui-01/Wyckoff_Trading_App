from __future__ import annotations

import re

from .llm import llm_engine
from .schemas import IntentResult


TICKER_RE = re.compile(r"\b[A-Z]{1,5}(?:[.-][A-Z])?\b")
STOCK_WORD_RE = re.compile(
    r"\b(price|stock|ticker|quote|current|now|phase|state|status|trend|risk|buy|sell|entry|stop|analysis|analyze|market)\b",
    re.I,
)
SMALL_TALK_RE = re.compile(r"^(hi|hello|hey|yo|thanks|thank you|ok|okay|test|testing)[.!?\s]*$", re.I)
KNOWN_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "BAC", "GS", "V", "MA",
    "SPY", "QQQ", "IWM", "DIA", "XLF", "COIN", "MSTR", "TSLA", "AMD", "NFLX", "DIS",
}
STOP_TICKERS = {"A", "I", "ON", "OR", "BUY", "SELL", "RISK", "PRICE", "NOW", "THE", "WHAT"}


def classify_intent(question: str) -> IntentResult:
    prompt = f"""
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
"""
    try:
        data = llm_engine.generate_json(prompt)
        return IntentResult(**data)
    except Exception:
        return heuristic_intent(question)


def heuristic_intent(question: str) -> IntentResult:
    text = " ".join(str(question).split())
    if not text or SMALL_TALK_RE.match(text):
        return IntentResult(intent="fallback", confidence=0.2)

    ticker = extract_ticker(text)
    if ticker and STOCK_WORD_RE.search(text):
        return IntentResult(
            intent="stock_analysis",
            confidence=0.78,
            ticker=ticker,
            range=extract_range(text),
            stock_intent=extract_stock_intent(text),
        )

    if re.search(r"wyckoff|accumulation|distribution|spring|phase|volume|support|resistance|sos|sow|lps|lpsy|upthrust", text, re.I):
        return IntentResult(intent="rag", confidence=0.7)

    return IntentResult(intent="fallback", confidence=0.25)


def extract_ticker(question: str) -> str | None:
    for match in TICKER_RE.findall(question):
        value = match.upper()
        if value not in STOP_TICKERS:
            return value
    for word in re.findall(r"\b[a-zA-Z]{1,5}(?:[.-][a-zA-Z])?\b", question):
        value = word.upper()
        if value in KNOWN_TICKERS:
            return value
    return None


def extract_range(question: str) -> str:
    text = question.upper()
    if re.search(r"\b(1M|1MO|ONE MONTH)\b", text):
        return "1M"
    if re.search(r"\b(3M|3MO|THREE MONTHS?)\b", text):
        return "3M"
    if re.search(r"\b(6M|6MO|SIX MONTHS?)\b", text):
        return "6M"
    if re.search(r"\b(2Y|2YR|TWO YEARS?)\b", text):
        return "2Y"
    return "1Y"


def extract_stock_intent(question: str) -> str:
    text = question.lower()
    if re.search(r"\b(risk|buy|sell|entry|stop|trade)\b", text):
        return "risk"
    if re.search(r"\b(phase|accumulation|distribution)\b", text):
        return "phase"
    if re.search(r"\b(state|status|trend|condition)\b", text):
        return "state"
    if re.search(r"\b(price|quote|current|now)\b", text):
        return "price"
    return "summary"

