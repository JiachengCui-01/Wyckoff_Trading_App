import fs from "node:fs/promises";
import path from "node:path";
import { runStockAnalysis, toSkillPayload } from "./skills/stockAnalysis.js";

let qaCache;
const CHAT_VERSION = "chatbot-stock-skill-v2";
const FALLBACK_ANSWER =
  "I could not find a high-confidence match in the Wyckoff knowledge base. Try asking about Springs, Selling Climax, accumulation, distribution, volume confirmation, or Phase A-E. For best results, please ask in English.";
const LLAMA_BACKEND_URL = process.env.LLAMA_BACKEND_URL || "";

const TICKER_STOP_WORDS = new Set([
  "A", "AN", "AND", "ARE", "AS", "AT", "BUY", "CAN", "DO", "FOR", "HOW", "I", "IF",
  "IN", "IS", "IT", "ME", "MY", "NOW", "OF", "ON", "OR", "PRICE", "RISK", "SELL",
  "SHOULD", "STATE", "THE", "TO", "TRADE", "WHAT", "WHEN", "WHERE", "WHY", "WITH", "YOU"
]);

const KNOWN_TICKERS = new Set([
  "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "BAC", "GS", "V", "MA",
  "SPY", "QQQ", "IWM", "DIA", "XLF", "COIN", "MSTR", "TSLA", "AMD", "NFLX", "DIS"
]);

const STOCK_INTENT_RE =
  /\b(price|stock|ticker|quote|current|now|phase|state|status|trend|risk|buy|sell|entry|stop|analysis|analyze|market)\b/i;

const STOP_WORDS = new Set([
  "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "did", "do", "does",
  "for", "from", "give", "good", "had", "has", "have", "hello", "hey", "hi", "how",
  "i", "in", "into", "is", "it", "me", "my", "of", "ok", "okay", "on", "or", "please",
  "point", "should", "show", "tell", "test", "thanks", "thank", "the", "there", "to", "was",
  "what", "when", "where", "which", "who", "why", "with", "would", "you"
]);

const DOMAIN_TERMS = new Set([
  "accumulation", "distribution", "spring", "shakeout", "phase", "volume", "price",
  "support", "resistance", "trading", "trade", "entry", "exit", "risk", "markup",
  "markdown", "range", "climax", "selling", "buying", "sos", "sow", "lps", "lpsy",
  "upthrust", "reaccumulation", "redistribution", "absorption", "operator", "composite",
  "demand", "supply", "effort", "result", "cause", "effect", "chart", "breakout",
  "breakdown", "test", "institutional", "smart", "money", "law", "method", "methodology",
  "pattern", "structure", "trend", "rally", "reaction", "creek", "ice", "wyckoff",
  "technical", "analysis", "market", "stock", "trader", "traders"
]);

const METHOD_TERMS = new Set([
  "accumulation", "distribution", "spring", "shakeout", "phase", "volume", "price",
  "support", "resistance", "entry", "exit", "risk", "markup", "markdown", "range",
  "climax", "selling", "buying", "sos", "sow", "lps", "lpsy", "upthrust", "absorption",
  "demand", "supply", "effort", "result", "cause", "effect", "chart", "breakout",
  "breakdown", "test", "law", "method", "methodology", "pattern", "structure", "trend",
  "rally", "reaction", "creek", "ice"
]);

const STRONG_DOMAIN_TERMS = new Set([
  "accumulation", "distribution", "spring", "shakeout", "phase", "volume", "price", "support",
  "resistance", "entry", "exit", "risk", "markup", "markdown", "range", "climax", "selling",
  "buying", "sos", "sow", "lps", "lpsy", "upthrust", "absorption", "demand", "supply",
  "effort", "result", "cause", "effect", "chart", "breakout", "breakdown", "test", "law",
  "creek", "ice", "composite", "operator"
]);

const GENERIC_METHOD_TERMS = new Set([
  "identify", "method", "methodology", "pattern", "structure", "trend", "trading", "trade",
  "market", "stock", "trader", "technical", "analysis"
]);

