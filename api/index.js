import fs from "node:fs/promises";
import path from "node:path";

let htmlCache;

async function loadHtml() {
  if (htmlCache) return htmlCache;
  htmlCache = await fs.readFile(path.join(process.cwd(), "index.html"), "utf8");
  return htmlCache;
}

export default async function handler(req, res) {
  const html = await loadHtml();
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store, max-age=0");
  return res.status(200).send(html);
}
