"""Simple in-memory abuse protection for a public demo (per-IP rate limit + daily LLM budget)."""
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import HTTPException, Request

from app.config import settings

_hits: dict[str, deque] = defaultdict(deque)
_daily = {"day": date.today(), "n": 0}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, limit: int, window: int = 60, cost: int = 0):
    """FastAPI dependency: at most `limit` calls per `window` seconds per IP; `cost` counts toward the daily budget."""

    def dependency(request: Request) -> None:
        now = time.time()
        recent = _hits[f"{name}:{_client_ip(request)}"]
        while recent and now - recent[0] > window:
            recent.popleft()
        if len(recent) >= limit:
            raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
        if cost:
            today = date.today()
            if _daily["day"] != today:
                _daily["day"], _daily["n"] = today, 0
            if _daily["n"] + cost > settings.daily_llm_budget:
                raise HTTPException(429, "The demo has reached today's usage limit. Please try again tomorrow.")
            _daily["n"] += cost
        recent.append(now)

    return dependency
