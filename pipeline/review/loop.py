"""Stage L5 deterministic Review-Fix Loop controller and hardened FindingLedger."""
from __future__ import annotations

from enum import Enum
from hashlib import sha256
from typing import Protocol
from pydantic import BaseModel
from pipeline.contracts.tasks import BuildTask
from pipeline.contracts.review import (
    Finding,
    ReviewReport,
    PriorFindingStatus,
    Severity,
    Dimension,
)
from pipeline.contracts.verification import VerificationReport
from pipeline.orchestration.retry import Rung, FailureRecord, next_rung
from pipeline.graph.port import GraphPort
from .alignment import decide_alignment
from .evidence import review_score


class LoopConfig(BaseModel):
    max_rounds: int = 6
    rung_step: int = 1
    min_score: int = 4
    proof_required: tuple[Dimension, ...] = (Dimension.CORRECTNESS, Dimension.SECURITY)


class LoopOutcome(str, Enum):
    CONVERGED = "converged"
    SPLIT = "split_task"
    REPLAN_LLD = "replan_lld"
    REJECT_HANDOFF = "reject_handoff"
    FAILED = "failed"


class Ports(Protocol):
    def head(self, task: BuildTask) -> str: ...
    def verify(self, task: BuildTask, commit: str) -> VerificationReport: ...
    def review(
        self, task: BuildTask, round_no: int, vr: VerificationReport, open_ids: list[str]
    ) -> ReviewReport: ...
    def validate(self, report: ReviewReport) -> ReviewReport: ...
    def fix(
        self, task: BuildTask, findings: list[Finding], instruction: str | None, rung: Rung
    ) -> str: ...
    def fix_proof(self, f: Finding, before: str, after: str) -> bool: ...
    def graph(self) -> GraphPort: ...


def verification_findings(vr: VerificationReport, task: BuildTask) -> list[Finding]:
    """Convert deterministic L4 layer failures into structured blocker Findings."""
    out: list[Finding] = []
    seq = 1
    for layer in vr.layers:
        if layer.passed:
            continue
        dim = (
            Dimension.SECURITY
            if layer.layer in ("sast", "secrets", "deps", "container", "iac", "dast")
            else Dimension.CORRECTNESS
            if layer.layer in ("unit", "mutation", "property", "contract", "integration", "acceptance")
            else Dimension.CONVENTIONS
        )
        for fail_msg in layer.failures or [f"{layer.layer} check failed"]:
            f_id = f"FND-{900 + seq:03d}"
            seq += 1
            out.append(
                Finding(
                    id=f_id,
                    dimension=dim,
                    severity=Severity.BLOCKER,
                    rule=f"L4_{layer.layer.upper()}",
                    file=task.files_owned[0],
                    line=1,
                    symbol_name="module",
                    quote=fail_msg[:60] if len(fail_msg) >= 3 else "err",
                    impact=f"Deterministic L4 gate '{layer.layer}' failed: {fail_msg}",
                    refs=[task.module_id],
                    source="verification",
                )
            )
    return out


