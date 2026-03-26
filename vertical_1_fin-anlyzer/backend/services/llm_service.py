"""
LLM service: builds context-rich prompts and calls the local
OpenAI-compatible endpoint (Ollama / vLLM running Qwen3-VL-8B).
"""

import json
import re
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434")
LLM_MODEL:    str = os.getenv("LLM_MODEL", "qwen2.5vl:7b")


# ── Chat with financial context ───────────────────────────────────────────────

async def chat_with_context(message: str, context: dict, custom_instruction: str = "") -> str:
    """
    Builds a system prompt containing live financial state,
    then calls the native Ollama /api/chat endpoint and returns
    the assistant reply as plain text.
    """
    custom_block = f"\n=== CUSTOM INSTRUCTIONS ===\n{custom_instruction.strip()}\n" if custom_instruction.strip() else ""

    system_prompt = f"""You are a sharp, concise AI Financial Strategist embedded inside a personal Financial Command Center.
{custom_block}
=== LIVE FINANCIAL SNAPSHOT ===
ASSETS:
{json.dumps(context.get('assets', []), indent=2, default=str)}

PENDING PAYABLES (outstanding debts):
{json.dumps(context.get('payables', []), indent=2, default=str)}

EXPECTED RECEIVABLES (incoming money):
{json.dumps(context.get('receivables', []), indent=2, default=str)}

=== YOUR ROLE ===
- Analyse the numbers above to give precise, actionable advice.
- Prioritise payment of high-penalty dues first.
- Flag liquidity risks (liquid assets < 30-day payables total).
- Keep responses focused and under 300 words unless a deeper analysis is explicitly requested.
- Respond in plain text only (no markdown headers, no bullet symbols unless requested).
"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": message},
        ],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(f"{LLM_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["message"]["content"]


# ── Document analysis (Vision-Language) ──────────────────────────────────────

async def analyze_document_with_llm(images_b64: list[str]) -> dict:
    """
    Sends up to 3 document pages as base64 images to the VLM.
    Instructs the model to return ONLY a strict JSON object.
    The JSON is parsed and returned; the caller (route) does NOT persist it.
    """
    extraction_prompt = """Carefully examine this financial document.
Extract ALL financial obligations and income information you can find.

Output ONLY a single valid JSON object — no explanation, no markdown fences, no extra text.

Required structure (include empty arrays if nothing found):
{
  "payables": [
    {
      "creditor": "string",
      "amount": 0.0,
      "due_date": "YYYY-MM-DDTHH:MM:SS",
      "penalty_fee": 0.0
    }
  ],
  "receivables": [
    {
      "source": "string",
      "amount": 0.0,
      "expected_date": "YYYY-MM-DDTHH:MM:SS",
      "confidence": "High"
    }
  ],
  "assets": [
    {
      "name": "string",
      "type": "Cash",
      "value": 0.0,
      "liquidity_score": 3
    }
  ]
}

Allowed confidence values: High, Med, Low
Allowed asset types: Cash, Bank, Gold, Land
Liquidity score: integer 1-5

Output the JSON object now:"""

    # Build multimodal message content (max 3 pages to control token usage)
    content: list[dict] = []
    for b64 in images_b64[:3]:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    content.append({"type": "text", "text": extraction_prompt})

    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 2048,
        "temperature": 0.05,   # Low temperature for deterministic structured output
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(f"{LLM_BASE_URL}/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()

    raw = data["choices"][0]["message"]["content"].strip()

    # ── Robust JSON extraction ────────────────────────────────────────────────
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fall back: grab first {...} block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Return raw for human inspection if all parsing fails
        return {
            "payables": [], "receivables": [], "assets": [],
            "_parse_error": True,
            "_raw_response": raw[:500],
        }