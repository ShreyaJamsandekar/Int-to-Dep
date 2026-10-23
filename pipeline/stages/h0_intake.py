"""Stage H0: HLD Handoff intake, validation, and Knowledge Graph initialization."""
from __future__ import annotations

import json
from pathlib import Path
from pipeline.contracts.base import utc_now_iso, sha256_obj
from pipeline.contracts.envelope import StageResult
from pipeline.contracts.handoff import HLDHandoff
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


def run_h0_intake(
    handoff_source: str | Path | dict,
    kg: SQLiteKnowledgeGraph,
    run_id: str = "run-2026-10-22-001",
) -> StageResult[HLDHandoff]:
    started = utc_now_iso()
    if isinstance(handoff_source, (str, Path)):
        raw = json.loads(Path(handoff_source).read_text(encoding="utf-8"))
    else:
        raw = handoff_source

    handoff = HLDHandoff.parse_obj_compat(raw)
    major_ver = int(handoff.handoff_version.split(".")[0])
    if major_ver != 1:
        raise ValueError(f"Unsupported handoff major version: {handoff.handoff_version}")

    ep = kg.load_handoff(handoff, run_id=run_id)
    finished = utc_now_iso()
    return StageResult[HLDHandoff](
        stage="H0_INTAKE",
        run_id=run_id,
        graph_epoch=ep,
        input_hash=sha256_obj(raw),
        model_id="none",
        payload=handoff,
        validators_passed=[
            "pydantic_strict_schema",
            "major_version_check",
            "referential_integrity",
            "runtime_dependency_acyclicity",
            "kg_epoch_loaded",
        ],
        started_at=started,
        finished_at=finished,
    )
