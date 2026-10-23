"""Production OpenAI/Anthropic/Gemini compatible structured client adapter."""
from __future__ import annotations

import os
from typing import TypeVar
from pydantic import BaseModel
from .base import BaseLLMClient

T = TypeVar("T", bound=BaseModel)


class EnterpriseLLMClient(BaseLLMClient):
    """
    Adapter for live LLM execution in Antigravity or CI.
    Reads `PIPELINE_LLM_API_KEY` and `PIPELINE_LLM_MODEL` from environment variables.
    Falls back to raising an informative configuration error if called without credentials.
    """

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.environ.get("PIPELINE_LLM_MODEL", "gpt-4o-2024-08-06")
        self.api_key = os.environ.get("PIPELINE_LLM_API_KEY", "")

    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        if not self.api_key:
            raise RuntimeError(
                "PIPELINE_LLM_API_KEY is not set. Use `--mode deterministic` (default) "
                "or export PIPELINE_LLM_API_KEY in your environment."
            )
        raise NotImplementedError("Configure your provider SDK inside EnterpriseLLMClient.generate_structured.")
