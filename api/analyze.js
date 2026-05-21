const STOCK_GROUPS = {
  "Tech Giants": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"],
  Finance: ["JPM", "BAC", "GS", "V", "MA"],
  ETFs: ["SPY", "QQQ", "IWM", "DIA", "XLF"],
  "Crypto-Related": ["COIN", "MSTR"],
  Other: ["TSLA", "AMD", "NFLX", "DIS"]
};

const RANGE_MAP = {
  "1M": "3mo",
  "3M": "3mo",
  "6M": "6mo",
  "1Y": "1y",
  "2Y": "2y"
};

const DISPLAY_DAYS = {
  "1M": 32,
  "3M": 75,
  "6M": 130,
  "1Y": 260,
  "2Y": 520
};

function sma(values, index, length) {
  const start = Math.max(0, index - length + 1);
  const slice = values.slice(start, index + 1).filter(Number.isFinite);
  return slice.reduce((sum, value) => sum + value, 0) / Math.max(1, slice.length);
}

function detectEvents(candles) {
  const events = [];
  const closes = candles.map((c) => c.close);
  const volumes = candles.map((c) => c.volume);
  const lookback = Math.max(8, Math.min(20, Math.floor(candles.length / 4)));
  const start = Math.max(lookback + 2, 10);

  for (let i = start; i < candles.length; i += 1) {
    const row = candles[i];
    const prev = candles[i - 1];
    const support = Math.min(...candles.slice(i - lookback, i).map((c) => c.low));
    const resistance = Math.max(...candles.slice(i - lookback, i).map((c) => c.high));
    const volumeRatio = row.volume / Math.max(1, sma(volumes, i - 1, lookback));
    const change = (row.close - prev.close) / prev.close;
    const range = Math.max(0.01, row.high - row.low);
    const closesOffLow = row.close > row.low + range * 0.32;
    const closesOffHigh = row.close < row.high - range * 0.32;

    let event = "";
    let type = "neutral";

    if (volumeRatio > 1.8 && change < -0.025 && closesOffLow) {
      event = "SC";
      type = "bullish";
    } else if (volumeRatio > 1.8 && change > 0.025 && row.close > sma(closes, i, 20) * 1.04) {
      event = "BC";
      type = "bearish";
    } else if (row.low < support * 0.992 && row.close > support && volumeRatio < 1.7) {
      event = "SP";
      type = "bullish";
    } else if (row.high > resistance * 1.008 && row.close < resistance && volumeRatio < 1.7) {
      event = "UT";
      type = "bearish";
    } else if (row.close > resistance && change > 0.014 && volumeRatio > 1.25) {
      event = "SOS";
      type = "bullish";
    } else if (row.close < support && change < -0.014 && volumeRatio > 1.25) {
      event = "SOW";
      type = "bearish";
    }

    if (event) {
      events.push({
        date: row.date,
        event,
        type,
        price: Number(row.close.toFixed(2)),
        volumeRatio: Number(volumeRatio.toFixed(2))
      });
    }
  }

  return events.slice(-12);
}

function phaseFrom(candles, events) {
  const recent = candles.slice(-Math.max(12, Math.min(30, candles.length)));
  const first = recent[0].close;
  const last = recent.at(-1).close;
  const trend = ((last / first) - 1) * 100;
  const recentEvents = events.slice(-5).map((item) => item.event);
  const bullishCount = events.filter((item) => item.type === "bullish").length;
  const bearishCount = events.filter((item) => item.type === "bearish").length;

  if (recentEvents.some((event) => ["SC", "SP"].includes(event))) {
    return trend > 2
      ? ["Accumulation - Test/Markup", "bullish", "Spring or selling climax behavior is resolving upward. Watch for a Sign of Strength and a low-volume pullback."]
      : ["Accumulation - Building Cause", "neutral", "Selling pressure is being absorbed. Wait for a stronger markup confirmation."];
  }

  if (recentEvents.some((event) => ["BC", "UT"].includes(event))) {
    return trend < -2
      ? ["Distribution - Test/Markdown", "bearish", "Upthrust or buying climax behavior is failing. Downside risk is elevated."]
      : ["Distribution - Building Cause", "neutral", "Buying pressure may be tiring. Monitor for failed rallies and supply expansion."];
  }

  if (recentEvents.includes("SOS") || (trend > 6 && bullishCount >= bearishCount)) {
    return ["Markup", "bullish", "Demand is in control. Prefer pullback entries near support with volume confirmation."];
  }

  if (recentEvents.includes("SOW") || (trend < -6 && bearishCount > bullishCount)) {
    return ["Markdown", "bearish", "Supply is in control. Avoid long entries until a stopping action appears."];
  }

  return ["Trading Range", "neutral", "No dominant Wyckoff event cluster. Monitor support, resistance, and volume confirmation."];
}

