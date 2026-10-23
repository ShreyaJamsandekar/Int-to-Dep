"""Unit tests for Handoff, LLD, TaskGraph validators, topological waves, and MVCC Knowledge Graph."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from pipeline.contracts.graphutil import assert_acyclic, topological_waves
from pipeline.contracts.handoff import HLDHandoff
from pipeline.contracts.lld import lld_violations
from pipeline.contracts.tasks import BuildTask, TaskGraph
from pipeline.orchestration.context import split_module_into_submodules
from pipeline.stages.h0_intake import run_h0_intake
from pipeline.stages.l1_lld import run_l1_lld
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


def load_sample_dict() -> dict:
    p = Path(__file__).resolve().parent.parent / "examples/sample_handoff.json"
    return json.loads(p.read_text(encoding="utf-8"))


class TestContractsAndGraph(unittest.TestCase):
    def test_assert_acyclic_and_topological_waves(self) -> None:
        waves = topological_waves({"BLD-001", "BLD-002"}, [("BLD-002", "BLD-001")])
        self.assertEqual(waves, [["BLD-001"], ["BLD-002"]])

        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            assert_acyclic([("MOD-001", "MOD-002"), ("MOD-002", "MOD-001")])

    def test_handoff_negative_rules(self) -> None:
        raw = load_sample_dict()
        HLDHandoff.parse_obj_compat(raw)

        bad_reason = dict(raw, architecture_selection_reasoning="We just liked this architecture style.")
        with self.assertRaisesRegex(ValueError, "must cite at least one NFR or story id"):
            HLDHandoff.parse_obj_compat(bad_reason)

        bad_cycle = dict(
            raw,
            dependencies=[
                {"source": "SVC-001", "target_component": "SVC-002", "kind": "runtime"},
                {"source": "SVC-002", "target_component": "SVC-001", "kind": "runtime"},
            ],
        )
        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            HLDHandoff.parse_obj_compat(bad_cycle)

    def test_task_graph_disjoint_file_ownership(self) -> None:
        t1 = BuildTask(
            id="BLD-001",
            module_id="MOD-001",
            files_owned=["services/a.py", "tests/unit/test_a.py"],
            task_ids=["TSK-001"],
            ac_ids=["AC-001-01"],
        )
        t2_conflict = BuildTask(
            id="BLD-002",
            module_id="MOD-002",
            files_owned=["services/a.py", "tests/unit/test_b.py"],
            task_ids=["TSK-001"],
            ac_ids=["AC-001-01"],
        )
        with self.assertRaisesRegex(ValueError, "owned by BLD-001 and BLD-002"):
            TaskGraph(tasks=[t1, t2_conflict])

    def test_kg_mvcc_epochs_and_surgical_lld_replan(self) -> None:
        kg = SQLiteKnowledgeGraph(":memory:")
        h0 = run_h0_intake(load_sample_dict(), kg, run_id="test-run")
        self.assertEqual(kg.epoch, 1)

        l1 = run_l1_lld(h0.payload, kg, run_id="test-run")
        self.assertEqual(kg.epoch, 2)
        self.assertEqual(lld_violations(l1.payload, h0.payload), [])

        patch = split_module_into_submodules(l1.payload, "MOD-001", ticket_id="TKT-001")
        updated_lld, stale_nodes = kg.apply_lld_replan(l1.payload, patch, run_id="test-run")
        self.assertEqual(updated_lld.lld_version, "1.0.1")
        self.assertEqual(lld_violations(updated_lld, h0.payload), [])
        self.assertIn("MOD-002", stale_nodes)


if __name__ == "__main__":
    unittest.main()
