"""Command-line interface for running, approving LLD, and resuming the pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from pipeline.orchestration.runner import PipelineRunner
from pipeline.orchestration.resume import ResumeManager


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pipeline.cli",
        description="Vision-PR / HLD-to-Deployable-Code Pipeline CLI (Antigravity Ready)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Start pipeline from H0 Handoff")
    p_run.add_argument("--handoff", default="examples/sample_handoff.json", help="Path to HLDHandoff JSON")
    p_run.add_argument("--state-dir", default="state", help="Directory for resume.txt and KG state")
    p_run.add_argument("--workspace-dir", default="workspace_build", help="Output directory for generated code")
    p_run.add_argument("--auto-approve-lld", action="store_true", help="Approve LLD automatically without pausing")

    p_approve = sub.add_parser("approve-lld", help="Mark LLD Approved: YES in state/resume.txt")
    p_approve.add_argument("--state-dir", default="state", help="Directory containing resume.txt")

    p_resume = sub.add_parser("resume", help="Resume pipeline from state/resume.txt")
    p_resume.add_argument("--state-dir", default="state", help="Directory containing resume.txt")

    p_status = sub.add_parser("status", help="Print plain-text state/resume.txt")
    p_status.add_argument("--state-dir", default="state", help="Directory containing resume.txt")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        runner = PipelineRunner(state_dir=args.state_dir, workspace_dir=args.workspace_dir)
        outcome = runner.run(
            handoff_file=args.handoff,
            auto_approve_lld=args.auto_approve_lld,
            fresh=True,
        )
        print(f"Pipeline Status: {outcome.status}")
        print(f"Resume File:     {Path(args.state_dir) / 'resume.txt'}")
        if outcome.release_bundle:
            print(f"Sandbox URL:     {outcome.release_bundle.sandbox_url}")
            print(f"Release Bundle:  {Path(args.workspace_dir) / 'release_bundle/release-bundle.json'}")
        return 0

    if args.cmd == "approve-lld":
        mgr = ResumeManager(args.state_dir)
        cp = mgr.load()
        cp.lld_approved = "YES"
        cp.current_stage = "LLD_APPROVED_READY_FOR_L2"
        cp.last_status = "LLD_APPROVED_BY_USER"
        cp.next_command = f"python -m pipeline.cli resume --state-dir {args.state_dir}"
        cp.notes = "LLD approved! Run the Next Command to build, verify, and deploy."
        mgr.save(cp)
        print(f"Updated {mgr.txt_path}: LLD Approved = YES")
        return 0

    if args.cmd == "resume":
        mgr = ResumeManager(args.state_dir)
        cp = mgr.load()
        runner = PipelineRunner(state_dir=args.state_dir, workspace_dir=cp.workspace_dir)
        outcome = runner.run(
            handoff_file=cp.handoff_file,
            auto_approve_lld=(cp.lld_approved == "YES"),
            run_id=cp.run_id,
        )
        print(f"Pipeline Resume Status: {outcome.status}")
        if outcome.release_bundle:
            print(f"Sandbox URL:            {outcome.release_bundle.sandbox_url}")
            print(f"Release Bundle:         {Path(cp.workspace_dir) / 'release_bundle/release-bundle.json'}")
        return 0

    if args.cmd == "status":
        mgr = ResumeManager(args.state_dir)
        if mgr.txt_path.is_file():
            print(mgr.txt_path.read_text(encoding="utf-8"))
        else:
            print(f"No resume.txt found in {args.state_dir}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
