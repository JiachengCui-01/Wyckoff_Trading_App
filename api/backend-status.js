const LLAMA_BACKEND_URL = process.env.LLAMA_BACKEND_URL || "";

async function checkLlamaBackend() {
  const chatUrl = LLAMA_BACKEND_URL
    ? new URL("/chat", LLAMA_BACKEND_URL.endsWith("/") ? LLAMA_BACKEND_URL : `${LLAMA_BACKEND_URL}/`).toString()
    : "";

  if (!LLAMA_BACKEND_URL) {
    return {
      mode: "fallback",
      label: "Serverless Fallback Demo",
      detail: "LLaMA backend URL is not configured.",
      chatUrl: ""
    };
  }

  try {
    const url = new URL("/health", LLAMA_BACKEND_URL.endsWith("/") ? LLAMA_BACKEND_URL : `${LLAMA_BACKEND_URL}/`);
    const response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(3500)
    });
    if (!response.ok) throw new Error(`health returned ${response.status}`);
    const data = await response.json().catch(() => ({}));
    return {
      mode: "llama",
      label: "LLaMA+LoRA Backend Online",
      detail: data.version ? `Connected to ${data.version}` : "Connected to GPU AI backend.",
      chatUrl
    };
  } catch (error) {
    return {
      mode: "fallback",
      label: "Serverless Fallback Demo",
      detail: `LLaMA backend unavailable: ${error.message}`,
      chatUrl: ""
    };
  }
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Cache-Control", "no-store, max-age=0");

  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

  const result = await checkLlamaBackend();
  return res.status(200).json({
    ...result,
    configured: Boolean(LLAMA_BACKEND_URL),
    checkedAt: new Date().toISOString()
  });
}
