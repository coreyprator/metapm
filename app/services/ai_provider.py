"""
Provider-agnostic AI wrapper. Swap provider by changing config.
Currently: Anthropic Claude. Future: OpenAI, Gemini, etc.
"""
import os
import httpx
from app.core.config import settings

AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")


async def call_ai(system_prompt: str, user_message: str) -> str:
    """Call the configured AI provider. Returns response text."""
    if AI_PROVIDER == "anthropic":
        return await _call_anthropic(system_prompt, user_message)
    raise ValueError(f"Unknown AI_PROVIDER: {AI_PROVIDER}")


async def _call_anthropic(system_prompt: str, user_message: str) -> str:
    api_key = settings.ANTHROPIC_API_KEY
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
