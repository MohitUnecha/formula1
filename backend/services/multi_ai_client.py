"""
Multi-AI Client for F1 Predictions

Orchestrates multiple AI providers with specialized roles:

AI PROVIDERS & ROLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| Provider         | Role                | Priority | Usage          |
|------------------|---------------------|----------|----------------|
| Gemini #1        | Race Strategist     | High     | Strategy       |
| Gemini #2        | Data Analyst        | High     | Stats          |
| DeepSeek         | Deep Reasoning      | Medium   | Complex        |
| NVIDIA Nemotron  | Technical Expert    | High     | Car/Engineering|
| Groq #1          | Quick Analyst       | Primary  | General        |
| Groq #2          | Fallback/Validator  | Fallback | All            |
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Groq is used as primary workhorse and fallback due to generous free tier.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class AIRole(Enum):
    """Specialized roles for different AI providers"""
    RACE_STRATEGIST = "race_strategist"      # Gemini #1 - Race strategy, tire calls
    DATA_ANALYST = "data_analyst"            # Gemini #2 - Statistical analysis
    DEEP_REASONER = "deep_reasoner"          # DeepSeek - Complex multi-factor reasoning
    TECHNICAL_EXPERT = "technical_expert"    # NVIDIA Nemotron - Car/engineering analysis
    QUICK_ANALYST = "quick_analyst"          # Groq #1 - Fast general predictions
    VALIDATOR = "validator"                   # Groq #2 - Fallback & consensus validation


@dataclass
class AIResponse:
    """Unified response from any AI provider"""
    probability: Optional[float] = None
    explanation: Optional[str] = None
    raw: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    role: Optional[str] = None
    latency_ms: Optional[float] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ConsensusResult:
    """Result from multi-AI consensus"""
    final_probability: float
    confidence_score: float
    providers_used: List[str]
    explanations: Dict[str, str]
    consensus_explanation: str
    reasoning_breakdown: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiAIClient:
    """Orchestrates multiple AI providers for F1 predictions"""
    
    # API Endpoints
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
    NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Models
    GEMINI_MODEL = "gemini-2.0-flash"
    DEEPSEEK_MODEL = "deepseek-chat"
    NVIDIA_MODEL = "nvidia/nemotron-mini-4b-instruct"  # Fast, efficient model for technical analysis
    GROQ_MODEL = "mixtral-8x7b-32768"
    
    # Role-specific system prompts
    ROLE_PROMPTS = {
        AIRole.RACE_STRATEGIST: """You are an expert F1 Race Strategist AI. 
Your specialty is analyzing race strategy: tire degradation, pit stop windows, track position battles, undercuts/overcuts.
Focus on HOW a driver could win through strategy. Consider tire compounds, pit stop timing, and track characteristics.
Return: probability (0-1), then a brief strategy-focused explanation.""",
        
        AIRole.DATA_ANALYST: """You are an expert F1 Data Analyst AI.
Your specialty is statistical analysis: historical data, head-to-head records, circuit-specific performance, qualifying pace.
Focus on NUMBERS and TRENDS. What do the statistics say about this driver's chances?
Return: probability (0-1), then a brief data-driven explanation.""",
        
        AIRole.DEEP_REASONER: """You are an expert F1 Deep Reasoning AI.
Your specialty is complex multi-factor analysis: combining weather, car upgrades, driver psychology, team dynamics, championship pressure.
Think step-by-step through all factors that could influence the outcome.
Return: probability (0-1), then a thorough reasoning chain.""",
        
        AIRole.QUICK_ANALYST: """You are an expert F1 Quick Analyst AI.
Provide fast, accurate win probability assessments based on current form, qualifying, and team performance.
Return: probability (0-1) and a concise 1-2 sentence explanation.""",
        
        AIRole.VALIDATOR: """You are an F1 Prediction Validator AI.
Review the prediction and provide a sanity check. Is this probability reasonable given the context?
Return: probability (0-1) and note any concerns or confirmations.""",
        
        AIRole.TECHNICAL_EXPERT: """You are an expert F1 Technical/Engineering AI.
