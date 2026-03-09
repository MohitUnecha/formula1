"""
Gemini AI Client for F1 Analytics

Uses Google's Gemini API as a secondary LLM alongside Groq.
Rate-limited with automatic fallback to Groq-only on errors.

Used in tandem with Groq — if Gemini fails or hits rate limits,
the system auto-switches to Groq alone.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeminiResponse:
    """Structured response from Gemini."""
    probability: Optional[float] = None
    explanation: Optional[str] = None
    raw: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class GeminiClient:
    """Async Gemini client with rate limiting and auto-disable on errors."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self):
        self.api_key: Optional[str] = getattr(settings, "gemini_api_key", None)
        self.model: str = getattr(settings, "gemini_model", "gemini-2.0-flash")
        self.timeout: float = getattr(settings, "gemini_timeout", 15.0)
        self.temperature: float = getattr(settings, "gemini_temperature", 0.3)
        self._last_request: float = 0.0
        self._min_interval: float = 1.5  # Conservative rate limiting
        self._error_count: int = 0
        self._max_errors: int = 5
        self._disabled: bool = False

    @property
    def available(self) -> bool:
        """Check if Gemini is available."""
        return bool(self.api_key) and not self._disabled

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> GeminiResponse:
        """
        Generate a response from Gemini.
        Returns GeminiResponse; on failure, error field is set.
        """
        if not self.api_key:
            return GeminiResponse(error="Gemini API key not configured")

        if self._disabled:
            return GeminiResponse(error="Gemini disabled due to repeated errors (rate limit likely)")

        # Rate limiting
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_request)
        if wait > 0:
            import asyncio
            await asyncio.sleep(wait)

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System instruction: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow those instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 150,
            },
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
            self._last_request = time.monotonic()
            latency = (time.monotonic() - start) * 1000

            if resp.status_code == 429:
                self._error_count += 1
                if self._error_count >= self._max_errors:
                    self._disabled = True
                    logger.warning("Gemini disabled: rate limit exceeded repeatedly")
                return GeminiResponse(error="Gemini rate limited (429)", latency_ms=latency)

            if resp.status_code != 200:
                self._error_count += 1
                if self._error_count >= self._max_errors:
                    self._disabled = True
                return GeminiResponse(error=f"Gemini HTTP {resp.status_code}: {resp.text[:200]}", latency_ms=latency)

            data = resp.json()
            self._error_count = 0  # reset on success

            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if not candidates:
                return GeminiResponse(error="No candidates in Gemini response", latency_ms=latency)

            parts = candidates[0].get("content", {}).get("parts", [])
            text = " ".join(p.get("text", "") for p in parts).strip()

            if not text:
                return GeminiResponse(error="Empty Gemini response", latency_ms=latency)

            # Parse probability and explanation
            prob = None
            explanation = None

            match = re.search(r"(0?\.\d{1,3}|1\.0|1)(?![\d])", text)
            if match:
                try:
                    prob = float(match.group(1))
                    if prob > 1:
                        prob = prob / 100.0
                except ValueError:
                    prob = None

            reason_match = re.search(r"\d[^\d]*(.+)", text, re.DOTALL)
            if reason_match:
                explanation = reason_match.group(1).strip()[:200]

            return GeminiResponse(
                probability=prob,
                explanation=explanation,
                raw=text[:500],
                latency_ms=latency,
            )

        except Exception as exc:
            self._error_count += 1
            if self._error_count >= self._max_errors:
                self._disabled = True
                logger.warning(f"Gemini disabled after {self._max_errors} errors: {exc}")
            return GeminiResponse(error=str(exc))

    async def score_prediction(self, prompt: str) -> GeminiResponse:
        """
        Score an F1 prediction — same interface as GroqClient for interchangeability.
        """
        system_prompt = (
            "You are an F1 race prediction expert. "
            "Given driver information and context, return a win probability between 0 and 1, "
            "followed by a concise reason (1-2 sentences). "
            "Format: <probability> <reason>"
        )
        return await self.generate(prompt, system_prompt=system_prompt)


# Module-level singleton
gemini_client = GeminiClient()
