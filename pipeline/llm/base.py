"""Base structured LLM client interface (compatible with Phase 1 BaseLLMClient)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMClient(ABC):
    model_id: str = "abstract-model"

    @abstractmethod
    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        """Generate a validated Pydantic instance matching `schema`."""
