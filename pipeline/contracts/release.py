"""Stage L7 ReleaseBundle and ReviewArtifacts contracts."""
from __future__ import annotations

from .base import Contract


class ReviewArtifacts(Contract):
    summary_md: str
    findings_json: str
    unresolved_md: str
    requirements_trace_json: str
    test_evidence_json: str
    security_sarif: str
    change_manifest_json: str
    suppressions_yaml: str


class ReleaseBundle(Contract):
    run_id: str
    graph_epoch: int
    handoff_hash: str
    lld_hash: str
    commit_sha: str
    images: list[str]
    sbom: str
    provenance: str
    iac_plan: str
    runbook: str
    review: ReviewArtifacts
    sandbox_url: str
    smoke_passed: bool
    db_migration_verified: bool = True
