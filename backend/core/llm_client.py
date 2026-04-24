"""
core/llm_client.py
──────────────────
Unified LLM client that routes to the correct provider
based on the agent's assigned model.

Supports: Claude (Anthropic), GPT (OpenAI), Gemini (Google).
Falls back to mock responses when API keys are not set.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Agent -> model mapping (mirrors budget_manager.AGENT_MODELS)
AGENT_MODEL_MAP = {
    "orchestrator":   "claude-sonnet-4-5",
    "audience_intel": "claude-sonnet-4-5",
    "analytics":      "gpt-5",
    "meta_ads":       "gpt-5",
    "google_ads":     "gpt-5",
    "linkedin_ads":   "gpt-5",
    "creative":       "gemini-3-pro",
    "reporting":      "claude-haiku-4-5",
}


class LLMClient:
    """
    Calls the appropriate LLM based on the agent's model assignment.
    If no API key is configured, returns mock responses for development.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.model = AGENT_MODEL_MAP.get(agent_id, "claude-sonnet-4-5")
        self._tokens_used = 0

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    def call_json(
        self,
        system_prompt: str,
        user_message: str,
        expected_keys: list[str],
        max_tokens: int = 1024,
    ) -> tuple[dict, int]:
        """
        Call the LLM and parse the response as JSON.
        Returns (parsed_json, tokens_used).
        Raises ValueError if response doesn't contain expected keys.
        """
        if self.model.startswith("claude"):
            return self._call_anthropic(system_prompt, user_message, expected_keys, max_tokens)
        elif self.model.startswith("gpt"):
            return self._call_openai(system_prompt, user_message, expected_keys, max_tokens)
        elif self.model.startswith("gemini"):
            return self._call_google(system_prompt, user_message, expected_keys, max_tokens)
        else:
            logger.warning(f"Unknown model {self.model}, using mock response")
            return self._mock_response(expected_keys), 0

    def call_text(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
    ) -> tuple[str, int]:
        """
        Call the LLM and return raw text response.
        Returns (text, tokens_used).
        """
        if self.model.startswith("claude"):
            return self._call_anthropic_text(system_prompt, user_message, max_tokens)
        elif self.model.startswith("gpt"):
            return self._call_openai_text(system_prompt, user_message, max_tokens)
        elif self.model.startswith("gemini"):
            return self._call_google_text(system_prompt, user_message, max_tokens)
        else:
            return "Mock response — no API key configured.", 0

    # ──────────────────────────────────────────
    # Anthropic (Claude)
    # ──────────────────────────────────────────

    def _call_anthropic(
        self, system_prompt: str, user_message: str, expected_keys: list[str], max_tokens: int
    ) -> tuple[dict, int]:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.info(f"[{self.agent_id}] No ANTHROPIC_API_KEY — using mock response")
            return self._mock_response(expected_keys), 0

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-5-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            text = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            self._tokens_used += tokens

            parsed = self._extract_json(text)
            self._validate_keys(parsed, expected_keys)
            return parsed, tokens

        except ImportError:
            logger.warning("anthropic package not installed. Run: pip install anthropic")
            return self._mock_response(expected_keys), 0
        except Exception as e:
            logger.error(f"[{self.agent_id}] Anthropic API error: {e}")
            return self._mock_response(expected_keys), 0

    def _call_anthropic_text(
        self, system_prompt: str, user_message: str, max_tokens: int
    ) -> tuple[str, int]:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "Mock response — set ANTHROPIC_API_KEY for real calls.", 0

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-5-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            tokens = response.usage.input_tokens + response.usage.output_tokens
            self._tokens_used += tokens
            return response.content[0].text, tokens
        except Exception as e:
            logger.error(f"[{self.agent_id}] Anthropic API error: {e}")
            return f"Error: {e}", 0

    # ──────────────────────────────────────────
    # OpenAI (GPT)
    # ──────────────────────────────────────────

    def _call_openai(
        self, system_prompt: str, user_message: str, expected_keys: list[str], max_tokens: int
    ) -> tuple[dict, int]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.info(f"[{self.agent_id}] No OPENAI_API_KEY — using mock response")
            return self._mock_response(expected_keys), 0

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            self._tokens_used += tokens

            parsed = self._extract_json(text)
            self._validate_keys(parsed, expected_keys)
            return parsed, tokens

        except ImportError:
            logger.warning("openai package not installed. Run: pip install openai")
            return self._mock_response(expected_keys), 0
        except Exception as e:
            logger.error(f"[{self.agent_id}] OpenAI API error: {e}")
            return self._mock_response(expected_keys), 0

    def _call_openai_text(
        self, system_prompt: str, user_message: str, max_tokens: int
    ) -> tuple[str, int]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Mock response — set OPENAI_API_KEY for real calls.", 0

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            tokens = response.usage.total_tokens if response.usage else 0
            self._tokens_used += tokens
            return response.choices[0].message.content, tokens
        except Exception as e:
            logger.error(f"[{self.agent_id}] OpenAI API error: {e}")
            return f"Error: {e}", 0

    # ──────────────────────────────────────────
    # Google (Gemini)
    # ──────────────────────────────────────────

    def _call_google(
        self, system_prompt: str, user_message: str, expected_keys: list[str], max_tokens: int
    ) -> tuple[dict, int]:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.info(f"[{self.agent_id}] No GOOGLE_API_KEY — using mock response")
            return self._mock_response(expected_keys), 0

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                user_message,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                ),
            )
            text = response.text
            tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
            self._tokens_used += tokens

            parsed = self._extract_json(text)
            self._validate_keys(parsed, expected_keys)
            return parsed, tokens

        except ImportError:
            logger.warning("google-generativeai not installed. Run: pip install google-generativeai")
            return self._mock_response(expected_keys), 0
        except Exception as e:
            logger.error(f"[{self.agent_id}] Google API error: {e}")
            return self._mock_response(expected_keys), 0

    def _call_google_text(
        self, system_prompt: str, user_message: str, max_tokens: int
    ) -> tuple[str, int]:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "Mock response — set GOOGLE_API_KEY for real calls.", 0

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system_prompt)
            response = model.generate_content(user_message)
            tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
            self._tokens_used += tokens
            return response.text, tokens
        except Exception as e:
            logger.error(f"[{self.agent_id}] Google API error: {e}")
            return f"Error: {e}", 0

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")

    @staticmethod
    def _validate_keys(data: dict, expected_keys: list[str]) -> None:
        """Warn if expected keys are missing (don't raise — agent should handle gracefully)."""
        missing = [k for k in expected_keys if k not in data]
        if missing:
            logger.warning(f"LLM response missing keys: {missing}")

    @staticmethod
    def _mock_response(expected_keys: list[str]) -> dict:
        """Generate a mock response for development without API keys."""
        mock_values = {
            "roas_prediction": 4.2,
            "ltv_score": 7.5,
            "priority": "scale",
            "budget_rec": "increase 30%",
            "targeting_notes": "Mock: High conversion rate from CRM data suggests strong purchase intent.",
            "ad_copy_angles": ["Value proposition", "Social proof", "Urgency"],
            "targeting_strategy": "Mock: Focus spend on CRM-sourced segments with proven ROAS above 3x.",
            "top_segment_id": "seg_past_customers",
            "lookalike_seed_ids": ["seg_past_customers", "seg_high_ltv"],
            "key_insight": "Mock: Past customers convert at 3x the rate of cold audiences.",
            "roas_report": [],
            "actions": [],
            "headline": "Special offer for you",
            "body": "Mock ad copy",
            "cta": "Learn More",
            "digest": "Mock pipeline digest",
        }
        return {k: mock_values.get(k, f"mock_{k}") for k in expected_keys}