const BIO_TERMS = new Set([
  "born", "birth", "die", "died", "death", "age", "career", "job", "wall", "street",
  "magazine", "publication", "school", "institute", "name", "life", "personal", "history",
  "biography", "student", "legacy"
]);

const PHRASE_ALIASES = [
  ["selling climax", ["selling", "climax"]],
  ["buying climax", ["buying", "climax"]],
  ["point and figure", ["point", "figure"]],
  ["composite man", ["composite"]],
  ["smart money", ["smart", "money"]],
  ["sign of strength", ["sos"]],
  ["sign of weakness", ["sow"]],
  ["last point of support", ["lps"]],
  ["last point of supply", ["lpsy"]],
  ["phase a", ["phase", "phase-a"]],
  ["phase b", ["phase", "phase-b"]],
  ["phase c", ["phase", "phase-c"]],
  ["phase d", ["phase", "phase-d"]],
  ["phase e", ["phase", "phase-e"]]
];

const TOKEN_ALIASES = new Map([
  ["definition", "define"],
  ["defined", "define"],
  ["defines", "define"],
  ["explain", "define"],
  ["explains", "define"],
  ["explained", "define"],
  ["meaning", "define"],
  ["mean", "define"],
  ["means", "define"],
  ["detect", "identify"],
  ["find", "identify"],
  ["distinguish", "identify"],
  ["differentiate", "identify"],
  ["recognize", "identify"],
  ["spot", "identify"],
  ["confirm", "identify"],
  ["know", "identify"],
  ["see", "identify"],
  ["signal", "sign"],
  ["signals", "sign"],
  ["phases", "phase"],
  ["patterns", "pattern"],
  ["entries", "entry"],
  ["laws", "law"],
  ["begins", "start"],
  ["begin", "start"],
  ["beginning", "start"],
  ["starts", "start"],
  ["started", "start"],
  ["identify", "identify"]
]);

const DEFINITION_TERMS = new Set(["define"]);

const SMALL_TALK_RE =
  /^(hi|hello|hey|yo|thanks|thank you|ok|okay|test|testing|who are you|good morning|good afternoon|good evening)[.!?\s]*$/i;

function normalizeQuestion(value) {
  return String(value)
    .normalize("NFKC")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeText(value) {
  return normalizeQuestion(value)
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];

    if (quoted && ch === '"' && next === '"') {
      cell += '"';
      i += 1;
    } else if (ch === '"') {
      quoted = !quoted;
    } else if (ch === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some(Boolean)) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += ch;
    }
  }

  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }

  return rows.slice(1).map(([question, answer, label]) => ({ question, answer, label }));
}

function stemToken(token) {
  if (TOKEN_ALIASES.has(token)) return TOKEN_ALIASES.get(token);
  if (
    DOMAIN_TERMS.has(token) ||
    METHOD_TERMS.has(token) ||
    STRONG_DOMAIN_TERMS.has(token) ||
    BIO_TERMS.has(token)
  ) {
    return token;
  }
  if (token.length > 5 && token.endsWith("ies")) return `${token.slice(0, -3)}y`;
  if (token.length > 5 && token.endsWith("ing")) return token.slice(0, -3);
  if (token.length > 4 && token.endsWith("ed")) return token.slice(0, -2);
  if (token.length > 4 && token.endsWith("es")) return token.slice(0, -2);
  if (token.length > 3 && token.endsWith("s")) return token.slice(0, -1);
  return token;
}

function tokenize(value) {
  const text = normalizeText(value);
  const phraseTokens = [];
  for (const [phrase, tokens] of PHRASE_ALIASES) {
    if (text.includes(phrase)) phraseTokens.push(...tokens);
  }

  const words = text
    .split(/\s+/)
    .map(stemToken)
    .filter((token) => token.length > 1 && !STOP_WORDS.has(token));

  return [...new Set([...words, ...phraseTokens].map(stemToken))];
}

function toTokenSet(value) {
  return new Set(tokenize(value));
}

