"""Stage L4: Deterministic verification stage wrapper for L4-Task and L4-Trunk."""
from __future__ import annotations

from pathlib import Path
from pipeline.contracts.tasks import BuildTask
from pipeline.contracts.verification import VerificationReport
from pipeline.harness.adapters import run_l4_task_verification, run_l4_trunk_verification


def verify_task_worktree(
    repo_root: Path, task: BuildTask, commit_sha: str, max_cyclomatic: int = 10
) -> VerificationReport:
    return run_l4_task_verification(repo_root, task, commit_sha, max_cyclomatic=max_cyclomatic)


def verify_trunk_system(repo_root: Path, commit_sha: str) -> VerificationReport:
    return run_l4_trunk_verification(repo_root, commit_sha)
