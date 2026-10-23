"""Stage L4 Verification contracts (bifurcated into L4-Task and L4-Trunk)."""
from __future__ import annotations

from enum import Enum
from .base import Contract, BuildId


class VerificationTier(str, Enum):
    L4_TASK = "L4_TASK"
    L4_TRUNK = "L4_TRUNK"


class LayerResult(Contract):
    layer: str
    tier: VerificationTier = VerificationTier.L4_TASK
    tool: str
    passed: bool
    failures: list[str] = []
    artifact: str | None = None


class VerificationReport(Contract):
    build_id: BuildId | None = None
    tier: VerificationTier = VerificationTier.L4_TASK
    commit_sha: str
    layers: list[LayerResult]
    coverage_line: float | None = None
    coverage_branch: float | None = None
    mutation_score: float | None = None

    @property
    def passed(self) -> bool:
        return all(l.passed for l in self.layers)
