"""Deterministic QA-Checker (Requirement Alignment & Public Symbol Conformance)."""
from __future__ import annotations

from pipeline.contracts.base import Contract, BuildId, AcId, TestId
from pipeline.contracts.tasks import BuildTask
from pipeline.graph.port import GraphPort


class AlignmentDecision(Contract):
    build_id: BuildId
    requirement_ids: list[str]
    aligned: bool
    satisfied_criteria: list[AcId]
    missing_criteria: list[AcId]
    contradictory_evidence: list[str]
    evidence_artifact_ids: list[TestId]
    retry_instruction: str | None = None


def decide_alignment(task: BuildTask, g: GraphPort, commit: str) -> AlignmentDecision:
    sat: list[str] = []
    miss: list[str] = []
    evidence: list[str] = []
    for ac in task.ac_ids:
        passing = [t for t in g.tests_verifying(ac) if g.test_passed(t, commit)]
        (sat if passing else miss).append(ac)
        evidence += passing
    extra = g.public_symbols_outside_lld(task.id)
    parts: list[str] = []
    if miss:
        parts.append("Make these acceptance criteria pass, each with a test: " + ", ".join(miss) + ".")
    if extra:
        parts.append("Remove or move into the LLD these unapproved public symbols: " + ", ".join(extra) + ".")
    return AlignmentDecision(
        build_id=task.id,
        requirement_ids=[*task.task_ids, *task.ac_ids],
        aligned=not miss and not extra,
        satisfied_criteria=sat,
        missing_criteria=miss,
        contradictory_evidence=extra,
        evidence_artifact_ids=sorted(set(evidence)),
        retry_instruction=" ".join(parts) or None,
    )