function backtest(candles, events) {
  const byDate = new Map(events.map((event) => [event.date, event]));
  let cash = 10000;
  let position = 0;
  let entry = 0;
  let wins = 0;
  let trades = 0;

  for (const candle of candles) {
    const signal = byDate.get(candle.date);

    if (!position && signal && ["SP", "SOS", "SC"].includes(signal.event)) {
      position = cash / candle.close;
      entry = candle.close;
      cash = 0;
    } else if (position && (candle.close >= entry * 1.08 || candle.close <= entry * 0.95 || (signal && ["UT", "SOW", "BC"].includes(signal.event)))) {
      cash = position * candle.close;
      wins += candle.close > entry ? 1 : 0;
      trades += 1;
      position = 0;
    }
  }

  if (position) cash = position * candles.at(-1).close;
  const totalReturn = ((cash / 10000) - 1) * 100;

  return {
    totalReturn: Number(totalReturn.toFixed(1)),
    trades,
    winRate: trades ? Number(((wins / trades) * 100).toFixed(0)) : 0
  };
}

function normalizeYahoo(result) {
  const quote = result.chart?.result?.[0];
  if (!quote) throw new Error("No market data returned");

  const timestamps = quote.timestamp || [];
  const q = quote.indicators?.quote?.[0] || {};
  const adj = quote.indicators?.adjclose?.[0]?.adjclose || q.close || [];

  return timestamps
    .map((time, index) => ({
      date: new Date(time * 1000).toISOString().slice(0, 10),
      open: q.open?.[index],
      high: q.high?.[index],
      low: q.low?.[index],
      close: adj[index] ?? q.close?.[index],
      volume: q.volume?.[index]
    }))
    .filter((c) => [c.open, c.high, c.low, c.close, c.volume].every(Number.isFinite));
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");

  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

  try {
    const ticker = String(req.query.ticker || "AAPL").trim().toUpperCase().replace(/[^A-Z0-9.-]/g, "");
    const rangeLabel = String(req.query.range || "1Y").toUpperCase();
    const range = RANGE_MAP[rangeLabel] || "1y";
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?range=${range}&interval=1d&includePrePost=false&events=div%2Csplits`;
    const response = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 WyckoffTrader/2.0"
      }
    });

    if (!response.ok) throw new Error(`Yahoo Finance returned ${response.status}`);

    const candles = normalizeYahoo(await response.json());
    if (candles.length < 14) throw new Error("Not enough candles for analysis");

    const events = detectEvents(candles);
    const [phase, bias, summary] = phaseFrom(candles, events);
    const displayCandles = candles.slice(-(DISPLAY_DAYS[rangeLabel] || 160));
    const displayDates = new Set(displayCandles.map((c) => c.date));
    const displayEvents = events.filter((event) => displayDates.has(event.date));
    const latest = displayCandles.at(-1);
    const first = displayCandles[0];
    const periodReturn = ((latest.close / first.close) - 1) * 100;
    const bt = backtest(displayCandles, displayEvents);

    return res.status(200).json({
      ticker,
      group: Object.entries(STOCK_GROUPS).find(([, list]) => list.includes(ticker))?.[0] || "Custom",
      latestDate: latest.date,
      price: Number(latest.close.toFixed(2)),
      periodReturn: Number(periodReturn.toFixed(2)),
      phase,
      bias,
      summary,
      events: displayEvents,
      backtest: bt,
      candles: displayCandles.slice(-180).map((c) => ({
        ...c,
        open: Number(c.open.toFixed(2)),
        high: Number(c.high.toFixed(2)),
        low: Number(c.low.toFixed(2)),
        close: Number(c.close.toFixed(2))
      }))
    });
  } catch (error) {
    return res.status(500).json({ error: error.message || "Analysis failed" });
  }
}
