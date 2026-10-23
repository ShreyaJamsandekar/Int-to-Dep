HLD-TO-DEPLOYABLE-CODE PIPELINE (SIMPLE PLAIN TEXT GUIDE)
=========================================================

WHAT THIS PROJECT DOES
----------------------
This pipeline takes a High-Level Design handoff file (examples/sample_handoff.json)
and turns it into deployable enterprise Python/FastAPI code through 7 stages:

  1. H0 Intake: Validates the HLD handoff and loads the Knowledge Graph.
  2. L1 LLD: Generates the Low-Level Design (modules, functions, data models, SQL tables,
     and API contracts) and checks that there are zero violations.
  3. LLD Approval Gate: Pauses and writes a simple text file (state/resume.txt) so you
     can review and approve the LLD before code generation starts.
  4. L2 Scaffold & Oracle: Builds the project skeleton, auto-discovery routers, and
     black-box acceptance tests.
  5. L3 + L4 + L5 Build-Verify-Review Loop: Builds modules in dependency waves (serial
     and parallel), runs deterministic checks, runs the AI code review loop, and updates
     the Knowledge Graph and LLD if a task needs splitting or replanning.
  6. L6 Conformance: Verifies that every story, task, and acceptance criterion is tested
     and implemented in the Knowledge Graph.
  7. L7 Deploy: Verifies database migrations, runs smoke checks, and writes the final
     Release Bundle in workspace_build/release_bundle/release-bundle.json.


WHAT YOU NEED TO RUN IT
-----------------------
- Python 3.11 or 3.12
- pydantic (v2) and pytest installed:
    pip install pydantic pytest


HOW TO USE THIS IN ANTIGRAVITY (STEP BY STEP)
---------------------------------------------
Step 1: Unzip `hld_to_deployable_code_pipeline.zip` and open the folder in Antigravity.

Step 2: Run the test suite first to see that everything works out of the box:
    pytest -v

Step 3: Start a pipeline run (this will run H0 and L1, generate the LLD, and pause for
        your LLD approval):
    python -m pipeline.cli run --handoff examples/sample_handoff.json

Step 4: Open `state/resume.txt` in Antigravity. It is written in simple, normal text!
        You will see:
            Current Stage: WAITING_FOR_LLD_APPROVAL
            LLD Approved: PENDING

Step 5: Approve the LLD in either of two easy ways:
        Option A (Edit the text file):
            In `state/resume.txt`, change `LLD Approved: PENDING` to `LLD Approved: YES`
            and save the file.
        Option B (Run the command):
            python -m pipeline.cli approve-lld --state-dir state

Step 6: Resume the pipeline so it builds, verifies, reviews, and deploys the code:
    python -m pipeline.cli resume --state-dir state

Step 7: Or, if you want to run the entire pipeline from start to finish in one command
        without pausing at LLD approval:
    python -m pipeline.cli run --handoff examples/sample_handoff.json --auto-approve-lld


HOW THE SIMPLE TEXT RESUME FILE (`state/resume.txt`) WORKS
----------------------------------------------------------
Whenever the pipeline runs, pauses, merges a build task, or splits/replans an LLD module,
it updates `state/resume.txt` in plain English. Here is what each line means:

- Run ID: Unique name for the current pipeline run.
- Handoff File: Path to the input HLD JSON file (default: examples/sample_handoff.json).
- Workspace Directory: Folder where the deployable code and release bundle are written
  (default: workspace_build).
- Current Stage: Where the pipeline is right now (for example: WAITING_FOR_LLD_APPROVAL
  or G2_RELEASE_READY).
- LLD Approved: PENDING or YES. Change this to YES in the text file to approve the LLD.
- Graph Epoch: Version number of the Knowledge Graph (increases every time serial or
  parallel tasks update the graph).
- Completed Stages: List of stages finished so far.
- Completed Build Tasks: List of build tasks (BLD-001, BLD-002, etc.) already merged.
- Pending Build Tasks: List of build tasks waiting to be built.
- Next Command: Exact terminal command you can copy and paste to continue.
