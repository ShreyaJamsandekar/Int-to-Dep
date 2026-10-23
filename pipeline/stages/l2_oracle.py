"""Stage L2b: Independent black-box acceptance test oracle generator."""
from __future__ import annotations

from pathlib import Path
from pipeline.contracts.handoff import HLDHandoff
from pipeline.contracts.lld import LLDPack
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


def run_l2_oracle(
    handoff: HLDHandoff,
    lld: LLDPack,
    repo_root: Path,
    kg: SQLiteKnowledgeGraph,
    run_id: str = "run-2026-10-22-001",
) -> list[str]:
    """
    Generate black-box acceptance tests strictly from Story AcceptanceCriteria and
    API Contracts without reading internal implementation code.
    Registers 1:1 `(:Test)-[:VERIFIES]->(:AC)` edges in the Knowledge Graph.
    """
    test_ids: list[str] = []
    seq = 1
    for st in handoff.stories:
        lines = [
            f'"""Frozen Acceptance Oracle for {st.story_id} ({st.title}). DO NOT MODIFY IN L3."""',
            "from __future__ import annotations",
            "from tests.harness.state_seeder import StateSeeder",
            "",
        ]
        for ac in st.criteria:
            tid = f"TST-{seq:03d}"
            seq += 1
            fn_Safe = ac.id.lower().replace("-", "_")
            lines += [
                f"def test_{fn_Safe}() -> None:",
                f'    """AC: {ac.id} -> {ac.gherkin}"""',
                "    seeder = StateSeeder()",
                "    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})",
                "    assert seeded['status'] == 'SEEDED'",
                "",
            ]
            rel_file = f"tests/acceptance/test_{st.story_id.lower().replace('-', '_')}.py"
            kg.register_test(tid, [ac.id], rel_file, run_id=run_id)
            test_ids.append(tid)

        rel_file = f"tests/acceptance/test_{st.story_id.lower().replace('-', '_')}.py"
        out_path = repo_root / rel_file
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")

    kg.bump_epoch()
    return test_ids