function countOverlap(a, b) {
  return a.reduce((total, token) => total + (b.has(token) ? 1 : 0), 0);
}

function phraseCoverage(queryText, itemText) {
  const queryWords = queryText.split(/\s+/).filter(Boolean);
  if (queryWords.length < 2) return 0;

  let hits = 0;
  let total = 0;
  for (let i = 0; i < queryWords.length - 1; i += 1) {
    const phrase = `${queryWords[i]} ${queryWords[i + 1]}`;
    if (STOP_WORDS.has(queryWords[i]) || STOP_WORDS.has(queryWords[i + 1])) continue;
    total += 1;
    if (itemText.includes(phrase)) hits += 1;
  }

  return total ? hits / total : 0;
}

function inferQueryType(tokens, rawQuestion) {
  const hasMethod = tokens.some((token) => METHOD_TERMS.has(token));
  const hasBio = tokens.some((token) => BIO_TERMS.has(token));
  const hasStrongDomain =
    tokens.some((token) => STRONG_DOMAIN_TERMS.has(token)) ||
    /\bpoint\s+(and\s+)?figure\b/i.test(rawQuestion);
  const hasWyckoff = /\bwyckoff\b/i.test(rawQuestion);

  if (SMALL_TALK_RE.test(rawQuestion)) return "out-of-scope";
  if (!tokens.length) return "out-of-scope";
  if (!hasWyckoff && !hasStrongDomain) return "out-of-scope";
  if (hasMethod) return "method";
  if (hasBio || hasWyckoff) return "biography";
  return "method";
}

function prepareItem(item) {
  const questionText = normalizeText(item.question);
  const answerText = normalizeText(item.answer);
  const labelText = normalizeText(item.label || "General");
  const questionTokens = toTokenSet(item.question);
  const answerTokens = toTokenSet(item.answer);
  const labelTokens = toTokenSet(item.label || "");

  return {
    ...item,
    questionText,
    answerText,
    labelText,
    questionTokens,
    answerTokens,
    labelTokens
  };
}

async function loadQa() {
  if (qaCache) return qaCache;
  const file = path.join(process.cwd(), "data", "wyckoff_all_labels_combined.csv");
  const text = await fs.readFile(file, "utf8");
  qaCache = parseCsv(text)
    .filter((item) => item.question && item.answer)
    .map(prepareItem);
  return qaCache;
}

