import fs from "node:fs/promises";
import path from "node:path";

let qaCache;
const CHAT_VERSION = "chatbot-rag-rerank-v4";
const FALLBACK_ANSWER =
  "I could not find a high-confidence match in the Wyckoff knowledge base. Try asking about Springs, Selling Climax, accumulation, distribution, volume confirmation, or Phase A-E.";

const STOP_WORDS = new Set([
  "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "did", "do", "does",
  "for", "from", "give", "good", "had", "has", "have", "hello", "hey", "hi", "how",
  "i", "in", "into", "is", "it", "me", "my", "of", "ok", "okay", "on", "or", "please",
  "should", "show", "tell", "test", "thanks", "thank", "the", "there", "to", "was",
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
  ["last point of supply", ["lpsy"]]
];

const TOKEN_ALIASES = new Map([
  ["detect", "identify"],
  ["find", "identify"],
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
  const hasStrongDomain = tokens.some((token) => STRONG_DOMAIN_TERMS.has(token));
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

  let score =
    questionCoverage * 0.58 +
    answerCoverage * 0.16 +
    labelCoverage * 0.08 +
    phraseScore * 0.12;

  if (query.text.length > 12 && item.questionText.includes(query.text)) score += 0.28;
  const requestedTopics = query.tokens.filter(
    (token) => METHOD_TERMS.has(token) && !GENERIC_METHOD_TERMS.has(token)
  );

  if (query.tokens.includes("identify") && item.questionTokens.has("identify")) score += 0.24;
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

  return Math.max(0, Math.min(1, score));
}

function formatResult(question, matches) {
  const best = matches[0];
  if (!best || best.score < 0.34) {
    return { answer: FALLBACK_ANSWER, confidence: 0.25, context: [] };
  }

  let answer = best.answer;
  if (matches[1] && matches[1].score >= 0.34 && matches[1].score > best.score * 0.9) {
    answer = mergeAnswerText(answer, matches[1].answer);
  }

  if (/\b(entry|buy|trade|signal|risk|stop)\b/i.test(question)) {
    answer +=
      "\n\nTrading note: treat this as methodology guidance, then confirm with price structure, volume behavior, risk limits, and broader market context.";
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

    const query = {
      text: normalizeText(question),
      tokens: tokenize(question),
      type: inferQueryType(tokenize(question), question)
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
    const matches = qa
      .map((item) => ({ ...item, score: scoreItem(query, item) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);

    const result = formatResult(question, matches);
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
