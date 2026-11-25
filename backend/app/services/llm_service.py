from google import genai

from app.config import settings

_client: genai.Client | None = None


class LLMError(RuntimeError):
    pass


def generate(prompt: str) -> str:
    global _client
    try:
        if _client is None:
            _client = genai.Client(api_key=settings.google_api_key)
        response = _client.models.generate_content(model=settings.gemini_model, contents=prompt)
        return (response.text or "").strip()
    except Exception as exc:  # quota, auth, network, safety blocks
        raise LLMError(str(exc)) from exc
