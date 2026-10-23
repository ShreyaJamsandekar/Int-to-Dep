"""Simple plain-text resume and LLD approval manager for Antigravity and CLI runs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
from pipeline.contracts.base import utc_now_iso


@dataclass
class RunCheckpoint:
    run_id: str = "run-2026-10-22-001"
    handoff_file: str = "examples/sample_handoff.json"
    workspace_dir: str = "workspace_build"
    current_stage: str = "H0_INTAKE"
    lld_approved: str = "PENDING"  # PENDING | YES | REJECTED
    graph_epoch: int = 0
    completed_stages: list[str] = field(default_factory=list)
    completed_waves: list[int] = field(default_factory=list)
    completed_build_tasks: list[str] = field(default_factory=list)
    pending_build_tasks: list[str] = field(default_factory=list)
    lld_replan_count: int = 0
    task_split_count: int = 0
    last_status: str = "INITIALIZED"
    next_command: str = "python -m pipeline.cli resume --state-dir state"
    updated_at: str = field(default_factory=utc_now_iso)
    notes: str = "Edit 'LLD Approved: YES' in resume.txt (or run approve-lld) to continue past LLD gate."


class ResumeManager:
    """
    Synchronizes pipeline run state to both:
      1. `state/resume.txt` — simple, normal, human-readable text that you can view or edit in Antigravity.
      2. `state/checkpoint.json` — structured backup used alongside `resume.txt`.
    If the user edits `LLD Approved: YES` or `Current Stage:` directly in `resume.txt`,
    `load()` honors those plain-text edits automatically.
    """

    def __init__(self, state_dir: str | Path = "state") -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.txt_path = self.state_dir / "resume.txt"
        self.json_path = self.state_dir / "checkpoint.json"

    def save(self, cp: RunCheckpoint) -> Path:
        cp.updated_at = utc_now_iso()
        self.json_path.write_text(json.dumps(asdict(cp), indent=2), encoding="utf-8")
        lines = [
            "PIPELINE RESUME FILE (SIMPLE PLAIN TEXT)",
            "========================================",
            "You can read or edit this file directly in Antigravity or any text editor.",
            "To approve the LLD and let the pipeline build and deploy the code, change",
            "'LLD Approved: PENDING' to 'LLD Approved: YES' and run the Next Command below.",
            "",
            f"Run ID: {cp.run_id}",
            f"Handoff File: {cp.handoff_file}",
            f"Workspace Directory: {cp.workspace_dir}",
            f"Current Stage: {cp.current_stage}",
            f"LLD Approved: {cp.lld_approved}",
            f"Graph Epoch: {cp.graph_epoch}",
            f"Completed Stages: {', '.join(cp.completed_stages) if cp.completed_stages else 'None'}",
            f"Completed Waves: {', '.join(str(w) for w in cp.completed_waves) if cp.completed_waves else 'None'}",
            f"Completed Build Tasks: {', '.join(cp.completed_build_tasks) if cp.completed_build_tasks else 'None'}",
            f"Pending Build Tasks: {', '.join(cp.pending_build_tasks) if cp.pending_build_tasks else 'None'}",
            f"LLD Replan Loops Run: {cp.lld_replan_count}",
            f"Task Splits Run: {cp.task_split_count}",
            f"Last Status: {cp.last_status}",
            f"Updated At: {cp.updated_at}",
            f"Notes: {cp.notes}",
            "",
            "HOW TO RESUME OR APPROVE:",
            f"Next Command: {cp.next_command}",
            "Approve LLD Command: python -m pipeline.cli approve-lld --state-dir " + str(self.state_dir),
            "Resume Run Command:  python -m pipeline.cli resume --state-dir " + str(self.state_dir),
            "",
        ]
        self.txt_path.write_text("\n".join(lines), encoding="utf-8")
        return self.txt_path

    def load(self) -> RunCheckpoint:
        data: dict[str, Any] = {}
        if self.json_path.is_file():
            data = json.loads(self.json_path.read_text(encoding="utf-8"))
        cp = RunCheckpoint(**data) if data else RunCheckpoint()

        if self.txt_path.is_file():
            for raw_line in self.txt_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if ":" not in line or line.startswith("#") or line.startswith("="):
                    continue
                k, v = [p.strip() for p in line.split(":", 1)]
                if k == "Run ID" and v:
                    cp.run_id = v
                elif k == "Handoff File" and v:
                    cp.handoff_file = v
                elif k == "Workspace Directory" and v:
                    cp.workspace_dir = v
                elif k == "Current Stage" and v:
                    cp.current_stage = v
                elif k == "LLD Approved" and v:
                    cp.lld_approved = v.upper()
                elif k == "Graph Epoch" and v.isdigit():
                    cp.graph_epoch = int(v)
                elif k == "Completed Build Tasks":
                    cp.completed_build_tasks = [] if v in ("None", "") else [x.strip() for x in v.split(",") if x.strip()]
                elif k == "Pending Build Tasks":
                    cp.pending_build_tasks = [] if v in ("None", "") else [x.strip() for x in v.split(",") if x.strip()]
        return cp
