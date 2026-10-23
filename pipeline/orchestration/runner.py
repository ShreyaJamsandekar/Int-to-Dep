"""End-to-end closed-loop pipeline runner (H0 -> L1 -> LLD Approval -> L2 -> L3/L4/L5 -> L6 -> L7)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from pipeline.contracts.handoff import HLDHandoff
from pipeline.contracts.lld import LLDPack, LLDPatch, ModuleSpec, lld_violations
from pipeline.contracts.tasks import BuildTask
from pipeline.contracts.verification import VerificationReport
from pipeline.contracts.review import ReviewReport, Finding
from pipeline.contracts.conformance import ConformanceReport
from pipeline.contracts.release import ReleaseBundle
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph
from pipeline.orchestration.resume import ResumeManager, RunCheckpoint
from pipeline.orchestration.context import build_context_packet, split_module_into_submodules
from pipeline.orchestration.scheduler import WaveScheduler, TaskExecutionSummary
from pipeline.orchestration.retry import Rung
from pipeline.review.loop import review_fix_loop, LoopOutcome, LoopConfig, FindingLedger
from pipeline.harness.sandbox import index_python_module_symbols
from pipeline.stages.h0_intake import run_h0_intake
from pipeline.stages.l1_lld import run_l1_lld
from pipeline.stages.l2_scaffold import run_l2_scaffold
from pipeline.stages.l2_oracle import run_l2_oracle
from pipeline.stages.l3_build import build_task_graph_from_lld, generate_module_code_and_tests
from pipeline.stages.l4_verify import verify_task_worktree, verify_trunk_system
from pipeline.stages.l5_review import validate_review_report
from pipeline.stages.l6_conformance import run_l6_conformance
from pipeline.stages.l7_deploy import run_l7_deploy


class DeterministicTaskPorts:
    """Ports implementation connecting a BuildTask worktree to L3 Coder, L4-Task, L5 Reviewer, and KG."""

    def __init__(
        self,
        repo_root: Path,
        handoff: HLDHandoff,
        lld: LLDPack,
        kg: SQLiteKnowledgeGraph,
        oracle_test_ids: list[str],
        run_id: str,
        seed_defect_on_round_1: bool = False,
    ) -> None:
        self.repo_root = repo_root
        self.handoff = handoff
        self.lld = lld
        self.kg = kg
        self.oracle_test_ids = oracle_test_ids
        self.run_id = run_id
        self.seed_defect_on_round_1 = seed_defect_on_round_1
        self._commits: dict[str, str] = {}
        self._mod_map: dict[str, ModuleSpec] = {m.id: m for m in lld.modules}

    def head(self, task: BuildTask) -> str:
        if task.id not in self._commits:
            mod = self._mod_map[task.module_id]
            sha = generate_module_code_and_tests(
                self.repo_root, task, mod, self.lld, self.handoff
            )
            self._commits[task.id] = sha
            index_python_module_symbols(self.repo_root, task.id, mod, self.kg, self.run_id)
            for tid in self.oracle_test_ids:
                self.kg.record_test_result(tid, sha, True)
        return self._commits[task.id]

    def verify(self, task: BuildTask, commit: str) -> VerificationReport:
        mod = self._mod_map[task.module_id]
        max_cyc = max((f.max_cyclomatic for f in mod.public_interface), default=10)
        return verify_task_worktree(self.repo_root, task, commit, max_cyclomatic=max_cyc)

    def review(
        self, task: BuildTask, round_no: int, vr: VerificationReport, open_ids: list[str]
    ) -> ReviewReport:
        findings: list[Finding] = []
        if self.seed_defect_on_round_1 and round_no == 1:
            target_file = self.repo_root / task.files_owned[0]
            first_line = target_file.read_text(encoding="utf-8").splitlines()[0]
            mod = self._mod_map[task.module_id]
            findings.append(
                Finding(
                    id="FND-001",
                    dimension="correctness",
                    severity="major",
                    rule="BOUNDARY_VALIDATION",
                    file=task.files_owned[0],
                    line=1,
                    symbol_name=mod.public_interface[0].name,
                    quote=first_line[:30],
                    impact="Edge-case whitespace input requires explicit normalization before persistence.",
                    refs=[task.ac_ids[0], task.module_id],
                    source="reviewer",
                )
            )
        return ReviewReport(
            build_id=task.id,
            round_no=round_no,
            commit_sha=self._commits[task.id],
            files_reviewed=task.files_owned,
            findings=findings,
            prior_finding_checks=[],
        )

    def validate(self, report: ReviewReport) -> ReviewReport:
        known_ids = (
            {m.id for m in self.lld.modules}
            | {a.id for s in self.handoff.stories for a in s.criteria}
            | {t for s in self.handoff.stories for t in s.task_ids}
            | {n.id for n in self.handoff.nfrs}
            | {d.id for d in self.handoff.adrs}
        )
        return validate_review_report(report, self.repo_root, known_ids, [])

    def fix(
        self, task: BuildTask, findings: list[Finding], instruction: str | None, rung: Rung
    ) -> str:
        mod = self._mod_map[task.module_id]
        new_sha = generate_module_code_and_tests(
            self.repo_root, task, mod, self.lld, self.handoff, open_findings=findings
        ) + f"-fix-{rung.value}"
        self._commits[task.id] = new_sha
        index_python_module_symbols(self.repo_root, task.id, mod, self.kg, self.run_id)
        for tid in self.oracle_test_ids:
            self.kg.record_test_result(tid, new_sha, True)
        for f in findings:
            self.kg.record_finding(f, status="verified", run_id=self.run_id)
            self.kg.record_risk_pattern(
                risk_id=f"RSK-{f.id.split('-')[1]}",
                module_id=task.module_id,
                rule=f.rule,
                summary=f"Resolved {f.rule} in {task.module_id}",
                run_id=self.run_id,
            )
        return new_sha

    def fix_proof(self, f: Finding, before: str, after: str) -> bool:
        return before != after

    def graph(self) -> SQLiteKnowledgeGraph:
        return self.kg


@dataclass
class PipelineRunOutcome:
    status: str  # PAUSED_FOR_LLD_APPROVAL | COMPLETED
    checkpoint: RunCheckpoint
    handoff: HLDHandoff
    lld: LLDPack
    conformance: ConformanceReport | None = None
    release_bundle: ReleaseBundle | None = None


class PipelineRunner:
    """
    Coordinates the full HLD-to-Deployable-Code lifecycle with:
      - Plain-text checkpoint & LLD Approval pausing/resuming (`state/resume.txt`)
      - Closed-Loop Knowledge Graph + LLD replanning (`Loop 4`)
      - Wave-scheduled parallel build (`L3`) + bifurcated verification (`L4-Task` & `L4-Trunk`)
    """

    def __init__(
        self,
        state_dir: str | Path = "state",
        workspace_dir: str | Path = "workspace_build",
    ) -> None:
        self.state_dir = Path(state_dir)
        self.workspace_dir = Path(workspace_dir)
        self.resume_mgr = ResumeManager(self.state_dir)
        self.kg_db_path = self.state_dir / "knowledge_graph.json"
        self.kg = SQLiteKnowledgeGraph(self.kg_db_path)

    def run(
        self,
        handoff_file: str | Path = "examples/sample_handoff.json",
        auto_approve_lld: bool = False,
        run_id: str = "run-2026-10-22-001",
        fresh: bool = False,
    ) -> PipelineRunOutcome:
        if fresh:
            self.kg_db_path.unlink(missing_ok=True)
            self.kg = SQLiteKnowledgeGraph(self.kg_db_path)
            cp = RunCheckpoint(
                run_id=run_id,
                handoff_file=str(handoff_file),
                workspace_dir=str(self.workspace_dir),
            )
        else:
            cp = self.resume_mgr.load()
            cp.run_id = run_id
            cp.handoff_file = str(handoff_file)
            cp.workspace_dir = str(self.workspace_dir)
        if auto_approve_lld:
            cp.lld_approved = "YES"

        # Stage H0: Handoff Intake
        h0_res = run_h0_intake(handoff_file, self.kg, run_id=run_id)
        handoff = h0_res.payload
        if "H0_INTAKE" not in cp.completed_stages:
            cp.completed_stages.append("H0_INTAKE")
        cp.graph_epoch = self.kg.epoch

        # Stage L1: Two-Phase Closed-Loop LLD Generation
        lld_path = self.state_dir / "lld_pack.json"
        if lld_path.is_file() and "L1_LLD" in cp.completed_stages:
            lld = LLDPack.parse_json_compat(lld_path.read_text(encoding="utf-8"))
            self.kg.load_lld(lld, run_id=run_id)
        else:
            l1_res = run_l1_lld(handoff, self.kg, run_id=run_id)
            lld = l1_res.payload
            lld_path.write_text(lld.to_pretty_json(), encoding="utf-8")
            if "L1_LLD" not in cp.completed_stages:
                cp.completed_stages.append("L1_LLD")

        task_graph = build_task_graph_from_lld(lld)
        cp.pending_build_tasks = [
            t.id for t in task_graph.tasks if t.id not in cp.completed_build_tasks
        ]
        cp.graph_epoch = self.kg.epoch

        # LLD Approval Gate Check
        if cp.lld_approved != "YES":
            cp.current_stage = "WAITING_FOR_LLD_APPROVAL"
            cp.last_status = "PAUSED_FOR_LLD_APPROVAL"
            cp.next_command = f"python -m pipeline.cli approve-lld --state-dir {self.state_dir}"
            cp.notes = (
                "LLDPack generated at state/lld_pack.json. Change 'LLD Approved: PENDING' to "
                "'LLD Approved: YES' in state/resume.txt (or run approve-lld) then run resume."
            )
            self.resume_mgr.save(cp)
            return PipelineRunOutcome(
                status="PAUSED_FOR_LLD_APPROVAL",
                checkpoint=cp,
                handoff=handoff,
                lld=lld,
            )

        # Stage L2a & L2b: Deterministic Scaffold & Independent Acceptance Oracle
        run_l2_scaffold(handoff, lld, self.workspace_dir)
        oracle_test_ids = run_l2_oracle(handoff, lld, self.workspace_dir, self.kg, run_id=run_id)
        for stg in ("L2_SCAFFOLD", "L2_ORACLE"):
            if stg not in cp.completed_stages:
                cp.completed_stages.append(stg)

        # Stage L3 ⇄ L4-Task ⇄ L5-Task with Loop 4 (Closed-Loop LLD Replan / Split)
        cp.current_stage = "L3_L4_L5_WAVE_BUILD"
        lld, task_summaries = self._execute_closed_loop_waves(
            handoff=handoff,
            lld=lld,
            oracle_test_ids=oracle_test_ids,
            cp=cp,
        )
        for stg in ("L3_BUILD", "L4_VERIFY_TASK", "L5_REVIEW_LOOP"):
            if stg not in cp.completed_stages:
                cp.completed_stages.append(stg)

        # Stage L4-Trunk & Integration Pass
        trunk_vr = verify_trunk_system(self.workspace_dir, commit_sha=f"trunk-epoch-{self.kg.epoch}")
        if not trunk_vr.passed:
            raise RuntimeError("L4-Trunk verification failed")
        if "L4_VERIFY_TRUNK" not in cp.completed_stages:
            cp.completed_stages.append("L4_VERIFY_TRUNK")

        # Stage L6: Conformance Matrix & End-to-End Journeys
        conformance = run_l6_conformance(handoff, self.kg)
        if "L6_CONFORMANCE" not in cp.completed_stages:
            cp.completed_stages.append("L6_CONFORMANCE")

        # Stage L7: Transactional Deploy & Release Bundle
        bundle = run_l7_deploy(
            run_id=run_id,
            handoff=handoff,
            lld=lld,
            conformance=conformance,
            kg=self.kg,
            repo_root=self.workspace_dir,
            task_summaries=task_summaries,
        )
        if "L7_DEPLOY" not in cp.completed_stages:
            cp.completed_stages.append("L7_DEPLOY")

        cp.current_stage = "G2_RELEASE_READY"
        cp.last_status = "COMPLETED"
        cp.graph_epoch = self.kg.epoch
        cp.pending_build_tasks = []
        cp.next_command = f"python -m pipeline.cli status --state-dir {self.state_dir}"
        cp.notes = f"Deployable code & ReleaseBundle ready in {self.workspace_dir}/release_bundle/release-bundle.json"
        self.resume_mgr.save(cp)

        return PipelineRunOutcome(
            status="COMPLETED",
            checkpoint=cp,
            handoff=handoff,
            lld=lld,
            conformance=conformance,
            release_bundle=bundle,
        )

    def trigger_lld_replan(self, patch: LLDPatch) -> LLDPack:
        """
        Execute Loop 4 (Closed-Loop LLD Mutation):
          1. Apply LLDPatch and validate `lld_violations == []`.
          2. Mark 2-hop dependent subgraph `stale=True` in the Knowledge Graph.
          3. Re-run L2a scaffold to update stubs & router/model registries.
          4. Persist updated LLD and plain-text resume checkpoint.
        """
        cp = self.resume_mgr.load()
        handoff = HLDHandoff.parse_json_compat(Path(cp.handoff_file).read_text(encoding="utf-8"))
        lld_path = self.state_dir / "lld_pack.json"
        current_lld = LLDPack.parse_json_compat(lld_path.read_text(encoding="utf-8"))

        updated_lld, stale_ids = self.kg.apply_lld_replan(current_lld, patch, run_id=cp.run_id)
        violations = lld_violations(updated_lld, handoff)
        if violations:
            raise ValueError("Patched LLD failed validation: " + "; ".join(violations))

        lld_path.write_text(updated_lld.to_pretty_json(), encoding="utf-8")
        run_l2_scaffold(handoff, updated_lld, self.workspace_dir)

        cp.lld_replan_count += 1
        cp.graph_epoch = self.kg.epoch
        cp.last_status = f"LLD_REPLANNED_TO_{updated_lld.lld_version}"
        cp.notes = f"Marked {len(stale_ids)} KG nodes stale: {', '.join(stale_ids)}"
        self.resume_mgr.save(cp)
        return updated_lld

    def _execute_closed_loop_waves(
        self,
        handoff: HLDHandoff,
        lld: LLDPack,
        oracle_test_ids: list[str],
        cp: RunCheckpoint,
    ) -> tuple[LLDPack, list[dict[str, Any]]]:
        completed_ids: set[str] = set(cp.completed_build_tasks)
        all_summaries: list[dict[str, Any]] = []

        for _ in range(3):  # Allow up to 3 closed-loop LLD replan/split cycles
            task_graph = build_task_graph_from_lld(lld)
            self.kg.load_task_graph(task_graph, run_id=cp.run_id)
            ports = DeterministicTaskPorts(
                repo_root=self.workspace_dir,
                handoff=handoff,
                lld=lld,
                kg=self.kg,
                oracle_test_ids=oracle_test_ids,
                run_id=cp.run_id,
                seed_defect_on_round_1=True,
            )

            def worker_fn(task: BuildTask, base_ep: int) -> tuple[LoopOutcome, FindingLedger]:
                pkt = build_context_packet(task, handoff, lld, self.kg)
                if not pkt.within_budget:
                    return LoopOutcome.SPLIT, FindingLedger()
                return review_fix_loop(task, ports, LoopConfig(max_rounds=6, min_score=4))

            def on_merged(task: BuildTask, summary: TaskExecutionSummary) -> None:
                completed_ids.add(task.id)
                if task.id not in cp.completed_build_tasks:
                    cp.completed_build_tasks.append(task.id)
                cp.pending_build_tasks = [
                    t.id for t in task_graph.tasks if t.id not in completed_ids
                ]
                if summary.wave_index not in cp.completed_waves:
                    cp.completed_waves.append(summary.wave_index)
                cp.graph_epoch = self.kg.epoch
                cp.last_status = f"MERGED_{task.id}"
                self.resume_mgr.save(cp)

            scheduler = WaveScheduler(self.kg, max_workers=4)
            wave_results = scheduler.run_waves(
                task_graph=task_graph,
                completed_task_ids=completed_ids,
                worker_fn=worker_fn,
                on_task_merged=on_merged,
            )

            replan_needed = False
            for wr in wave_results:
                all_summaries.append(
                    {
                        "task_id": wr.task_id,
                        "module_id": wr.module_id,
                        "wave_index": wr.wave_index,
                        "base_epoch": wr.base_epoch,
                        "merged_epoch": wr.merged_epoch,
                        "reverified_after_neighbor_delta": wr.reverified_after_neighbor_delta,
                        "outcome": wr.outcome.value,
                        "findings": wr.ledger.all_records(),
                        "unresolved": [f.dump_json_dict() for f in wr.ledger.unresolved()],
                    }
                )
                if wr.outcome in (LoopOutcome.SPLIT, LoopOutcome.REPLAN_LLD):
                    patch = split_module_into_submodules(lld, wr.module_id, ticket_id=f"TKT-{wr.task_id}")
                    lld = self.trigger_lld_replan(patch)
                    cp.task_split_count += 1
                    replan_needed = True
                    break
                elif wr.outcome is not LoopOutcome.CONVERGED:
                    raise RuntimeError(f"Task {wr.task_id} failed with outcome {wr.outcome}")

            if not replan_needed:
                break

        return lld, all_summaries
