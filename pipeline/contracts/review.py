"""Stage L5 Review-Fix contracts with AST symbol anchoring and reverification checks."""
from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import Field
from .base import Contract, BuildId, ModuleId, AdrId, RiskId, FindingId
from .handoff import _min_list


class Severity(str, Enum):
    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"


class Dimension(str, Enum):
    REQUIREMENT_ALIGNMENT = "requirement_alignment"
    CORRECTNESS = "correctness"
    SECURITY = "security"
    BLAST_RADIUS = "blast_radius"
    ARCHITECTURE = "architecture"
    CONVENTIONS = "conventions"
    TEST_ADEQUACY = "test_adequacy"
    COMMIT_CONSISTENCY = "commit_consistency"
    PERFORMANCE = "performance"


class ReviewPackage(Contract):
    build_id: BuildId
    round_no: int = Field(ge=1)
    graph_epoch: int = Field(default=0, ge=0)
    commit_sha: str
    base_sha: str
    requirement_ids: list[str]
    lld_module: ModuleId
    adr_ids: list[AdrId] = []
    diff_path: str
    commit_message: str
    changed_files: list[str]
    related_files: list[str]
    verification_report: str
    scanner_sarif: str
    risk_pattern_ids: list[RiskId] = []
    open_finding_ids: list[FindingId] = []


class Finding(Contract):
    id: FindingId
    dimension: Dimension
    severity: Severity
    rule: str
    file: str
    line: int = Field(ge=1)
    symbol_name: str = Field(default="module", min_length=1)
    quote: str = Field(min_length=3)
    impact: str = Field(min_length=20)
    refs: list[str] = _min_list(1)
    repro_artifact: str | None = None
    source: Literal["reviewer", "scanner", "verification", "fix_proof"]


class PriorFindingStatus(Contract):
    finding_id: FindingId
    still_present: bool
    evidence_note: str = Field(min_length=5)


class ReviewReport(Contract):
    build_id: BuildId
    round_no: int
    commit_sha: str
    files_reviewed: list[str]
    findings: list[Finding]
    prior_finding_checks: list[PriorFindingStatus] = []
    dropped_unverifiable: int = 0