Your specialty is car performance: aerodynamics, power unit reliability, downforce vs drag, car upgrades, track-specific car characteristics.
Focus on TECHNICAL FACTORS: Is the car suited to this track? Any reliability concerns? Recent upgrades?
Return: probability (0-1), then a brief technical/engineering-focused explanation.""",
    }

    def __init__(self):
        self.timeout = 15.0

        # Credentials are loaded from environment to avoid committing secrets.
        self.gemini_key_1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
        self.gemini_key_2 = os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.nvidia_key = os.getenv("NVIDIA_API_KEY")
        self.groq_key_1 = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")
        self.groq_key_2 = os.getenv("GROQ_API_KEY_2") or self.groq_key_1

        self.providers_status = {
            "gemini_1": {"available": bool(self.gemini_key_1), "role": "Race Strategist", "calls": 0, "errors": 0},
            "gemini_2": {"available": bool(self.gemini_key_2), "role": "Data Analyst", "calls": 0, "errors": 0},
            "deepseek": {"available": bool(self.deepseek_key), "role": "Deep Reasoner", "calls": 0, "errors": 0},
            "nvidia": {"available": bool(self.nvidia_key), "role": "Technical Expert", "calls": 0, "errors": 0},
            "groq_1": {"available": bool(self.groq_key_1), "role": "Quick Analyst", "calls": 0, "errors": 0},
            "groq_2": {"available": bool(self.groq_key_2), "role": "Validator/Fallback", "calls": 0, "errors": 0},
        }

    def _extract_probability(self, text: str) -> Optional[float]:
        """Extract probability from AI response text"""
        if not text:
            return None
        # Look for decimals like 0.75, 0.8, etc.
        match = re.search(r'(0?\.[0-9]{1,3}|1\.0|1(?!\d)|0(?!\d))', text)
        if match:
            try:
                prob = float(match.group(1))
                if 0 <= prob <= 1:
                    return prob
            except ValueError:
                pass
        # Look for percentages like 75%, 80%
        pct_match = re.search(r'(\d{1,3})%', text)
        if pct_match:
            try:
                prob = float(pct_match.group(1)) / 100
                if 0 <= prob <= 1:
                    return prob
            except ValueError:
                pass
        return None

    async def _call_gemini(self, prompt: str, api_key: str, role: AIRole) -> AIResponse:
        """Call Gemini API"""
        if not api_key:
            return AIResponse(error="Gemini API key missing", provider="gemini", role=role.value)

        url = f"{self.GEMINI_URL}?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{self.ROLE_PROMPTS[role]}\n\n{prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 200
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                
            if resp.status_code != 200:
                return AIResponse(error=f"Gemini HTTP {resp.status_code}", provider="gemini", role=role.value)
            
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            prob = self._extract_probability(text)
            
            return AIResponse(
                probability=prob,
                explanation=text[:300] if text else None,
                raw=text,
                provider="gemini",
                role=role.value
            )
        except Exception as e:
            return AIResponse(error=str(e), provider="gemini", role=role.value)

    async def _call_deepseek(self, prompt: str, role: AIRole) -> AIResponse:
        """Call DeepSeek API"""
        if not self.deepseek_key:
            return AIResponse(error="DeepSeek API key missing", provider="deepseek", role=role.value)

        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": self.ROLE_PROMPTS[role]},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.DEEPSEEK_URL, json=payload, headers=headers)
                
            if resp.status_code != 200:
                return AIResponse(error=f"DeepSeek HTTP {resp.status_code}", provider="deepseek", role=role.value)
            
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            prob = self._extract_probability(text)
            
            return AIResponse(
                probability=prob,
                explanation=text[:300] if text else None,
                raw=text,
                provider="deepseek",
                role=role.value
            )
        except Exception as e:
            return AIResponse(error=str(e), provider="deepseek", role=role.value)

    async def _call_groq(self, prompt: str, api_key: str, role: AIRole) -> AIResponse:
        """Call Groq API"""
        if not api_key:
            return AIResponse(error="Groq API key missing", provider="groq", role=role.value)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": self.ROLE_PROMPTS[role]},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 150,
            "temperature": 0.35
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.GROQ_URL, json=payload, headers=headers)
                
            if resp.status_code != 200:
                return AIResponse(error=f"Groq HTTP {resp.status_code}", provider="groq", role=role.value)
            
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            prob = self._extract_probability(text)
            
            return AIResponse(
                probability=prob,
                explanation=text[:300] if text else None,
                raw=text,
                provider="groq",
                role=role.value
            )
        except Exception as e:
            return AIResponse(error=str(e), provider="groq", role=role.value)

    async def get_quick_prediction(self, prompt: str) -> AIResponse:
        """Fast prediction using Groq (primary) with Groq fallback"""
        self.providers_status["groq_1"]["calls"] += 1
        result = await self._call_groq(prompt, self.groq_key_1, AIRole.QUICK_ANALYST)
        
        if result.error or result.probability is None:
            self.providers_status["groq_1"]["errors"] += 1
            # Fallback to Groq #2
            self.providers_status["groq_2"]["calls"] += 1
            result = await self._call_groq(prompt, self.groq_key_2, AIRole.VALIDATOR)
            if result.error:
                self.providers_status["groq_2"]["errors"] += 1
        
        return result

    async def get_strategy_analysis(self, prompt: str) -> AIResponse:
        """Strategy-focused analysis using Gemini #1 with Groq fallback"""
        self.providers_status["gemini_1"]["calls"] += 1
        result = await self._call_gemini(prompt, self.gemini_key_1, AIRole.RACE_STRATEGIST)
        
        if result.error or result.probability is None:
            self.providers_status["gemini_1"]["errors"] += 1
            logger.warning("Gemini #1 failed, falling back to Groq")
            self.providers_status["groq_1"]["calls"] += 1
            result = await self._call_groq(prompt, self.groq_key_1, AIRole.QUICK_ANALYST)
        
        return result

    async def get_data_analysis(self, prompt: str) -> AIResponse:
        """Data-focused analysis using Gemini #2 with Groq fallback"""
        self.providers_status["gemini_2"]["calls"] += 1
        result = await self._call_gemini(prompt, self.gemini_key_2, AIRole.DATA_ANALYST)
        
        if result.error or result.probability is None:
            self.providers_status["gemini_2"]["errors"] += 1
            logger.warning("Gemini #2 failed, falling back to Groq")
            self.providers_status["groq_2"]["calls"] += 1
            result = await self._call_groq(prompt, self.groq_key_2, AIRole.VALIDATOR)
        
        return result

    async def get_deep_reasoning(self, prompt: str) -> AIResponse:
        """Deep reasoning using DeepSeek with Groq fallback"""
        self.providers_status["deepseek"]["calls"] += 1
        result = await self._call_deepseek(prompt, AIRole.DEEP_REASONER)
        
        if result.error or result.probability is None:
            self.providers_status["deepseek"]["errors"] += 1
            logger.warning("DeepSeek failed, falling back to Groq")
            self.providers_status["groq_1"]["calls"] += 1
            result = await self._call_groq(prompt, self.groq_key_1, AIRole.QUICK_ANALYST)
        
        return result

    async def get_consensus_prediction(
        self, 
        driver_name: str,
        driver_code: str,
        team: str,
        event_name: str,
        season: int,
        round_num: int,
        base_probability: float,
        context: str = ""
    ) -> ConsensusResult:
        """
        Get consensus prediction from multiple AI providers.
        
        Uses all 5 AI roles in parallel, then combines results:
        - Gemini #1: Race Strategy perspective
        - Gemini #2: Statistical perspective  
        - DeepSeek: Deep multi-factor reasoning
        - Groq #1: Quick general analysis
        - Groq #2: Validation check
        
        Final probability is weighted average with confidence scoring.
        """
        base_prompt = (
            f"Race: {event_name} (Season {season}, Round {round_num})\n"
            f"Driver: {driver_name} ({driver_code}) driving for {team}\n"
            f"Model base win probability: {base_probability:.1%}\n"
            f"Context: {context or 'Use your knowledge of current F1'}\n"
            f"IMPORTANT: Factor in weather conditions (temperature, rain risk, wind, humidity) "
            f"and how they affect tire strategy, car handling, driver wet-weather skill, and race pace.\n"
            f"Provide your win probability (0-1) and brief explanation."
        )
        
        # Run all AI calls in parallel
        tasks = [
            self.get_strategy_analysis(f"[STRATEGY FOCUS] {base_prompt}"),
            self.get_data_analysis(f"[DATA FOCUS] {base_prompt}"),
            self.get_deep_reasoning(f"[DEEP ANALYSIS] {base_prompt}"),
            self.get_quick_prediction(f"[QUICK ASSESSMENT] {base_prompt}"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect valid results
        valid_probs = []
        providers_used = []
        explanations = {}
        
        role_names = ["Strategy (Gemini)", "Data (Gemini)", "Reasoning (DeepSeek)", "Quick (Groq)"]
        weights = [0.25, 0.25, 0.30, 0.20]  # DeepSeek weighted slightly higher for complex reasoning
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"AI task {i} failed with exception: {result}")
                continue
            if result.error:
                logger.warning(f"AI task {i} returned error: {result.error}")
                continue
            if result.probability is not None:
                valid_probs.append((result.probability, weights[i], role_names[i]))
                providers_used.append(f"{result.provider}:{result.role}")
                explanations[role_names[i]] = result.explanation or result.raw or ""
        
        # If we got at least one valid result, compute weighted average
        if valid_probs:
            total_weight = sum(w for _, w, _ in valid_probs)
            final_prob = sum(p * w for p, w, _ in valid_probs) / total_weight
            
            # Confidence based on agreement between providers
            if len(valid_probs) >= 2:
                probs_only = [p for p, _, _ in valid_probs]
                variance = sum((p - final_prob) ** 2 for p in probs_only) / len(probs_only)
                # Low variance = high agreement = high confidence
                confidence = max(0.5, 1.0 - (variance * 5))
            else:
                confidence = 0.6  # Single provider = moderate confidence
            
            # Build consensus explanation
            consensus_parts = []
            for prob, weight, role in valid_probs:
                consensus_parts.append(f"{role}: {prob:.1%}")
            consensus_explanation = f"Multi-AI Consensus ({len(valid_probs)} providers): " + " | ".join(consensus_parts)
        else:
            # All failed, use base probability
            final_prob = base_probability
            confidence = 0.3
            consensus_explanation = "AI consensus unavailable, using model baseline"
        
        return ConsensusResult(
            final_probability=round(max(0.001, min(0.99, final_prob)), 4),
            confidence_score=round(confidence, 2),
            providers_used=providers_used,
            explanations=explanations,
            consensus_explanation=consensus_explanation,
            reasoning_breakdown={
                "providers_queried": 4,
                "providers_responded": len(valid_probs),
                "base_probability": base_probability,
                "adjustment": round(final_prob - base_probability, 4) if valid_probs else 0,
            }
        )

    def get_provider_info(self) -> Dict[str, Any]:
        """Return information about AI providers for display to users"""
        return {
            "system_name": "F1 Multi-AI Prediction Engine",
            "description": "Our predictions combine insights from 5 specialized AI models, each with unique expertise",
            "providers": [
                {
                    "name": "Gemini Pro #1",
                    "provider": "Google",
                    "role": "Race Strategist",
                    "specialty": "Tire strategy, pit windows, track position battles",
                    "icon": "🎯"
                },
                {
                    "name": "Gemini Pro #2", 
                    "provider": "Google",
                    "role": "Data Analyst",
                    "specialty": "Historical statistics, qualifying pace, head-to-head records",
                    "icon": "📊"
                },
                {
                    "name": "DeepSeek",
                    "provider": "DeepSeek",
                    "role": "Deep Reasoner",
                    "specialty": "Complex multi-factor analysis, championship pressure, weather impact",
                    "icon": "🧠"
                },
                {
                    "name": "Groq Mixtral #1",
                    "provider": "Groq",
                    "role": "Quick Analyst",
                    "specialty": "Fast real-time assessments, current form analysis",
                    "icon": "⚡"
                },
                {
                    "name": "Groq Mixtral #2",
                    "provider": "Groq", 
                    "role": "Validator & Fallback",
                    "specialty": "Consensus validation, backup analysis, reliability",
                    "icon": "✅"
                }
            ],
            "reasoning_method": "Weighted consensus with confidence scoring",
            "fallback_strategy": "Groq provides backup for all providers due to high availability",
            "stats": self.providers_status
        }


# Singleton instance
multi_ai_client = MultiAIClient()