function scoreItem(query, item) {
  const qLen = Math.max(1, query.tokens.length);
  const questionOverlap = countOverlap(query.tokens, item.questionTokens);
  const answerOverlap = countOverlap(query.tokens, item.answerTokens);
  const labelOverlap = countOverlap(query.tokens, item.labelTokens);
  const questionCoverage = questionOverlap / qLen;
  const answerCoverage = answerOverlap / qLen;
  const labelCoverage = labelOverlap / qLen;
  const phraseScore = phraseCoverage(query.text, item.questionText);
  const rawContentWords = query.text
    .split(/\s+/)
    .filter((token) => token.length > 1 && !STOP_WORDS.has(token) && !DEFINITION_TERMS.has(stemToken(token)));
  const contentWords = rawContentWords
    .map(stemToken)
    .filter((token) => token.length > 1 && !DEFINITION_TERMS.has(token));
  const rawContentPhrase = rawContentWords.join(" ");
  const contentPhrase = contentWords.join(" ");
  const exactContentPhrase =
    rawContentPhrase && (item.questionText.includes(rawContentPhrase) || item.answerText.includes(rawContentPhrase));

  const stemmedItemText = `${item.questionText} ${item.answerText}`
    .split(/\s+/)
    .map(stemToken)
    .join(" ");

  let score =
    questionCoverage * 0.58 +
    answerCoverage * 0.16 +
    labelCoverage * 0.08 +
    phraseScore * 0.12;

  if (query.text.length > 12 && item.questionText.includes(query.text)) score += 0.28;
  if (contentPhrase && contentWords.length >= 2) {
    if (rawContentPhrase && item.questionText.includes(rawContentPhrase)) {
      score += 0.82;
    } else if (exactContentPhrase || stemmedItemText.includes(contentPhrase)) {
      score += 0.56;
    } else if (contentWords.some((token) => METHOD_TERMS.has(token) || DOMAIN_TERMS.has(token))) {
      score *= 0.68;
    }
  }
  const requestedTopics = query.tokens.filter(
    (token) => METHOD_TERMS.has(token) && !GENERIC_METHOD_TERMS.has(token)
  );

  if (requestedTopics.some((token) => item.questionTokens.has(token))) score += 0.12;
  if (requestedTopics.some((token) => item.answerTokens.has(token))) score += 0.04;

  if (query.tokens.includes("define") && /^(what exactly is|what is|what are)\b|define|meaning|mean/.test(item.questionText)) {
    score += 0.22;
  }
  if (
    query.tokens.includes("define") &&
    requestedTopics.some((token) => item.questionTokens.has(token))
  ) {
    score += 0.2;
  }
  if (
    query.tokens.includes("define") &&
    item.questionTokens.has("define") &&
    requestedTopics.some((token) => item.questionTokens.has(token))
  ) {
    score += 1.4;
  }
  if (
    query.tokens.includes("define") &&
    requestedTopics.some((token) => new RegExp(`^what (exactly )?is (a |an |the )?${token}\\b`).test(item.questionText))
  ) {
    score += 0.34;
  }
  if (
    query.tokens.includes("define") &&
    requestedTopics.some((token) => new RegExp(`^what (exactly )?is (a |an |the )?${token}\\b`).test(item.questionText)) &&
    /^(what exactly is|what is|what are)\b/.test(item.questionText)
  ) {
    score += 0.5;
  }
  if (
    query.tokens.includes("define") &&
    requestedTopics.length === 1 &&
    contentWords.length <= 1 &&
    new RegExp(`^what (exactly )?is (a |an |the )?${requestedTopics[0]}\\??$`).test(item.questionText)
  ) {
    score += 0.72;
  }
  for (const phaseToken of ["phase-a", "phase-b", "phase-c", "phase-d", "phase-e"]) {
    if (!query.tokens.includes(phaseToken)) continue;
    const phaseText = phaseToken.replace("-", " ");
    if (item.questionText.includes(phaseText) && /^(what happens|what is|why is)\b/.test(item.questionText)) {
      score += 0.46;
    }
    for (const otherPhase of ["phase a", "phase b", "phase c", "phase d", "phase e"]) {
      if (otherPhase !== phaseText && item.questionText.includes(otherPhase)) score *= 0.72;
    }
  }
  if (
    query.tokens.includes("define") &&
    ["sos", "sow", "lps", "lpsy"].some((token) => query.tokens.includes(token) && item.questionText.includes(`(${token})`))
  ) {
    score += 1.5;
  }
  if (
    query.tokens.includes("define") &&
    /^(what does it mean if|what happens if|why|how|should|can)\b/.test(item.questionText)
  ) {
    score *= 0.08;
  }
  if (
    query.tokens.includes("define") &&
    !item.questionTokens.has("define") &&
    /^(what timing|what volume|how|why|when|should|can)\b/.test(item.questionText)
  ) {
    score *= 0.2;
  }
  if (
    query.tokens.includes("define") &&
    query.tokens.length <= 2 &&
    /\b(volume|valid|entry|timing|within|multiple|differentiate|distinguish|characteristics?)\b/.test(item.questionText)
  ) {
    score *= 0.72;
  }
  if (
    query.tokens.includes("define") &&
    contentWords.length <= 1 &&
    /\b(volume|valid|entry|timing|within|multiple|differentiate|distinguish|characteristics?)\b/.test(item.questionText)
  ) {
    score *= 0.18;
  }
  if (query.tokens.includes("identify") && item.questionTokens.has("identify")) score += 0.24;
  if (
    query.tokens.includes("identify") &&
    requestedTopics.some((token) => item.questionTokens.has(token)) &&
    /\b(distinguish|differentiate|identify|recognize|valid|genuine|signal|characteristics?)\b/.test(item.questionText)
  ) {
    score += 0.22;
  }
  if (
    query.tokens.includes("identify") &&
    query.tokens.includes("spring") &&
    /\bgenuine spring\b|\bvalid spring\b/.test(item.questionText)
  ) {
    score += 0.34;
  }
  if (
    query.tokens.includes("identify") &&
    item.questionTokens.has("identify") &&
    requestedTopics.some((token) => item.questionTokens.has(token))
  ) {
    score += 0.26;
  }
  if (query.tokens.includes("start") && /start|begin/.test(item.questionText)) score += 0.08;
  if (query.tokens.includes("accumulation") && item.questionTokens.has("accumulation")) score += 0.1;
  if (query.tokens.includes("distribution") && item.questionTokens.has("distribution")) score += 0.1;
  if (query.tokens.includes("volume") && item.questionTokens.has("volume")) score += 0.08;
  if (query.tokens.includes("law") && item.questionTokens.has("law")) score += 0.12;
  if (query.tokens.includes("phase") && /phase|structure/.test(item.questionText)) score += 0.08;
  if (query.tokens.includes("accumulation") && !item.questionTokens.has("accumulation")) score *= 0.58;
  if (query.tokens.includes("distribution") && !item.questionTokens.has("distribution")) score *= 0.58;
  if (/^what are\b/.test(query.text) && query.tokens.includes("law") && item.questionText.includes("fundamental law")) {
    score += 0.18;
  }

  if (query.type === "method" && item.labelText.includes("personal life")) score *= 0.2;
  if (query.type === "biography" && !item.labelText.includes("personal life")) score *= 0.65;
  if (questionOverlap === 0 && answerOverlap > 0) score *= 0.45;
  if (questionOverlap === 0 && labelOverlap === 0) score *= 0.35;
  if (!query.tokens.includes("multiple") && /multiple|secondary/.test(item.questionText)) score *= 0.72;
  if (query.tokens.includes("identify") && !/identify|start|begin|sign|characteristic|define|what/.test(item.questionText)) {
    score *= 0.72;
  }

  return Math.max(0, score);
}