class FindingLedger:
    """
    Hardened ledger that keys findings by AST symbol identity (`rule|file|symbol_name`)
    rather than volatile quote text (fixing GAP-11) and tracks two-factor fix verification.
    """

    def __init__(self) -> None:
        self._f: dict[str, Finding] = {}
        self._s: dict[str, str] = {}  # open | fixed_pending_review | verified
        self._id_to_key: dict[str, str] = {}

    @staticmethod
    def key(f: Finding) -> str:
        return f"{f.rule}|{f.file}|{f.symbol_name.strip()}"

    def absorb(
        self,
        raised: list[Finding],
        prior_checks: list[PriorFindingStatus] | None = None,
        l4_passed: bool = True,
    ) -> None:
        raised_keys = {self.key(f) for f in raised}
        check_map: dict[str, bool] = {}
        for chk in prior_checks or []:
            check_map[chk.finding_id] = chk.still_present

        for f in raised:
            k = self.key(f)
            self._f[k] = f
            self._s[k] = "open"
            self._id_to_key[f.id] = k

        for k, status in list(self._s.items()):
            f_obj = self._f[k]
            if status == "fixed_pending_review":
                still_there = check_map.get(f_obj.id, False)
                if k not in raised_keys and not still_there and l4_passed:
                    self._s[k] = "verified"
                else:
                    self._s[k] = "open"
            elif status == "open" and f_obj.source in ("verification", "fix_proof"):
                if k not in raised_keys and l4_passed:
                    self._s[k] = "verified"

    def open(self) -> list[Finding]:
        return [self._f[k] for k, s in self._s.items() if s == "open"]

    def open_ids(self) -> list[str]:
        return [f.id for f in self.open()]

    def mark_fixed(self, fs: list[Finding]) -> None:
        for f in fs:
            k = self.key(f)
            if k in self._s:
                self._s[k] = "fixed_pending_review"

    def inject_proof_failure(self, f: Finding, round_no: int) -> None:
        """Emit explicit diagnostic finding when fix_proof fails (fixing GAP-12)."""
        proof_id = f"FND-{800 + round_no:03d}"
        pf = Finding(
            id=proof_id,
            dimension=f.dimension,
            severity=Severity.BLOCKER,
            rule="FIX_PROOF_REQUIRED",
            file=f.file,
            line=f.line,
            symbol_name=f.symbol_name,
            quote=f.quote,
            impact=(
                f"Fix proof failed for {f.id} ({f.rule}): regression test must fail on "
                f"pre-fix commit and pass on post-fix commit."
            ),
            refs=f.refs,
            source="fix_proof",
        )
        k = self.key(pf)
        self._f[k] = pf
        self._s[k] = "open"
        self._id_to_key[pf.id] = k

    def all_records(self) -> list[dict[str, object]]:
        return [
            {"finding": self._f[k].dump_json_dict(), "status": self._s[k]}
            for k in sorted(self._f)
        ]

    def unresolved(self) -> list[Finding]:
        return [self._f[k] for k, s in self._s.items() if s != "verified"]

    def signature(self) -> str:
        opened = sorted(k for k, s in self._s.items() if s == "open")
        return sha256("|".join(opened).encode("utf-8")).hexdigest()[:16]


def review_fix_loop(
    task: BuildTask, ports: Ports, cfg: LoopConfig = LoopConfig()
) -> tuple[LoopOutcome, FindingLedger]:
    ledger = FindingLedger()
    history: list[FailureRecord] = []
    commit = ports.head(task)

    for round_no in range(1, cfg.max_rounds + 1):
        vr = ports.verify(task, commit)
        raw_report = ports.review(task, round_no, vr, ledger.open_ids())
        report = ports.validate(raw_report)
        ledger.absorb(
            verification_findings(vr, task) + list(report.findings),
            prior_checks=report.prior_finding_checks,
            l4_passed=vr.passed,
        )
        decision = decide_alignment(task, ports.graph(), commit)
        if vr.passed and decision.aligned and review_score(ledger.open()) >= cfg.min_score:
            return LoopOutcome.CONVERGED, ledger

        rung = next_rung(history, per_rung=cfg.rung_step)
        history.append(
            FailureRecord(
                task_id=task.id,
                tool="review_fix_loop",
                signature=ledger.signature(),
                attempt=round_no,
            )
        )
        if rung is Rung.SPLIT_TASK:
            return LoopOutcome.SPLIT, ledger
        if rung is Rung.REPLAN_LLD:
            return LoopOutcome.REPLAN_LLD, ledger
        if rung is Rung.REJECT_HANDOFF:
            return LoopOutcome.REJECT_HANDOFF, ledger
        if rung is Rung.FAIL:
            return LoopOutcome.FAILED, ledger

        before = commit
        targets = ledger.open()
        commit = ports.fix(task, targets, decision.retry_instruction, rung)
        proven: list[Finding] = []
        for f in targets:
            needs_proof = (
                f.source == "reviewer"
                and f.dimension in cfg.proof_required
                and f.severity is not Severity.MINOR
            )
            if not needs_proof or ports.fix_proof(f, before, commit):
                proven.append(f)
            else:
                ledger.inject_proof_failure(f, round_no)
        ledger.mark_fixed(proven)

    return LoopOutcome.FAILED, ledger
