"""Wave-based parallel worktree scheduler with MVCC Knowledge Graph synchronization."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable
from pipeline.contracts.tasks import BuildTask, TaskGraph
from pipeline.review.loop import LoopOutcome, FindingLedger
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


@dataclass
class TaskExecutionSummary:
    task_id: str
    module_id: str
    wave_index: int
    base_epoch: int
    merged_epoch: int
    reverified_after_neighbor_delta: bool
    outcome: LoopOutcome
    ledger: FindingLedger


class WaveScheduler:
    """
    Executes BuildTasks in dependency-first topological waves.
    Within each wave, up to `max_workers` tasks execute in parallel against a pinned
    MVCC `base_epoch`. Merges happen serially under lock, bumping `graph_epoch` and
    triggering a pre-merge neighbor delta check if a sibling modified a 1-hop neighbor.
    """

    def __init__(self, kg: SQLiteKnowledgeGraph, max_workers: int = 4) -> None:
        self.kg = kg
        self.max_workers = max_workers

    def run_waves(
        self,
        task_graph: TaskGraph,
        completed_task_ids: set[str],
        worker_fn: Callable[[BuildTask, int], tuple[LoopOutcome, FindingLedger]],
        on_task_merged: Callable[[BuildTask, TaskExecutionSummary], None] | None = None,
    ) -> list[TaskExecutionSummary]:
        task_map = {t.id: t for t in task_graph.tasks}
        waves = task_graph.execution_waves()
        results: list[TaskExecutionSummary] = []

        for wave_idx, wave_task_ids in enumerate(waves):
            pending_in_wave = [tid for tid in wave_task_ids if tid not in completed_task_ids]
            if not pending_in_wave:
                continue

            wave_base_epoch = self.kg.epoch
            raw_outcomes: dict[str, tuple[LoopOutcome, FindingLedger, int]] = {}

            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(pending_in_wave))) as pool:
                future_to_tid = {
                    pool.submit(worker_fn, task_map[tid], wave_base_epoch): tid
                    for tid in pending_in_wave
                }
                for fut in as_completed(future_to_tid):
                    tid = future_to_tid[fut]
                    outcome, ledger = fut.result()
                    raw_outcomes[tid] = (outcome, ledger, wave_base_epoch)

            # Serial deterministic merge order within wave
            for tid in sorted(pending_in_wave):
                task = task_map[tid]
                outcome, ledger, base_ep = raw_outcomes[tid]
                reverified = False

                if outcome is LoopOutcome.CONVERGED:
                    if self.kg.epoch > base_ep and self.kg.has_neighbor_delta_since_epoch(task.module_id, base_ep):
                        reverified = True
                        outcome, ledger = worker_fn(task, self.kg.epoch)

                    if outcome is LoopOutcome.CONVERGED:
                        self.kg.clear_stale(task.module_id)
                        self.kg.clear_stale(task.id)
                        merged_ep = self.kg.bump_epoch()
                        summary = TaskExecutionSummary(
                            task_id=task.id,
                            module_id=task.module_id,
                            wave_index=wave_idx,
                            base_epoch=base_ep,
                            merged_epoch=merged_ep,
                            reverified_after_neighbor_delta=reverified,
                            outcome=outcome,
                            ledger=ledger,
                        )
                        results.append(summary)
                        if on_task_merged:
                            on_task_merged(task, summary)
                        continue

                # Non-converged outcome (SPLIT, REPLAN_LLD, REJECT_HANDOFF, FAILED)
                summary = TaskExecutionSummary(
                    task_id=task.id,
                    module_id=task.module_id,
                    wave_index=wave_idx,
                    base_epoch=base_ep,
                    merged_epoch=self.kg.epoch,
                    reverified_after_neighbor_delta=reverified,
                    outcome=outcome,
                    ledger=ledger,
                )
                results.append(summary)
                return results

        return results
