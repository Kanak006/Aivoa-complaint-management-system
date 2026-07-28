import json
import re
import requests

from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _call_groq(model: str, messages: list, temperature: float = 0.2, max_tokens: int = 1024) -> str:
    """Low-level call to Groq's chat completions endpoint. Returns raw text content."""
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy backend/.env.example to backend/.env and add your key."
        )

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_extraction_model(system_prompt: str, user_prompt: str) -> str:
    return _call_groq(
        model=settings.groq_extraction_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=800,
    )


def call_reasoning_model(system_prompt: str, user_prompt: str) -> str:
    return _call_groq(
        model=settings.groq_reasoning_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=800,
    )


def extract_json(raw_text: str) -> dict:
    """
    LLMs often wrap JSON in prose or markdown fences. This pulls out the first
    {...} block and parses it defensively.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    candidate = fenced.group(1) if fenced else raw_text

    brace_match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if brace_match:
        candidate = brace_match.group(0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Last resort: strip trailing commas, a common small-model mistake
        cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
        return json.loads(cleaned)
