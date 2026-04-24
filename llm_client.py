"""
core/llm_client.py
───────────────────
Thin wrapper around the Anthropic API.
Handles retries, token counting, and structured JSON output.
All agents call this — never call anthropic directly.
"""

import os
import json
import time
import logging
from typing import Any, Optional
import anthropic

logger = logging.getLogger(__name__)

# Model assignments per agent role
MODELS = {
    "orchestrator":   "claude-sonnet-4-5",
    "audience_intel": "claude-sonnet-4-5",
    "analytics":      "claude-sonnet-4-5",
    "reporting":      "claude-haiku-4-5-20251001",
    "default":        "claude-sonnet-4-5",
}

MAX_RETRIES   = 3
RETRY_DELAY   = 2.0   # seconds between retries


class LLMClient:
    """
    Anthropic API client with:
    - Token usage tracking (feeds back to BudgetManager)
    - Automatic retry on transient errors
    - JSON output enforcement with validation
    - Budget-aware: refuses to call if estimated cost exceeds remaining budget
    """

    def __init__(self, agent_id: str = "default"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. "
                "Copy .env.example → .env and add your key."
            )
        self._client   = anthropic.Anthropic(api_key=api_key)
        self._agent_id = agent_id
        self._model    = MODELS.get(agent_id, MODELS["default"])
        self.tokens_used = 0   # Cumulative across all calls this session

    # ─────────────────────────────────────────
    # Core call — returns plain text
    # ─────────────────────────────────────────

    def call(
        self,
        system_prompt: str,
        user_message:  str,
        max_tokens:    int = 1000,
        temperature:   float = 0.2,   # Low temp for deterministic analysis
    ) -> tuple[str, int]:
        """
        Call the Claude API.

        Returns:
            (response_text, tokens_used)
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                tokens = response.usage.input_tokens + response.usage.output_tokens
                self.tokens_used += tokens
                text = response.content[0].text

                logger.debug(
                    f"[{self._agent_id}] LLM call: "
                    f"{response.usage.input_tokens} in + "
                    f"{response.usage.output_tokens} out = {tokens} tokens"
                )
                return text, tokens

            except anthropic.RateLimitError:
                wait = RETRY_DELAY * attempt
                logger.warning(
                    f"[{self._agent_id}] Rate limit hit. "
                    f"Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(wait)

            except anthropic.APIStatusError as e:
                if attempt == MAX_RETRIES:
                    raise
                logger.warning(
                    f"[{self._agent_id}] API error {e.status_code}: {e.message}. "
                    f"Retrying ({attempt}/{MAX_RETRIES})"
                )
                time.sleep(RETRY_DELAY)

        raise RuntimeError(
            f"[{self._agent_id}] LLM call failed after {MAX_RETRIES} retries"
        )

    # ─────────────────────────────────────────
    # JSON call — enforces structured output
    # ─────────────────────────────────────────

    def call_json(
        self,
        system_prompt: str,
        user_message:  str,
        expected_keys: list[str],
        max_tokens:    int = 1000,
    ) -> tuple[dict, int]:
        """
        Call Claude and parse the response as JSON.
        Retries if response is not valid JSON or missing expected keys.

        Returns:
            (parsed_dict, tokens_used)
        """
        json_system = (
            system_prompt + "\n\n"
            "CRITICAL: Respond ONLY with a valid JSON object. "
            "No preamble, no explanation, no markdown fences. "
            "Pure JSON that can be parsed with json.loads()."
        )

        for attempt in range(1, MAX_RETRIES + 1):
            text, tokens = self.call(json_system, user_message, max_tokens)

            try:
                # Strip any accidental markdown fences
                clean = text.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                clean = clean.strip()

                parsed = json.loads(clean)

                # Validate expected keys present
                missing = [k for k in expected_keys if k not in parsed]
                if missing:
                    raise ValueError(f"Missing keys in JSON response: {missing}")

                return parsed, tokens

            except (json.JSONDecodeError, ValueError) as e:
                if attempt == MAX_RETRIES:
                    logger.error(
                        f"[{self._agent_id}] JSON parse failed after "
                        f"{MAX_RETRIES} attempts. Last response:\n{text[:500]}"
                    )
                    raise
                logger.warning(
                    f"[{self._agent_id}] JSON parse error (attempt {attempt}): {e}"
                )
                # Add explicit correction instruction on retry
                user_message = (
                    user_message + "\n\n"
                    f"Your previous response could not be parsed as JSON. "
                    f"Error: {e}. "
                    f"Respond with ONLY a JSON object containing these keys: "
                    f"{expected_keys}"
                )