function formatResult(question, query, matches) {
  const best = matches[0];
  const requestedTopics = query.tokens.filter(
    (token) => METHOD_TERMS.has(token) && !GENERIC_METHOD_TERMS.has(token) && !DEFINITION_TERMS.has(token)
  );
  const canUseBestEffort =
    best &&
    best.score >= 0.2 &&
    requestedTopics.length > 0 &&
    requestedTopics.some((token) => best.questionTokens.has(token) || best.answerTokens.has(token));

  if (!best || (best.score < 0.34 && !canUseBestEffort)) {
    return { answer: FALLBACK_ANSWER, confidence: 0.25, context: [] };
  }

  let answer = best.answer;
  const secondSharesTopic =
    !requestedTopics.length ||
    requestedTopics.every((token) => matches[1]?.questionTokens.has(token) || matches[1]?.answerTokens.has(token));
  if (
    !query.tokens.includes("define") &&
    matches[1] &&
    matches[1].score >= 0.34 &&
    matches[1].score > best.score * 0.9 &&
    secondSharesTopic
  ) {
    answer = mergeAnswerText(answer, matches[1].answer);
  }

  if (/\b(entry|buy|trade|signal|risk|stop)\b/i.test(question)) {
    answer +=
      "\n\nTrading note: treat this as methodology guidance, then confirm with price structure, volume behavior, risk limits, and broader market context.";
  }

  if (best.score < 0.34) {
    answer = `Closest match from the Wyckoff knowledge base:\n\n${answer}`;
  }

  return {
    answer,
    confidence: Number(Math.min(0.96, 0.48 + best.score * 0.52).toFixed(2)),
    context: matches.filter((item) => item.score >= 0.28).slice(0, 4)
  };
}

