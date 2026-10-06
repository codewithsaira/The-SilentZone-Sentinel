"""LLM access for the Coordinator: Gemini free tier, local Ollama, or a deterministic template fallback."""
from typing import Optional

import httpx

from ..config import settings


def describe() -> str:
    p = settings.llm_provider
    if settings.offline_mode or p == "template":
        return "template"
    if p == "auto":
        return "gemini" if settings.gemini_api_key else "ollama-if-reachable"
    return p


async def _gemini(client: httpx.AsyncClient, prompt: str) -> Optional[str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    r = await client.post(url, params={"key": settings.gemini_api_key},
                          json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _ollama(client: httpx.AsyncClient, prompt: str) -> Optional[str]:
    r = await client.post(f"{settings.ollama_host}/api/generate",
                          json={"model": settings.ollama_model, "prompt": prompt, "stream": False}, timeout=90)
    r.raise_for_status()
    return r.json().get("response")


async def generate(client: httpx.AsyncClient, prompt: str) -> tuple[Optional[str], str]:
    """Returns (text, provider_used). text is None when the caller should use its template."""
    if settings.offline_mode or settings.llm_provider == "template":
        return None, "template"
    order = {"gemini": ["gemini"], "ollama": ["ollama"],
             "auto": (["gemini"] if settings.gemini_api_key else []) + ["ollama"]}.get(settings.llm_provider, [])
    for name in order:
        if name == "gemini" and not settings.gemini_api_key:
            continue
        try:
            text = await (_gemini if name == "gemini" else _ollama)(client, prompt)
            if text and text.strip():
                return text.strip(), name
        except Exception:
            continue
    return None, "template"
