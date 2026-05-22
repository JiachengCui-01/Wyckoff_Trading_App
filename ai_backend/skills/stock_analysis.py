from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


RANGE_MAP = {
    "1M": "3mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y",
}

DISPLAY_DAYS = {
    "1M": 32,
    "3M": 75,
    "6M": 130,
    "1Y": 260,
    "2Y": 520,
}


def run_stock_analysis(input_data: dict[str, Any]) -> dict[str, Any]:
    ticker = normalize_ticker(input_data.get("ticker", "AAPL"))
    range_label = str(input_data.get("range", "1Y")).upper()
    if range_label not in RANGE_MAP:
        range_label = "1Y"
    intent = str(input_data.get("intent", "summary")).lower()

    df = fetch_stock_data(ticker, RANGE_MAP[range_label])
    events = detect_events(df)
    phase, bias, summary = phase_from(df, events)
    display_df = df.tail(DISPLAY_DAYS.get(range_label, 160)).copy()
    display_events = [event for event in events if event["date"] in set(display_df["date"])]
    latest = display_df.iloc[-1]
    first = display_df.iloc[0]
    period_return = ((latest["close"] / first["close"]) - 1) * 100
    bt = backtest(display_df, display_events)

    return {
        "ticker": ticker,
        "range": range_label,
        "intent": intent,
        "latestDate": latest["date"],
        "price": round(float(latest["close"]), 2),
        "periodReturn": round(float(period_return), 2),
        "phase": phase,
        "bias": bias,
        "summary": summary,
        "events": display_events[-5:],
        "backtest": bt,
    }


def normalize_ticker(value: str) -> str:
    return "".join(ch for ch in str(value).strip().upper() if ch.isalnum() or ch in ".-")[:12]


def fetch_stock_data(ticker: str, period: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval="1d")
    if df.empty:
        raise ValueError(f"No market data found for {ticker}")
    df = df.reset_index()
    df.columns = [str(col).lower() for col in df.columns]
    date_col = "date" if "date" in df.columns else "datetime"
    df["date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
    df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
    df = df[["date", "open", "high", "low", "close", "volume"]].dropna()
    df["returns"] = df["close"].pct_change()
    df["volume_ma"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma"]
    return df.dropna().reset_index(drop=True)


def detect_events(df: pd.DataFrame) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    lookback = max(8, min(20, len(df) // 4))

    for i in range(max(lookback + 2, 10), len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        window = df.iloc[i - lookback : i]
        support = window["low"].min()
        resistance = window["high"].max()
        volume_ratio = float(row["volume"] / max(1, window["volume"].mean()))
        change = float((row["close"] - prev["close"]) / prev["close"])
        candle_range = max(0.01, float(row["high"] - row["low"]))
        closes_off_low = row["close"] > row["low"] + candle_range * 0.32

        event = ""
        event_type = "neutral"
        if volume_ratio > 1.8 and change < -0.025 and closes_off_low:
            event, event_type = "SC", "bullish"
        elif volume_ratio > 1.8 and change > 0.025 and row["close"] > df["close"].iloc[max(0, i - 20) : i + 1].mean() * 1.04:
            event, event_type = "BC", "bearish"
        elif row["low"] < support * 0.992 and row["close"] > support and volume_ratio < 1.7:
            event, event_type = "SP", "bullish"
        elif row["high"] > resistance * 1.008 and row["close"] < resistance and volume_ratio < 1.7:
            event, event_type = "UT", "bearish"
        elif row["close"] > resistance and change > 0.014 and volume_ratio > 1.25:
            event, event_type = "SOS", "bullish"
        elif row["close"] < support and change < -0.014 and volume_ratio > 1.25:
            event, event_type = "SOW", "bearish"

        if event:
            events.append(
                {
                    "date": row["date"],
                    "event": event,
                    "type": event_type,
                    "price": round(float(row["close"]), 2),
                    "volumeRatio": round(volume_ratio, 2),
                }
            )
    return events[-12:]


def phase_from(df: pd.DataFrame, events: list[dict[str, Any]]) -> tuple[str, str, str]:
    recent = df.tail(max(12, min(30, len(df))))
    trend = ((recent.iloc[-1]["close"] / recent.iloc[0]["close"]) - 1) * 100
    recent_events = [event["event"] for event in events[-5:]]
    bullish_count = sum(1 for event in events if event["type"] == "bullish")
    bearish_count = sum(1 for event in events if event["type"] == "bearish")

    if any(event in {"SC", "SP"} for event in recent_events):
        if trend > 2:
            return "Accumulation - Test/Markup", "bullish", "Spring or selling climax behavior is resolving upward. Watch for a Sign of Strength and a low-volume pullback."
        return "Accumulation - Building Cause", "neutral", "Selling pressure is being absorbed. Wait for a stronger markup confirmation."
    if any(event in {"BC", "UT"} for event in recent_events):
        if trend < -2:
            return "Distribution - Test/Markdown", "bearish", "Upthrust or buying climax behavior is failing. Downside risk is elevated."
        return "Distribution - Building Cause", "neutral", "Buying pressure may be tiring. Monitor for failed rallies and supply expansion."
    if "SOS" in recent_events or (trend > 6 and bullish_count >= bearish_count):
        return "Markup", "bullish", "Demand is in control. Prefer pullback entries near support with volume confirmation."
    if "SOW" in recent_events or (trend < -6 and bearish_count > bullish_count):
        return "Markdown", "bearish", "Supply is in control. Avoid long entries until a stopping action appears."
    return "Trading Range", "neutral", "No dominant Wyckoff event cluster. Monitor support, resistance, and volume confirmation."


def backtest(df: pd.DataFrame, events: list[dict[str, Any]]) -> dict[str, Any]:
    event_by_date = {event["date"]: event for event in events}
    cash = 10000.0
    position = 0.0
    entry = 0.0
    wins = 0
    trades = 0

    for _, candle in df.iterrows():
        signal = event_by_date.get(candle["date"])
        close = float(candle["close"])
        if not position and signal and signal["event"] in {"SP", "SOS", "SC"}:
            position = cash / close
            entry = close
            cash = 0.0
        elif position and (close >= entry * 1.08 or close <= entry * 0.95 or (signal and signal["event"] in {"UT", "SOW", "BC"})):
            cash = position * close
            wins += 1 if close > entry else 0
            trades += 1
            position = 0.0

    if position:
        cash = position * float(df.iloc[-1]["close"])
    total_return = ((cash / 10000.0) - 1) * 100
    return {
        "totalReturn": round(total_return, 1),
        "trades": trades,
        "winRate": round((wins / trades) * 100) if trades else 0,
    }

