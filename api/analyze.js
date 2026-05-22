import { runStockAnalysis } from "./skills/stockAnalysis.js";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");

  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

  try {
    const result = await runStockAnalysis({
      ticker: req.query.ticker || "AAPL",
      range: req.query.range || "1Y",
      intent: "summary"
    });

    return res.status(200).json(result);
  } catch (error) {
    return res.status(500).json({ error: error.message || "Analysis failed" });
  }
}
