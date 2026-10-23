"""Standard stage envelope for content-addressed auditability."""
from __future__ import annotations

from typing import Any, Generic, TypeVar
from pydantic import BaseModel
from .base import Contract

T = TypeVar("T", bound=BaseModel)


class StageResult(Contract, Generic[T]):
    stage: str
    run_id: str
    graph_epoch: int
    input_hash: str
    model_id: str
    payload: Any
    validators_passed: list[str]
    started_at: str
    finished_at: str
