"""Retry and escalation ladder shared across stages and L5 review-fix loops."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class Rung(str, Enum):
    RETRY = "retry"
    WIDEN_CONTEXT = "widen_context"
    SPLIT_TASK = "split_task"
    ESCALATE_MODEL = "escalate_model"
    REPLAN_LLD = "replan_lld"
    REJECT_HANDOFF = "reject_handoff"
    FAIL = "fail_with_report"


LADDER = [
    Rung.RETRY,
    Rung.WIDEN_CONTEXT,
    Rung.SPLIT_TASK,
    Rung.ESCALATE_MODEL,
    Rung.REPLAN_LLD,
    Rung.REJECT_HANDOFF,
    Rung.FAIL,
]


class FailureRecord(BaseModel):
    task_id: str
    tool: str
    signature: str
    attempt: int


def next_rung(history: list[FailureRecord], per_rung: int = 2) -> Rung:
    idx = min(len(history) // max(1, per_rung), len(LADDER) - 1)
    if len(history) >= 2 and history[-1].signature == history[-2].signature:
        idx = min(idx + 1, len(LADDER) - 1)
    return LADDER[idx]
