"""Stage L5: Evidence-verified code review and validator filter."""
from __future__ import annotations

from pathlib import Path
from pipeline.contracts.tasks import BuildTask
from pipeline.contracts.review import ReviewReport, PriorFindingStatus
from pipeline.review.evidence import evidence_ok


def validate_review_report(
    report: ReviewReport,
    repo_root: Path,
    known_ids: set[str],
    open_finding_ids: list[str],
) -> ReviewReport:
    """Filter out any finding whose file, line, quote, or ref IDs fail deterministic evidence_ok()."""
    valid_findings = []
    dropped = 0
    for f in report.findings:
        if evidence_ok(f, repo_root, known_ids):
            valid_findings.append(f)
        else:
            dropped += 1

    existing_checks = {c.finding_id: c for c in report.prior_finding_checks}
    still_open_ids = {f.id for f in valid_findings}
    for oid in open_finding_ids:
        if oid not in existing_checks:
            existing_checks[oid] = PriorFindingStatus(
                finding_id=oid,
                still_present=oid in still_open_ids,
                evidence_note="Verified automatically against round findings and L4 status.",
            )

    return ReviewReport(
        build_id=report.build_id,
        round_no=report.round_no,
        commit_sha=report.commit_sha,
        files_reviewed=report.files_reviewed,
        findings=valid_findings,
        prior_finding_checks=list(existing_checks.values()),
        dropped_unverifiable=dropped,
    )
