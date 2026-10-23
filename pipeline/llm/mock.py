"""Deterministic MockLLMClient for offline testing and reference runs."""
from __future__ import annotations

from typing import Any, Callable, TypeVar
from pydantic import BaseModel
from .base import BaseLLMClient

T = TypeVar("T", bound=BaseModel)


class DeterministicMockLLMClient(BaseLLMClient):
    """
    Deterministic mock LLM client that dispatches by target Pydantic schema type
    or custom registered handler functions.
    """

    def __init__(self, model_id: str = "mock-deterministic-v1") -> None:
        self.model_id = model_id
        self._handlers: dict[type[BaseModel], Callable[[str], Any]] = {}
        self.calls: list[tuple[str, str]] = []

    def register(self, schema: type[T], handler: Callable[[str], T]) -> None:
        self._handlers[schema] = handler

    def generate_structured(self, prompt: str, schema: type[T]) -> T:
        self.calls.append((schema.__name__, prompt))
        if schema in self._handlers:
            return self._handlers[schema](prompt)
        raise LookupError(f"No deterministic mock handler registered for schema {schema.__name__}")
