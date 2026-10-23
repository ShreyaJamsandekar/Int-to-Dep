"""End-to-end test of the pipeline: H0 -> L1 -> Plain-Text Resume Pause/Approve -> L2..L7 Deploy."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from pipeline.cli import main as cli_main
from pipeline.orchestration.resume import ResumeManager


class TestEndToEndPipeline(unittest.TestCase):
    def test_end_to_end_pause_approve_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            handoff_path = Path(__file__).resolve().parent.parent / "examples/sample_handoff.json"
            state_dir = tmp_path / "state"
            workspace_dir = tmp_path / "workspace_build"

            # 1. Run without --auto-approve-lld: pauses at WAITING_FOR_LLD_APPROVAL & writes resume.txt
            rc1 = cli_main(
                [
                    "run",
                    "--handoff",
                    str(handoff_path),
                    "--state-dir",
                    str(state_dir),
                    "--workspace-dir",
                    str(workspace_dir),
                ]
            )
            self.assertEqual(rc1, 0)
            resume_txt = (state_dir / "resume.txt").read_text(encoding="utf-8")
            self.assertIn("Current Stage: WAITING_FOR_LLD_APPROVAL", resume_txt)
            self.assertIn("LLD Approved: PENDING", resume_txt)

            # 2. Simulate user editing `LLD Approved: PENDING` -> `LLD Approved: YES` in resume.txt
            edited_txt = resume_txt.replace("LLD Approved: PENDING", "LLD Approved: YES")
            (state_dir / "resume.txt").write_text(edited_txt, encoding="utf-8")

            mgr = ResumeManager(state_dir)
            loaded_cp = mgr.load()
            self.assertEqual(loaded_cp.lld_approved, "YES")

            # 3. Resume the pipeline from state/resume.txt -> runs L2..L7 to completion
            rc2 = cli_main(["resume", "--state-dir", str(state_dir)])
            self.assertEqual(rc2, 0)

            final_txt = (state_dir / "resume.txt").read_text(encoding="utf-8")
            self.assertIn("Current Stage: G2_RELEASE_READY", final_txt)
            self.assertIn("Last Status: COMPLETED", final_txt)
            self.assertIn("Completed Waves: 0, 1", final_txt)
            self.assertIn("Completed Build Tasks: BLD-001, BLD-003, BLD-002, BLD-004", final_txt)
            self.assertTrue((workspace_dir / "release_bundle/release-bundle.json").is_file())
            self.assertTrue((workspace_dir / "app/main.py").is_file())


if __name__ == "__main__":
    unittest.main()