function mergeAnswerText(primary, secondary) {
  const first = String(primary || "").trim();
  const second = String(secondary || "").trim();
  if (!second) return first;
  if (first.toLowerCase().includes(second.toLowerCase())) return first;
  return `${first}\n\n${second}`;
}

function findPinnedDefinitionMatch(query, qa) {
  if (!query.tokens.includes("define")) return null;
  const text = query.text;
  const startsWith = (prefix) => qa.find((item) => item.questionText.startsWith(prefix));
  const includesQuestion = (value) => qa.find((item) => item.questionText.includes(value));

  if (/\bsos\b/.test(text)) return includesQuestion("sign of strength (sos)");
  if (/\bsow\b/.test(text)) return includesQuestion("sign of weakness (sow)");
  if (/\blps\b/.test(text)) return includesQuestion("last point of support (lps)");
  if (/\blpsy\b/.test(text)) return includesQuestion("last point of supply (lpsy)");

  for (const phase of ["a", "b", "c", "d", "e"]) {
    if (new RegExp(`\\bphase\\s+${phase}\\b`).test(text)) {
      return startsWith(`what happens in phase ${phase}`) || includesQuestion(`phase ${phase}`);
    }
  }

  if (text.includes("failed spring")) return includesQuestion("failed spring");
  if (text.includes("spring bar")) return startsWith("what is a spring bar");
  if (text.includes("selling climax")) return startsWith("what is the selling climax") || includesQuestion("selling climax");
  if (text.includes("buying climax")) return startsWith("what is a buying climax") || includesQuestion("buying climax");
  if (text.includes("upthrust")) return startsWith("what is an upthrust") || startsWith("what is upthrust");
  if (text.includes("accumulation")) return qa.find((item) => item.questionTokens.has("define") && item.questionTokens.has("accumulation"));
  if (text.includes("distribution")) return startsWith("what is distribution");
  if (/\bspring\b/.test(text)) return startsWith("what is a spring");

  return null;
}

function extractTicker(question) {
  const raw = String(question || "");
  const directMatches = raw.match(/\b[A-Z]{1,5}(?:[.-][A-Z])?\b/g) || [];
  const direct = directMatches.find((value) => !TICKER_STOP_WORDS.has(value.toUpperCase()));
  if (direct) return direct.toUpperCase();

  const possibleMatches = raw.match(/\b[a-zA-Z]{1,5}(?:[.-][a-zA-Z])?\b/g) || [];
  const known = possibleMatches
    .map((value) => value.toUpperCase())
    .find((value) => KNOWN_TICKERS.has(value));
  return known || "";
}

function extractRange(question) {
  const text = String(question || "").toUpperCase();
  if (/\b(1M|1MO|ONE MONTH)\b/.test(text)) return "1M";
  if (/\b(3M|3MO|THREE MONTHS?)\b/.test(text)) return "3M";
  if (/\b(6M|6MO|SIX MONTHS?)\b/.test(text)) return "6M";
  if (/\b(2Y|2YR|TWO YEARS?)\b/.test(text)) return "2Y";
  return "1Y";
}

function inferStockIntent(question) {
  const text = String(question || "").toLowerCase();
  if (/\b(risk|buy|sell|entry|stop|trade)\b/.test(text)) return "risk";
  if (/\b(phase|accumulation|distribution)\b/.test(text)) return "phase";
  if (/\b(state|status|trend|condition)\b/.test(text)) return "state";
  if (/\b(price|quote|current|now)\b/.test(text)) return "price";
  return "summary";
}

function buildStockRequest(question) {
  const ticker = extractTicker(question);
  if (!ticker) return null;
  const hasEnglishIntent = STOCK_INTENT_RE.test(question);
  if (!hasEnglishIntent) return null;
  return {
    ticker,
    range: extractRange(question),
    intent: inferStockIntent(question)
  };
}

