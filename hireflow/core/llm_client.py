"""LLM client wrapper supporting Anthropic API with structured output and offline fallback."""

import json
import re
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel
from hireflow.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Robust client interfacing with Anthropic or fallback heuristic engine."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self._client = None

    @property
    def is_live(self) -> bool:
        return self._client is not None

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 4096) -> str:
        """Call Claude API or return empty if not connected."""
        if not self._client:
            return ""

        try:
            messages = [{"role": "user", "content": prompt}]
            kwargs = {
                "model": settings.primary_model,
                "max_tokens": max_tokens,
                "messages": messages,
                "temperature": settings.temperature,
            }
            if system:
                kwargs["system"] = system

            response = self._client.messages.create(**kwargs)
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return ""
        except Exception as e:
            # Fallback on network or API failure
            return ""

    def generate_structured(self, prompt: str, schema_class: Type[T], system: Optional[str] = None) -> Optional[T]:
        """Request structured JSON from Claude and parse into target Pydantic model."""
        if not self._client:
            return None

        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        system_instruction = (
            f"{system or ''}\n\n"
            "You MUST respond ONLY with valid JSON matching the following JSON Schema. "
            "Do not include any conversational preamble or markdown code fences other than ```json ```:\n"
            f"{schema_json}"
        )

        raw_output = self.complete(prompt=prompt, system=system_instruction)
        if not raw_output:
            return None

        try:
            # Extract JSON block
            cleaned = raw_output.strip()
            if "```json" in cleaned:
                match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
            elif "```" in cleaned:
                match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)

            data = json.loads(cleaned)
            return schema_class.model_validate(data)
        except Exception:
            return None


# Global LLM client
llm_client = LLMClient()
