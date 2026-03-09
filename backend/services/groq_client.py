"""Lightweight Groq client used by prediction endpoints."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import re
import httpx

from config import settings


@dataclass
class GroqResponse:
    probability: Optional[float] = None
    explanation: Optional[str] = None
    raw: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class GroqClient:
    def __init__(self):
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.timeout = settings.groq_timeout
        self.temperature = settings.groq_temperature
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def score_prediction(self, prompt: str) -> GroqResponse:
        if not self.api_key:
            return GroqResponse(error="Groq API key missing")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an F1 race prediction expert. Factor in weather conditions (temperature, rain, wind, humidity) and how they affect tire strategy, car handling, and race pace. Return a probability 0-1 and a concise reason."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 80,
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
        except Exception as exc:  # network/timeout
            return GroqResponse(error=str(exc))

        if resp.status_code != 200:
            return GroqResponse(error=f"Groq HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        prob = None
        explanation = None
        # Extract first float between 0 and 1
        match = re.search(r"(0?\.?\d{1,3}|1\.0|1)(?![\d])", message)
        if match:
            try:
                prob = float(match.group(1))
                if prob > 1:
                    prob = prob / 100.0  # Handle percentages typed as 70 -> 0.7
            except ValueError:
                prob = None
        # Capture short reason after the probability if present
        reason_match = re.search(r"\d[^\d]*(.+)", message, re.DOTALL)
        if reason_match:
            explanation = reason_match.group(1).strip()

        return GroqResponse(
            probability=prob,
            explanation=explanation,
            raw=message.strip() or None,
        )


# Singleton instance for reuse
groq_client = GroqClient()

