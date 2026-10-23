"""Stage L6 Conformance report contracts."""
from __future__ import annotations

from .base import Contract, StoryId, AcId, TaskId, ServiceId
from .handoff import _min_list


class JourneyStep(Contract):
    step: str
    expected: str
    observed: str
    passed: bool
    evidence: str


class JourneyResult(Contract):
    story_id: StoryId
    steps: list[JourneyStep] = _min_list(1)

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.steps)


class ConformanceReport(Contract):
    matrix_complete: bool
    uncovered_acs: list[AcId] = []
    unimplemented_tasks: list[TaskId] = []
    unrequested_components: list[ServiceId] = []
    journeys: list[JourneyResult] = []
    advisory_reverse_spec_notes: list[str] = []