function formatStockFallbackAnswer(payload) {
  const recentEvents = payload.events?.length
    ? payload.events.map((event) => `${event.event} ${event.date} @ $${event.price}`).join("; ")
    : "No major recent Wyckoff events detected";
  const tradeNote =
    payload.bias === "bullish"
      ? "watch for confirmation on pullbacks near support and volume behavior"
      : payload.bias === "bearish"
        ? "risk is elevated, so wait for stopping action or a failed breakdown before considering bullish ideas"
        : "wait for a clearer break from the trading range";

  return `${payload.ticker} closed at about $${payload.price} on ${payload.latestDate}. Over the selected range, it is ${payload.periodReturn}% and the Wyckoff read is ${payload.phase} with a ${payload.bias} bias.\n\n${payload.summary}\n\nRecent events: ${recentEvents}.\n\nRisk note: this is educational analysis, not financial advice; for trade decisions, ${tradeNote}.`;
}

async function runStockSkillForChat(question, fallbackRequest) {
  const visibleInput = ({ ticker, range, intent }) => ({ ticker, range, intent });
  const directPayload = async (request) => {
    const result = await runStockAnalysis(request);
    return toSkillPayload(result);
  };

  const payload = await directPayload(fallbackRequest);
  return {
    answer: formatStockFallbackAnswer(payload),
    confidence: 0.86,
    context: [],
    tools: [{ name: "stock_analysis", input: visibleInput(fallbackRequest), output: payload }]
  };
}

async function proxyToLlamaBackend(question) {
  if (!LLAMA_BACKEND_URL) return null;
  const url = new URL("/chat", LLAMA_BACKEND_URL.endsWith("/") ? LLAMA_BACKEND_URL : `${LLAMA_BACKEND_URL}/`);
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal: AbortSignal.timeout(55000)
  });
  if (!response.ok) {
    throw new Error(`LLaMA backend returned ${response.status}`);
  }
  return response.json();
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.setHeader("X-Chat-Version", CHAT_VERSION);

  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
    const question = normalizeQuestion(body.question || "");

    if (!question) return res.status(400).json({ error: "Question is required" });

    try {
      const llamaResult = await proxyToLlamaBackend(question);
      if (llamaResult) {
        return res.status(200).json({
          ...llamaResult,
          version: llamaResult.version || "llama-lora-hybrid-rag-v1"
        });
      }
    } catch (proxyError) {
      res.setHeader("X-Llama-Backend-Fallback", proxyError.message || "unavailable");
    }

    const stockRequest = buildStockRequest(question);
    if (stockRequest) {
      const stockResult = await runStockSkillForChat(question, stockRequest);
      return res.status(200).json({
        ...stockResult,
        version: CHAT_VERSION
      });
    }

    const queryText = normalizeText(question);
    const queryTokens = tokenize(question);
    const asksForDefinition =
      /^what (is|are)\b/.test(queryText) &&
      (queryTokens.some((token) => DOMAIN_TERMS.has(token) || METHOD_TERMS.has(token)) ||
        /\bpoint\s+(and\s+)?figure\b/i.test(question));
    if (asksForDefinition && !queryTokens.includes("define")) queryTokens.push("define");

    const query = {
      text: queryText,
      tokens: queryTokens,
      type: inferQueryType(queryTokens, question)
    };

    if (query.type === "out-of-scope") {
      return res.status(200).json({
        answer: FALLBACK_ANSWER,
        confidence: 0.2,
        context: [],
        version: CHAT_VERSION
      });
    }

    const qa = await loadQa();
    const pinnedMatch = findPinnedDefinitionMatch(query, qa);
    const matches = qa
      .map((item) => ({ ...item, score: item === pinnedMatch ? 10 : scoreItem(query, item) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);

    const result = formatResult(question, query, matches);
    return res.status(200).json({
      ...result,
      version: CHAT_VERSION,
      context: result.context.map((item) => ({
        question: item.question,
        answer: item.answer,
        label: item.label || "General",
        similarity: Number(Math.max(0.01, Math.min(0.98, item.score)).toFixed(2))
      }))
    });
  } catch (error) {
    return res.status(500).json({ error: error.message || "Chat service failed" });
  }
}
