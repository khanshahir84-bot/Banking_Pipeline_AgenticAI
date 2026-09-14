"""Client for an externally hosted OpenAI-compatible chat-completions provider."""
import httpx

from .config import settings


class LLMProviderError(RuntimeError):
    """Raised when a third-party provider response cannot safely be used."""


class ThirdPartyLLM:
    """Call only the configured external provider; no local model backend exists."""

    async def complete(self, system: str, prompt: str) -> str:
        if not settings.llm_api_key:
            if settings.llm_required:
                raise LLMProviderError("LLM_API_KEY is required by configuration")
            return "I completed your request using the approved banking tool."
        payload = {"model": settings.llm_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0}
        headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                response = await client.post(f"{settings.llm_base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("third-party LLM response was unavailable or malformed") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("third-party LLM response did not include text")
        return content.strip()
