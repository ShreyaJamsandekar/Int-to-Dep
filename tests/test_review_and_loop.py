"""Unit tests for evidence_ok, review_score, decide_alignment, FindingLedger, and review_fix_loop."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from pipeline.contracts.tasks import BuildTask
from pipeline.contracts.verification import VerificationReport, LayerResult
from pipeline.contracts.review import (
    Finding,
    ReviewReport,
    PriorFindingStatus,
    Severity,
    Dimension,
)
from pipeline.review.evidence import evidence_ok, review_score
from pipeline.review.loop import FindingLedger, review_fix_loop, LoopOutcome, LoopConfig
from pipeline.orchestration.retry import Rung
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


def mk_finding(sev: Severity, dim: Dimension = Dimension.CONVENTIONS, quote: str = "x = 1") -> Finding:
    return Finding(
        id="FND-001",
        dimension=dim,
        severity=sev,
        rule="RULE_X",
        file="a.py",
        line=1,
        symbol_name="my_func",
        quote=quote,
        impact="Order total is wrong for empty carts.",
        refs=["AC-001-01"],
        source="reviewer",
    )


class TestReviewAndLoop(unittest.TestCase):
    def test_score_table_and_security_correctness_floor(self) -> None:
        self.assertEqual(review_score([]), 5)
        self.assertEqual(review_score([mk_finding(Severity.MINOR, Dimension.CONVENTIONS)]), 4)
        self.assertEqual(review_score([mk_finding(Severity.MINOR, Dimension.SECURITY)]), 3)
        self.assertEqual(review_score([mk_finding(Severity.MAJOR)]), 3)
        self.assertEqual(review_score([mk_finding(Severity.MAJOR)] * 3), 2)
        self.assertEqual(review_score([mk_finding(Severity.BLOCKER)]), 1)
        self.assertEqual(review_score([mk_finding(Severity.BLOCKER)] * 3), 0)

    def test_evidence_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
            f = mk_finding(Severity.MINOR)
            self.assertTrue(evidence_ok(f, tmp_path, {"AC-001-01"}))
            self.assertFalse(evidence_ok(f.copy_with({"quote": "y = 2"}), tmp_path, {"AC-001-01"}))
            self.assertFalse(evidence_ok(f.copy_with({"file": "../etc/passwd"}), tmp_path, {"AC-001-01"}))
            self.assertFalse(evidence_ok(f, tmp_path, set()))

    def test_finding_ledger_prevents_quote_drift_auto_verify(self) -> None:
        ledger = FindingLedger()
        f_round1 = mk_finding(Severity.BLOCKER, Dimension.CORRECTNESS, quote="x = 1")
        ledger.absorb([f_round1])
        ledger.mark_fixed([f_round1])

        f_round2 = mk_finding(Severity.BLOCKER, Dimension.CORRECTNESS, quote="x = 2")
        ledger.absorb(
            [f_round2],
            prior_checks=[PriorFindingStatus(finding_id="FND-001", still_present=True, evidence_note="Still broken")],
            l4_passed=True,
        )
        self.assertEqual(len(ledger.open()), 1)
        self.assertEqual(ledger.open()[0].quote, "x = 2")

    def test_loop_converges_after_one_fix(self) -> None:
        kg = SQLiteKnowledgeGraph(":memory:")
        kg.register_test("TST-001", ["AC-001-01"], "tests/acceptance/test_st_001.py")
        kg.record_test_result("TST-001", "sha-1", True)
        kg.record_test_result("TST-001", "sha-2", True)

        task = BuildTask(
            id="BLD-001",
            module_id="MOD-001",
            files_owned=["a.py", "test_a.py"],
            task_ids=["TSK-001"],
            ac_ids=["AC-001-01"],
        )

        class ScriptedPorts:
            def __init__(self) -> None:
                self.sha = "sha-1"

            def head(self, t: BuildTask) -> str:
                return self.sha

            def verify(self, t: BuildTask, commit: str) -> VerificationReport:
                return VerificationReport(
                    build_id=t.id,
                    commit_sha=commit,
                    layers=[LayerResult(layer="unit", tool="pytest", passed=True)],
                )

            def review(self, t: BuildTask, round_no: int, vr: VerificationReport, open_ids: list[str]) -> ReviewReport:
                findings = [mk_finding(Severity.MAJOR, Dimension.CORRECTNESS)] if round_no == 1 else []
                checks = (
                    [PriorFindingStatus(finding_id="FND-001", still_present=False, evidence_note="Fixed in sha-2")]
                    if round_no > 1
                    else []
                )
                return ReviewReport(
                    build_id=t.id,
                    round_no=round_no,
                    commit_sha=self.sha,
                    files_reviewed=t.files_owned,
                    findings=findings,
                    prior_finding_checks=checks,
                )

            def validate(self, report: ReviewReport) -> ReviewReport:
                return report

            def fix(self, t: BuildTask, findings: list[Finding], instruction: str | None, rung: Rung) -> str:
                self.sha = "sha-2"
                return self.sha

            def fix_proof(self, f: Finding, before: str, after: str) -> bool:
                return before != after

            def graph(self) -> SQLiteKnowledgeGraph:
                return kg

        outcome, ledger = review_fix_loop(task, ScriptedPorts(), LoopConfig(max_rounds=4, min_score=4))
        self.assertEqual(outcome, LoopOutcome.CONVERGED)
        self.assertEqual(ledger.open(), [])


if __name__ == "__main__":
    unittest.main()
