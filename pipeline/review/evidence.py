"""Evidence verification and review score computation."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from pipeline.contracts.review import Finding, Severity, Dimension


def evidence_ok(f: Finding, repo: Path, known_ids: set[str]) -> bool:
    """Verify file exists inside repo, line is valid, quote matches window, and refs resolve."""
    p = (repo / f.file).resolve()
    if not p.is_relative_to(repo.resolve()) or not p.is_file():
        return False
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if f.line < 1 or f.line > len(lines):
        return False
    window = "\n".join(lines[max(0, f.line - 2) : f.line + 1])
    return f.quote.strip() in window and all(r in known_ids for r in f.refs)


def review_score(open_findings: list[Finding]) -> int:
    """
    Compute 0..5 review score.
    Note: Any open finding in CORRECTNESS or SECURITY caps score at 3 so it must be fixed before merge.
    """
    n = Counter(f.severity for f in open_findings)
    if n[Severity.BLOCKER] >= 3:
        return 0
    if n[Severity.BLOCKER]:
        return 1
    if n[Severity.MAJOR] >= 3:
        return 2
    if n[Severity.MAJOR]:
        return 3
    if any(f.dimension in (Dimension.CORRECTNESS, Dimension.SECURITY) for f in open_findings):
        return 3
    if n[Severity.MINOR]:
        return 4
    return 5
