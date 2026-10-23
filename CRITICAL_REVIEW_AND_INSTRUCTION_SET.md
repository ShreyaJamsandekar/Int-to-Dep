# Critical Review & Master Instruction Set: Vision-PR / HLD-to-Deployable-Code Pipeline (v0.3)

**Document Type:** Critical Architecture Review, Gap Remediation & Complete Execution Instruction Set  
**Base Specification Reviewed:** `HLD-to-Deployable-Code Pipeline: Unified Specification (Draft v0.2 · 22 Oct 2026)`  
**Scope:** End-to-end deterministic loop from Vision PR & HLD Handoff (`H0`) → Closed-Loop LLD & Knowledge Graph (`L1`) → Scaffold & Independent Oracle (`L2`) → Serial/Parallel Orchestrated Build (`L3`) → Tiered Verification (`L4`) → Evidence-Gated Review-Fix Loop (`L5`) → Conformance & Enterprise Sandbox Deployment (`L6–L7`)

## Part 1: Critical Review of Draft v0.2 — Identified Gaps & Logic Defects

Draft v0.2 establishes a strong foundation ("Generate probabilistically, verify deterministically", strict Pydantic contracts, role-separated agents, and an evidence-verified review-fix loop). However, evaluating v0.2 against the goal of transforming a **Vision PR + HLD Handoff into deployable, enterprise-grade production code** reveals **15 critical architectural, graph-loop, and implementation gaps** across five categories.

### 1.1 Summary Gap Matrix

| ID | Category | Severity | Gap / Defect in Draft v0.2 | Impact on Enterprise Deployability | Remediation in v0.3 Instruction Set |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | KG & LLD Loop | **Blocker** | **LLD is Open-Loop after L1:** `Rung.REPLAN_LLD` exists in `retry.py` and `loop.py`, but there is no contract, graph invalidation rule, or stage transition to mutate `LLDPack` when L3/L5 discovers an unimplementable module or interface defect. | Pipeline halts permanently whenever a coder/reviewer hits an LLD flaw during build. | Introduce **Closed-Loop LLD Delta Protocol (`L1-Replan`)** with surgical KG subgraph invalidation (`stale=True`). |
| **GAP-02** | KG & LLD Loop | **Blocker** | **No Serial- vs. Parallel-Execution KG Synchronization (MVCC):** L1 runs serially per component while L3–L5 runs 4 parallel worktrees and mutates the KG only *after* trunk merge. In-flight parallel workers run against stale graph slices and lack cross-component contracts during L1. | Parallel workers write conflicting integration assumptions; serial L1 components cannot resolve shared `CON-xxx` contracts. | Implement **Two-Phase L1 (Serial Global Topology → Parallel Module LLD)** and **MVCC Graph Snapshots (`graph_epoch`)** with pre-merge staleness gates. |
| **GAP-03** | KG Schema | **Major** | **Missing Enterprise Entities in KG:** Graph nodes omit `DataModel` (`DTO-xxx`), `DatabaseTable` (`TBL-xxx`), `ErrorEnvelope` (`ERR-xxx`), `AuthScope` (`SEC-xxx`), and `ConfigVar` (`CFG-xxx`). | Parallel modules pass type-checking on function signatures while inventing incompatible DB columns, env vars, and HTTP error payloads. | Expand KG ontology and `LLDPack` with first-class data, config, security, and error nodes. |
| **GAP-04** | Graph Math | **Blocker** | **Dependency Direction vs. Topological Merge Order Inversion:** In `Dependency(source, target)` and `BuildTask(depends_on)`, `A -> B` means *A depends on B* (`B` must execute/merge before `A`), whereas Kahn's `indeg == 0` in `assert_acyclic` starts at `A` (the caller) instead of `B` (the callee). | L3 scheduler merges callers before callees, breaking trunk integration builds immediately. | Separate cycle detection from **Reverse-Topological Execution Scheduling** (leaf dependencies build and merge first). |
| **GAP-05** | Vision PR Context | **Major** | **Vision PR Ubiquitous Language & Domain Invariants Stripped at H0:** `HLDHandoff` only retains `prd_sha256` and Gherkin strings, losing domain glossary terms, data privacy classifications (PII/PCI), and cross-story business invariants from the Vision PR. | Generated code uses inconsistent domain naming across services and misses domain-level invariants not repeated in every Gherkin scenario. | Add `DomainGlossary`, `BusinessInvariant`, and `DataClassification` to `HLDHandoff` and inject into every KG context slice. |
| **GAP-06** | LLD Depth | **Blocker** | **Under-Specified `FunctionSpec` & `ModuleSpec`:** L1 lacks DTO field schemas, transaction/idempotency boundaries, observability hooks (OTel spans, metrics, structured logs), and resilience policies (timeouts, retries, circuit breakers). | Output code is "toy" CRUD rather than enterprise-deployable code; fails NFR load and resilience testing. | Upgrade `ModuleSpec` and `FunctionSpec` with explicit `dto_schemas`, `transaction_boundary`, `idempotency_key`, `telemetry_spec`, and `resilience_policy`. |
| **GAP-07** | L2/L3 Wiring | **Blocker** | **"One Writer Per File" Deadlock on Shared Wiring Files:** Disjoint `files_owned` prevents multiple parallel tasks from registering routes in `main.py`, exporting ORM models in `models/__init__.py`, or wiring dependency injection in `dependencies.py`. | Either one giant task owns all wiring (destroying parallelism) or leaf modules are never wired into the FastAPI application. | L2a Scaffold deterministically generates **Auto-Discovery Registries / Wiring Manifests** directly from `LLDPack`; L3 workers touch only leaf module files. |
| **GAP-08** | L2b Oracle | **Blocker** | **Unseedable `Given` State in Black-Box Oracle:** L2b `oracle-writer` sees only ACs and OpenAPI specs, not DB schemas or internal services. When an AC states `Given an expired invoice exists`, the black-box test has no mechanism to seed that state. | 100% of stateful acceptance tests fail at runtime due to missing prerequisite state. | Introduce **Deterministic State Seeding Contracts (`FixtureContract` / `/__test__/seed` harness)** generated in L2a from LLD data models. |
| **GAP-09** | L3 Splitting | **Major** | **`Rung.SPLIT_TASK` Violates Disjoint File Ownership:** Section 9.3 splits an overflowing task "by file, then function". Splitting a single-file module by function assigns the same file to multiple child tasks, violating `TaskGraph.valid()`. | `TaskGraph` validation crashes whenever a single-file module splits by function. | Splitting a single-file task triggers a **Micro-LLD Package Split** (converting `foo.py` into package `foo/part_a.py`, `foo/part_b.py`, and frozen `foo/__init__.py`). |
| **GAP-10** | L4 Verification | **Blocker** | **Monolithic L4 Runs System-Level Gates on Single-Task Worktrees:** Section 10 runs all 16 L4 layers (including full `pytest-bdd` acceptance, Locust performance, and OWASP ZAP DAST) per build task *before* merge. | A single task implementing one repository class cannot boot the full system or pass end-to-end acceptance/DAST in isolation. | Bifurcate L4 into **L4-Task (Static, Unit, Property, Mutation, Module-Contract, SAST)** and **L4-Trunk/Sandbox (Integration, Migrations, Acceptance Oracle, Perf, Container/IaC, DAST, a11y)**. |
| **GAP-11** | L5 Ledger Bug | **Blocker** | **`FindingLedger.absorb()` Key-Drift Auto-Verification Bug:** `FindingLedger.key(f)` hashes `rule|file|quote`. If a coder modifies the quoted line without fixing the bug, the quote changes; the next round's `keys` set misses the old key, and `absorb()` falsely transitions the finding from `"fixed"` to `"verified"`. | Unfixed blocker findings silently mark themselves `"verified"` whenever the surrounding line text is edited. | Key findings by stable **`FindingId` + AST Symbol Anchor (`symbol_id` + `rule` + `dimension`)** and require explicit reviewer `reverification_verdict` per `open_finding_id`. |
| **GAP-12** | L5 Ledger Bug | **Major** | **`fix_proof` Failure Leaves Findings Stuck or Orphaned:** In `review_fix_loop`, if `fix_proof` returns `False`, the finding is not passed to `mark_fixed()`, staying `"open"`. If the reviewer does not re-emit the exact quote on the next round, it stays `"open"` forever with no explanation of why `fix_proof` failed. | Loop burns all 6 rounds and fails even when the code fix is right but the regression test didn't fail on `before` commit. | Emit a deterministic `FND-PROOF-xxx` finding when `fix_proof` fails, telling the coder specifically whether the regression test failed to fail on `before` or failed to pass on `after`. |
| **GAP-13** | L5 Alignment | **Major** | **`public_symbols_outside_lld` Rejects Valid Helper Types:** Tree-sitter/SCIP flags every non-underscore class/function (Pydantic models, FastAPI `router`, custom exceptions, Enums) as an unapproved public symbol if not listed in `FunctionSpec`. | `decide_alignment()` permanently returns `aligned=False` for idiomatic Python/FastAPI code. | Scope public symbol check to `__all__` exports and explicitly include `DataModelSpec`, `ErrorSpec`, and `FunctionSpec` in `REALIZES` graph edges. |
| **GAP-14** | L7 Rollback | **Major** | **Stateful DB Migration Rollback Missing in L7:** Section 13.2 runs Alembic `upgrade head` before smoke/ZAP tests, but on failure only runs `helm rollback`, leaving the database mutated. | Failed deployments corrupt the sandbox database schema and break subsequent runs. | Mandate **Transactional Pre-Deploy DB Snapshot + Alembic Downgrade Rehearsal** in L7 rollback handler. |
| **GAP-15** | Enterprise Ops | **Major** | **Missing Enterprise Production Readiness Contract:** Scaffold and LLD lack mandatory contracts for `/healthz` + `/readyz`, graceful `SIGTERM` drain, RFC 7807 error formatting, W3C trace propagation, secret mounting, and K8s `PodDisruptionBudget` / `NetworkPolicy` / resource limits. | Code passes unit tests but fails enterprise Kubernetes production readiness standards. | Bake an **Enterprise Baseline Contract (`ENT-001`..`ENT-008`)** into L2a templates and L4 fitness/IaC gates. |

## Part 2: Closed-Loop Knowledge Graph & LLD Architecture (Serial & Parallel Synchronization)

To ensure the pipeline outputs deployable enterprise code, **the Knowledge Graph (KG) and LLD cannot be static upstream artifacts**. They must operate as a **continuous, versioned state machine** that synchronizes context across **serial topology decisions** and **parallel worker execution**.

### 2.1 The Four Interlocking Loops of the KG-LLD Engine

| Loop | Execution Mode | Stage Scope | Core Responsibility & Deterministic Exit Gate |
| :--- | :--- | :--- | :--- |
| **Loop 1: Global Topology & Contract Freeze** | **Serial** | `H0` → `L1.1` | Ingest Vision PR Glossary, Invariants, Stories, ACs, NFRs, and Components. Synthesize cross-service API/Event Contracts (`CON`), Shared DTOs (`DTO`), DB Table Ownership (`TBL`), Error Envelopes (`ERR`), and Auth Scopes (`SEC`). **Gate:** Global KG Referential Integrity + Spectral Linting + Schema Acyclicity = `PASS` (`graph_epoch = E1`). |
| **Loop 2: Component LLD & Stub Verification** | **Parallel per Component** | `L1.2` ⇄ `L2a` | Decompose each `SVC-xxx` into `ModuleSpec`s, `FunctionSpec`s, DDL migrations, State Machines, Resilience, and Telemetry specs. Render Python AST stubs + SQL DDL + `import-linter` contracts. **Gate:** `mypy --strict` on stubs + Scratch DB Alembic Up/Down/Up + `lld_violations == []` (`graph_epoch = E2`). |
| **Loop 3: Wave-Scheduled Worktree Build-Verify-Review** | **Parallel per Wave + Serial Merge** | `L3` ⇄ `L4-Task` ⇄ `L5` | Execute leaf-first dependency waves (`Wave 0`, `Wave 1`, ...). Workers check out pinned MVCC KG Snapshot (`E_n`) and iterate Coder ⇄ `L4-Task` ⇄ Reviewer/Validator/Alignment. **Gate:** On merge to trunk, Tree-Sitter/SCIP updates `CodeSymbol` nodes (`E_{n+1}`) and runs a 2-hop blast-radius staleness check on concurrent tasks. |
| **Loop 4: Surgical LLD Mutation & Subgraph Replan** | **Serial Delta + Parallel Resume** | `L3/L5` → `L1-Replan` → `L2a` → `L3` | Triggered by `Rung.REPLAN_LLD` or `Rung.SPLIT_TASK`. Mutates only the failing `ModuleSpec` in `LLDPack`, marks 2-hop dependent KG nodes `stale=True`, regenerates stubs/contracts in `L2a`, and resumes `L3` only for `stale` tasks. |

### 2.2 Serial vs. Parallel Knowledge Graph Synchronization Protocol

1. **Why Serial + Parallel Co-Exist:**
   - **Serial Phases (Global Coherence):** Cross-service API contracts (`CON-xxx`), database table ownership (`TBL-xxx`), ubiquitous domain terms, and trunk merges (`E_n -> E_{n+1}`) **must execute serially** so there is a single source of truth for boundaries.
   - **Parallel Phases (Throughput within Frozen Boundaries):** Component-level LLD decomposition (`L1.2`), independent oracle generation (`L2b`), and leaf-module code implementation/review (`L3–L5`) **execute in parallel** because their external boundaries are already frozen in the KG.

2. **MVCC Graph Epochs (`graph_epoch`):**
   - Every mutation to the Knowledge Graph increments an integer `graph_epoch` and records a SHA-256 `graph_state_hash`.
   - When a parallel `BuildTask` starts in L3, its `ContextPacket` records `base_graph_epoch`.
   - **Wave-Based Parallelism:** The L3 scheduler groups the `TaskGraph` into **topological waves** (`Wave 0`: leaf modules with zero internal dependencies; `Wave 1`: modules depending only on `Wave 0`, etc.). All tasks within a wave run in parallel without code-level race conditions because their dependencies (`Wave < k`) are already merged and indexed in the KG, and their own public interfaces are frozen by L2a stubs.
   - **Cross-Task Risk & Contract Delta Propagation:** When Task A merges to trunk (creating `graph_epoch = E + 1`), the orchestrator updates `CodeSymbol` nodes and `RiskPattern` nodes. Before Task B (running concurrently in the same wave) merges, the orchestrator runs a **Pre-Merge Graph Delta Check**:
     - Did Task A modify any shared contract, fixture, or raise a `RiskPattern` attached to a module sharing data with Task B?
     - If no: Task B rebases cleanly onto trunk and merges.
     - If yes: Task B runs one incremental L4/L5 verification pass against `E + 1` before merge.

3. **Closed-Loop LLD Feedback (`L3/L5 -> L1-Replan -> L2a -> L3`):**
   - When a build task reaches `Rung.REPLAN_LLD` (e.g., an LLD `FunctionSpec` signature is missing a required dependency or cannot satisfy an AC without violating an import-linter boundary) or `Rung.SPLIT_TASK` (when a single-file module exceeds token budget or cyclomatic limits):
     1. The orchestrator pauses the failing `BuildTask` and packages an **`LLDDefectTicket`** containing: `module_id`, `ac_ids`, `verification_failures`, `open_findings`, and the deterministic `alignment_decision`.
     2. **L1-Replan Agent** receives only the defective `ModuleSpec`, its immediate 1-hop KG neighborhood, and the `LLDDefectTicket`. It emits an **`LLDPatch`** (adding/splitting submodules, updating `FunctionSpec` or `DataModelSpec`, or adding an internal `depends_on` edge).
     3. **Deterministic Gate:** `lld_violations(patched_lld, handoff, kg)` and `assert_acyclic` run immediately. Public external `ApiContract` (`CON-xxx`) changes are prohibited during a module-level replan unless escalated to a full component replan.
     4. **Selective Graph Invalidation:** The KG marks the modified `ModuleSpec` and any downstream `BuildTask` with a `DEPENDS_ON` edge to the changed `FunctionSpec` as `stale = True`. Unaffected modules remain `stale = False` and keep their merged commits.
     5. **L2a Incremental Stub Sync:** L2a regenerates the interface stubs and `import-linter` config for the patched module(s), and L3 resumes execution only for the `stale` subgraph.

## Part 3: Complete Master Instruction Set (Stages H0 through G2)

This section is the complete, normative instruction set required to build the pipeline and generate the code artifacts.

### 3.1 Extended Identifier & Contract Conventions (`contracts/base.py`)

In addition to the Draft v0.2 prefixes (`EP, ST, TSK, SVC, NFR, AC, ADR, MOD, CON, BLD, TST, FND, RSK`), add five enterprise entity prefixes so the KG tracks data schemas, errors, security scopes, configs, and LLD patches end-to-end:

| Prefix | Entity | Issued By | Example |
| :--- | :--- | :--- | :--- |
| `DTO` | Shared or Module Data Transfer Object / Pydantic Schema | L1.1 / L1.2 | `DTO-004` |
| `TBL` | Database Table / Persistent Entity Schema | L1.1 / L1.2 | `TBL-002` |
| `ERR` | Typed Domain Error / RFC 7807 Problem Detail Contract | L1.1 | `ERR-001` |
| `SEC` | Authentication / Authorization Scope or RBAC Policy | L1.1 | `SEC-002` |
| `CFG` | Environment Variable / Typed Secret Configuration Key | L1.2 | `CFG-005` |

```python
# Upgraded ID types in contracts/base.py
DtoId, TableId, ErrorId = _id("DTO"), _id("TBL"), _id("ERR")
SecId, ConfigId = _id("SEC"), _id("CFG")
```

**Corrected Graph Utility (`contracts/graphutil.py`):**
Fix **GAP-04** by explicitly distinguishing cycle verification from **dependency-first topological wave scheduling**:

```python
# contracts/graphutil.py
from collections import deque

def assert_acyclic(edges: list[tuple[str, str]]) -> None:
    # Verify directed graph has no cycles. Edge (a, b) means 'a depends on b'.
    unique_edges = set(edges)
    nodes = {n for e in unique_edges for n in e}
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for dependent, dependency in unique_edges:
        if dependent == dependency:
            raise ValueError(f"self-dependency cycle on {dependent}")
        adj[dependency].append(dependent)
        indeg[dependent] += 1
    queue = deque(sorted(n for n, d in indeg.items() if d == 0))
    visited = 0
    while queue:
        curr = queue.popleft()
        visited += 1
        for nxt in sorted(adj[curr]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if visited != len(nodes):
        cycling = sorted(n for n, d in indeg.items() if d > 0)
        raise ValueError(f"dependency cycle detected among: {', '.join(cycling)}")

def topological_waves(nodes: set[str], dependency_edges: list[tuple[str, str]]) -> list[list[str]]:
    # Return execution waves where Wave 0 has zero dependencies, Wave 1 depends only on Wave 0, etc.
    # Edge (dependent, dependency) means `dependency` MUST complete before `dependent` starts.
    assert_acyclic(dependency_edges)
    unique_edges = set(dependency_edges)
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for dependent, dependency in unique_edges:
        adj[dependency].append(dependent)
        indeg[dependent] += 1
    current_wave = sorted(n for n, d in indeg.items() if d == 0)
    waves: list[list[str]] = []
    while current_wave:
        waves.append(current_wave)
        next_wave: list[str] = []
        for u in current_wave:
            for v in sorted(adj[u]):
                indeg[v] -= 1
                if indeg[v] == 0:
                    next_wave.append(v)
        current_wave = sorted(next_wave)
    return waves
```

### 3.2 Stage H0: Vision PR & HLD Handoff Intake (`stages/h0_intake.py`)

**Objective:** Validate the incoming `HLDHandoff` manifest, preserve the Vision PR's ubiquitous language and business invariants (**GAP-05**), enforce 100% referential integrity, and populate the initial Knowledge Graph (`graph_epoch = 0`).

#### Upgraded `HLDHandoff` Contract Additions (`contracts/handoff.py`)

```python
class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED_PII = "restricted_pii"
    RESTRICTED_PCI = "restricted_pci"

class DomainTerm(Contract):
    term: str = Field(pattern="^[A-Za-z][A-Za-z0-9_ -]+$")
    canonical_snake: str = Field(pattern="^[a-z][a-z0-9_]*$")
    definition: str = Field(min_length=10)
    classification: DataClassification = DataClassification.INTERNAL

class BusinessInvariant(Contract):
    id: str = Field(pattern="^INV-[0-9]{3,5}$")
    statement: str = Field(min_length=15)
    applies_to_stories: list[StoryId] = Field(min_length=1)
```

Add `domain_glossary: list[DomainTerm] = Field(min_length=1)` and `business_invariants: list[BusinessInvariant] = []` to `HLDHandoff`.

#### H0 Execution Instructions
1. Parse incoming JSON into `HLDHandoff` (strict Pydantic v2 validation).
2. Verify `handoff_version` major version matches supported major version (`1.x.x`).
3. Verify `assert_acyclic` on runtime component dependencies and check that every `TaskId`, `AcId`, `NfrId`, and `AdrId` resolves with zero orphans.
4. Load all `Story`, `Task`, `AC`, `NFR`, `Component`, `ADR`, `DomainTerm`, and `BusinessInvariant` nodes and edges into the Knowledge Graph (`graph_epoch = 0`).
5. Emit `StageResult[HLDHandoff]`. On any validation error, emit a structured `HandoffDefectReport` and halt immediately (zero AI repair on upstream HLD handoff).

### 3.3 Stage L1: Two-Phase Closed-Loop LLD Generation (`stages/l1_lld.py`)

**Objective:** Transform `HLDHandoff` into a complete, enterprise-grade `LLDPack` that is continuously cross-checked against the Knowledge Graph, compiler type-checkers, OpenAPI/AsyncAPI linters, and scratch database migrations (**GAP-01, GAP-02, GAP-03, GAP-06**).

#### Upgraded `LLDPack` Contract (`contracts/lld.py`)

```python
class FieldSpec(Contract):
    name: str = Field(pattern="^[a-z][a-z0-9_]*$")
    type_annotation: str
    required: bool = True
    constraints: str | None = None
    classification: DataClassification = DataClassification.INTERNAL

class DataModelSpec(Contract):
    id: DtoId
    name: str = Field(pattern="^[A-Z][A-Za-z0-9]+$")
    module_id: ModuleId
    fields: list[FieldSpec] = Field(min_length=1)
    validators: list[str] = []

class TableSpec(Contract):
    id: TableId
    table_name: str = Field(pattern="^[a-z][a-z0-9_]*$")
    owner_component_id: ServiceId
    module_id: ModuleId
    primary_key: list[str] = Field(min_length=1)
    columns: list[FieldSpec] = Field(min_length=1)
    foreign_keys: list[str] = []           # format: "col -> table.col"
    indexes: list[list[str]] = []

class ErrorSpec(Contract):
    id: ErrorId
    exception_name: str = Field(pattern="^[A-Z][A-Za-z0-9]+Error$")
    http_status: int = Field(ge=400, le=599)
    problem_type_uri: str
    module_id: ModuleId

class ResiliencePolicy(Contract):
    timeout_ms: int = Field(default=5000, ge=50)
    max_retries: int = Field(default=0, ge=0, le=5)
    backoff_base_ms: int = Field(default=200, ge=10)
    idempotency_required: bool = False
    circuit_breaker_threshold: int | None = None

class TelemetrySpec(Contract):
    span_name: str
    structured_log_events: list[str] = []
    metrics_emitted: list[str] = []

class FunctionSpec(Contract):
    name: str = Field(pattern="^[a-z_][a-z0-9_]*$")
    signature: str                         # e.g. "async def create_order(cmd: CreateOrderCmd, uow: UnitOfWork) -> OrderDTO"
    purpose: str = Field(min_length=10)
    input_dtos: list[DtoId] = []
    output_dto: DtoId | None = None
    raises: list[ErrorId] = []
    preconditions: list[str] = []
    postconditions: list[str] = []
    transaction_boundary: Literal["required", "requires_new", "read_only", "none"] = "none"
    resilience: ResiliencePolicy = ResiliencePolicy()
    telemetry: TelemetrySpec | None = None
    max_cyclomatic: int = Field(default=10, ge=1, le=15)
    ac_ids: list[AcId] = []

class ModuleSpec(Contract):
    id: ModuleId
    component_id: ServiceId
    path: str                              # e.g. "services/order_service/app/domain/orders.py"
    layer: Literal["domain", "application", "adapters", "api", "worker", "config"]
    responsibilities: list[str] = Field(min_length=1)
    public_interface: list[FunctionSpec] = Field(min_length=1)
    data_models: list[DataModelSpec] = []
    tables: list[TableSpec] = []
    errors: list[ErrorSpec] = []
    config_keys: list[ConfigId] = []
    depends_on: list[ModuleId] = []
    task_ids: list[TaskId] = Field(min_length=1)
    ac_ids: list[AcId] = Field(min_length=1)
    tags: list[Literal["core_logic", "io", "persistence", "api", "worker"]] = []

class LLDPatch(Contract):
    target_lld_version: str
    new_lld_version: str
    defect_ticket_id: str
    replaced_modules: list[ModuleSpec] = Field(min_length=1)
    removed_module_ids: list[ModuleId] = []
    rationale: str = Field(min_length=20)
```

#### L1 Execution Instructions (Two-Phase Serial + Parallel Loop)
- **Phase L1.1 (Serial Global Contract & Data Topology Freeze):**
  1. Query the KG for all `Relationship` edges across components, `DomainTerm`s, `BusinessInvariant`s, and `NFR`s.
  2. Generate and freeze:
     - All inter-component `ApiContract` files (`OpenAPI 3.1` / `AsyncAPI 2.6`), assigning `CON-xxx` IDs.
     - Shared RFC 7807 `ErrorSpec` catalog (`ERR-xxx`) and `SecId` auth scopes (`SEC-xxx`).
     - Database ownership boundaries (`TBL-xxx` mapped to a single owning `ServiceId`—no cross-service shared tables).
  3. **Deterministic Gate L1.1:** Validate all OpenAPI/AsyncAPI specs via Spectral; verify every `Relationship.contract_ref` in `HLDHandoff` resolves to a valid `ApiContract`. Commit to KG (`graph_epoch = 1`).
- **Phase L1.2 (Parallel Component LLD Generation + Deterministic Verification Loop):**
  1. For each `Component` (`SVC-xxx`) in parallel, retrieve its budgeted KG slice (component tasks, ACs, NFRs, ADRs, global `ApiContract`s, and `DomainTerm`s).
  2. LLD Agent generates `ModuleSpec`s following clean hexagonal layering (`domain` ← `application` ← `adapters` / `api` / `worker`), `DataModelSpec`s (`DTO-xxx`), `TableSpec`s (`TBL-xxx`), `FunctionSpec`s, and SQL/Alembic DDL files.
  3. **Deterministic Gate L1.2 (The LLD-KG Verification Loop):**
     - Run `lld_violations(lld, handoff, kg)` checking:
       - Every `TaskId` and `AcId` is mapped to at least one `ModuleSpec` and `FunctionSpec`.
       - Layer dependency direction holds (`domain` never depends on `adapters` or `api`).
       - `assert_acyclic` passes on `ModuleSpec.depends_on`.
       - Every `Input/Output DTO` and `ErrorId` referenced in `FunctionSpec` exists in `LLDPack`.
       - Every `DomainTerm` in a story's ACs matches the `canonical_snake` naming in `DataModelSpec` / `TableSpec`.
     - Render Python `.pyi` / stub `.py` files from `ModuleSpec` and run `mypy --strict`.
     - Apply generated DDL / Alembic migrations (`upgrade head` → `downgrade base` → `upgrade head`) against an ephemeral SQLite/PostgreSQL scratch instance.
     - If any check fails, format the exact deterministic error list into the LLD repair prompt template and iterate up to `per_rung` retries before escalating on the retry ladder.
  4. Commit verified `LLDPack` to KG (`graph_epoch = 2`).

### 3.4 Stage L2: Deterministic Scaffold & Independent Oracle (`stages/l2_scaffold.py`, `stages/l2_oracle.py`)

**Objective:** Run L2a (Deterministic Scaffold) and L2b (Independent Acceptance Oracle) in parallel against `graph_epoch = 2`.

#### L2a: Deterministic Scaffold & Auto-Discovery Wiring (`l2_scaffold.py`)
1. **Zero AI Generation:** Render repository structure from Copier templates keyed to `target_platform` and `technology_stack`.
2. **Solve the Shared-File Wiring Deadlock (GAP-07):**
   - Generate `app/main.py`, `app/api/router_registry.py`, `app/db/model_registry.py`, and `app/core/container.py` **deterministically from `LLDPack` during L2a**!
   - `router_registry.py` dynamically imports each `api`-layered `ModuleSpec.path` declared in `LLDPack`.
   - `model_registry.py` imports every `persistence`-layered `TableSpec` module for Alembic.
   - Lock `main.py`, `router_registry.py`, `model_registry.py`, `pyproject.toml`, `import-linter.ini`, `.github/workflows/ci.yml`, `Dockerfile`, and `helm/` as **protected paths** so L3 workers only ever edit their isolated `ModuleSpec.path` and unit test files!
3. **Enterprise Production Baseline (GAP-15):**
   - Emit built-in `/healthz` (liveness) and `/readyz` (DB/broker readiness check) endpoints, W3C `traceparent` + `X-Request-ID` middleware, RFC 7807 global exception handler wired to `ErrorSpec`, structured JSON logger, and graceful `SIGTERM` lifespan hook.
4. **Deterministic State Seeding Harness (GAP-08):**
   - Emit `tests/harness/state_seeder.py` (enabled only when `ENV=sandbox_test`) providing a typed fixture factory mapped to `TableSpec` / `DataModelSpec` so black-box `pytest-bdd` `Given` steps can seed prerequisite domain entities deterministically without coupling to internal function implementation details.
5. **Gate L2a:** Run `ruff`, `mypy --strict`, `import-linter`, and `pytest` on the empty scaffolded stub repo. Must exit `0`.

#### L2b: Independent Acceptance Oracle (`l2_oracle.py`)
1. **Strict Information Barrier:** `oracle-writer` receives **only**:
   - Story `AcceptanceCriterion` list (`AC-xxx-yy` with Gherkin `Given/When/Then`).
   - Frozen `ApiContract` files (`OpenAPI`/`AsyncAPI`) from L1.1.
   - Public `DataModelSpec` / `FixtureContract` schemas for `Given` state seeding.
   - It **never** sees `FunctionSpec` internals, `ModuleSpec` private logic, or coder implementation files.
2. **Output:** `tests/acceptance/test_ac_<story_id>.py` using `pytest-bdd` + `httpx.AsyncClient`, with `@pytest.mark.ac("AC-xxx-yy")` decorators on every test function.
3. **Gate L2b:**
   - Run `pytest --collect-only` on `tests/acceptance/` to prove syntax and fixture validity.
   - Run KG invariant query: verify 1:1 `(:Test)-[:VERIFIES]->(:AC)` coverage for every `AC` in `HLDHandoff`.
   - Freeze `tests/acceptance/` as a read-only protected path and advance KG to `graph_epoch = 3`.

### 3.5 Stage L3: Wave-Scheduled Parallel Build & Context Slicing (`stages/l3_build.py`)

**Objective:** Schedule and execute `BuildTask`s in parallel waves with strict file-ownership isolation, budgeted KG context slices, and pre-merge KG staleness checks.

#### Upgraded `BuildTask` & Wave Scheduler (`contracts/tasks.py`, `orchestration/scheduler.py`)
1. **Task Graph Construction:**
   - Planner maps each `ModuleSpec` (`MOD-xxx`) to a `BuildTask` (`BLD-xxx`) owning `[module.path, f"tests/unit/test_{module.id.lower()}.py"]`.
   - `depends_on` edges are derived directly from `ModuleSpec.depends_on`.
   - Compute execution waves via `topological_waves(task_ids, dependency_edges)` (**GAP-04 fix**).
2. **Budgeted Context Packet Assembly (`orchestration/context.py`):**
   - Assemble context in strict priority order up to `token_budget` (default `24,000` tokens):
     1. **P0 (Never Dropped/Summarized):** Target `ModuleSpec` (full `FunctionSpec`, `DataModelSpec`, `TableSpec`, `ErrorSpec`), linked `AcceptanceCriterion` items, linked `ApiContract` fragments, and `BusinessInvariant`s.
     2. **P1 (Never Dropped):** 1-hop dependency stub signatures (`depends_on` modules) and `DomainTerm` glossary.
     3. **P2:** Ancestor `AdrSummary` items and active `RiskPattern`s (`RSK-xxx`) attached via `GUARDS` to this module or its 1-hop neighbors.
     4. **P3:** 2-hop neighbor merged code excerpts and pinned library documentation snippets.
   - **Pre-Flight Split Rule (GAP-09 fix):** If `P0 + P1 > token_budget`, do **not** split functions inside the same file. Instead, invoke `L1-Replan` to convert `module_path/foo.py` into a subpackage (`module_path/foo/part_1.py`, `module_path/foo/part_2.py`, and frozen `module_path/foo/__init__.py`), creating disjoint child `BuildTask`s.
3. **Worktree Execution & Trunk Rebase Protocol:**
   - Up to `concurrency = 4` workers execute tasks from the active wave in isolated containers + `git worktree` checkouts pinned to `base_graph_epoch`.
   - Each worker enters the **Per-Task L4-Task ⇄ L5 Review-Fix Loop**.
   - When a task converges (`LoopOutcome.CONVERGED`):
     - Acquire the serial Trunk Merge Lock.
     - Check if `current_trunk_epoch > task.base_graph_epoch`. If trunk advanced while the task was running, run the **KG Blast-Radius Staleness Query** (checking if any newly merged symbol or `RiskPattern` touches a 1-hop neighbor of `task.module_id`). If affected, rebase the worktree and run `L4-Task` + `decide_alignment` once before completing the merge.
     - Merge to trunk, run incremental Tree-Sitter + SCIP indexer to populate `CodeSymbol` nodes and `(:CodeSymbol)-[:REALIZES]->(:FunctionSpec|DataModelSpec|ErrorSpec)` edges, and increment `graph_epoch`.

### 3.6 Stage L4: Bifurcated Deterministic Verification (`stages/l4_verify.py`)

**Objective:** Resolve **GAP-10** by splitting deterministic verification into **L4-Task** (fast, module-scoped gates run on every coder round) and **L4-Trunk** (full-system integration, acceptance, performance, container, and security gates run on merged trunk).

| Verification Tier | Layer | Tool | Deterministic Gate Criteria |
| :--- | :--- | :--- | :--- |
| **L4-Task** *(Per-Task Worktree, < 45s)* | 1. Format & Lint | `ruff check` & `ruff format --check` | 0 errors; cyclomatic complexity `<= max_cyclomatic` |
| **L4-Task** | 2. Static Types | `mypy --strict` | 0 errors across module + unit tests + stubs |
| **L4-Task** | 3. Architecture Fitness | `import-linter` | 0 broken layer or module dependency contracts |
| **L4-Task** | 4. Unit & Coverage | `pytest tests/unit/test_<mod>.py --cov` | Line `>= 0.85`, Branch `>= 0.75` on target module |
| **L4-Task** | 5. Property Tests | `hypothesis` | Required and passing if module tagged `core_logic` |
| **L4-Task** | 6. Mutation Testing | `mutmut` (scoped to target module) | Mutation score `>= 0.70` on `core_logic` and `api` modules |
| **L4-Task** | 7. SAST & Secrets | `semgrep`, `bandit`, `gitleaks` | 0 high/critical findings, 0 leaked secrets |
| **L4-Task** | 8. Dependency Gate | `package_gate.py` + `pip-audit` | 0 unapproved imports; 0 protected-path edits |
| **L4-Trunk** *(Post-Wave & Full System)* | 9. DB Migrations | `alembic upgrade head && downgrade base && upgrade head` | Clean up/down/up on PostgreSQL testcontainer |
| **L4-Trunk** | 10. Integration Suite | `pytest tests/integration` (Testcontainers) | 100% pass against real PostgreSQL / Broker |
| **L4-Trunk** | 11. API Contract Fuzzing | `schemathesis` + AsyncAPI validator | 0 contract schema or status code violations |
| **L4-Trunk** | 12. Frozen Oracle (L2b) | `pytest tests/acceptance` (`pytest-bdd`) | 100% of `AC-xxx-yy` scenarios pass |
| **L4-Trunk** | 13. Performance (NFRs) | `k6` / `locust` scripts generated from `NFR`s | All latency/throughput NFR comparators satisfied |
| **L4-Trunk** | 14. Container & IaC | `trivy image`, `checkov -d helm/` | 0 high/critical CVEs or IaC misconfigurations |
| **L4-Trunk** | 15. DAST | `OWASP ZAP` baseline scan vs. sandbox | 0 high/critical alerts |
| **L4-Trunk** | 16. Accessibility (if UI) | `Playwright` + `@axe-core/playwright` | 0 serious/critical a11y violations |

### 3.7 Stage L5: Hardened Review-Fix Loop & Ledger (`stages/l5_review.py`, `review/loop.py`)

**Objective:** Fix the `FindingLedger` auto-verification and `fix_proof` bugs (**GAP-11, GAP-12, GAP-13**) while maintaining a 100% deterministic loop controller.

#### Upgraded `Finding`, `PriorFindingStatus`, and `FindingLedger` (`contracts/review.py`, `review/loop.py`)

```python
# Upgraded contracts/review.py additions
class Finding(Contract):
    id: FindingId
    dimension: Dimension
    severity: Severity
    rule: str
    file: str
    line: int = Field(ge=1)
    symbol_name: str = Field(min_length=1)           # AST function/class/variable anchor (fixes GAP-11)
    quote: str = Field(min_length=3)
    impact: str = Field(min_length=20)
    refs: list[str] = Field(min_length=1)
    repro_artifact: str | None = None
    source: Literal["reviewer", "scanner", "verification", "fix_proof"]

class PriorFindingStatus(Contract):
    finding_id: FindingId
    still_present: bool
    evidence_note: str = Field(min_length=10)

class ReviewReport(Contract):
    build_id: BuildId
    round_no: int
    commit_sha: str
    files_reviewed: list[str]
    findings: list[Finding]
    prior_finding_checks: list[PriorFindingStatus] = []   # Required for every open_finding_id in ReviewPackage
    dropped_unverifiable: int = 0
```

#### Corrected `FindingLedger` Implementation (`review/loop.py`)
1. **Stable Identity (`symbol_key`):** Identify findings by `f"{f.rule}|{f.file}|{f.symbol_name}"` rather than raw `quote` text so editing a line does not silently orphan or auto-verify the finding (**GAP-11 fix**).
2. **Explicit Two-Factor Verification of Fixes:**
   - A finding transitions from `"open"` → `"fixed_pending_review"` **only** when:
     - For `correctness` and `security` (`blocker`/`major`): `ports.fix_proof(f, before_sha, after_sha)` returns `True` (a new or updated test in the diff fails on `before_sha` and passes on `after_sha`).
     - If `fix_proof` returns `False`, the harness injects a deterministic `Finding(source="fix_proof", severity=Severity.BLOCKER, ...)` explaining whether the test passed on `before_sha` (test doesn't reproduce the bug) or failed on `after_sha` (fix didn't work) (**GAP-12 fix**).
   - A `"fixed_pending_review"` finding transitions to `"verified"` in Round `N+1` **only** when:
     - `L4-Task` passes, **AND**
     - Its `symbol_key` is not raised in `report.findings`, **AND**
     - `report.prior_finding_checks` contains `PriorFindingStatus(finding_id=f.id, still_present=False)`.
3. **Scoped Public Symbol Alignment (`review/alignment.py` - GAP-13 fix):**
   - Update the KG invariant query in `public_symbols_outside_lld` so a public symbol is valid if it has a `[:REALIZES]` edge to **any** of `(:FunctionSpec)`, `(:DataModelSpec)`, `(:TableSpec)`, or `(:ErrorSpec)`, or is a framework entrypoint declared in `L2a` scaffold (`router`, `Base`).

### 3.8 Stages L6, L7 & G2: Conformance, Transactional Deploy, and Release Gate

1. **L6 Conformance (`stages/l6_conformance.py`):**
   - Execute all 5 KG Cypher invariant queries (untested ACs, unimplemented tasks, unowned modules, unapproved public symbols, unresolved blocker/major findings). All 5 must return **0 rows**.
   - Execute `JourneyAgent` against the live sandbox to produce `ConformanceReport` with recorded HTTP response hashes / screenshots per `StoryId`.
   - Run advisory `ReverseSpecDiff` (comparing deployed OpenAPI + observed responses against `HLDHandoff.stories`).
2. **L7 Enterprise Sandbox Deploy (`stages/l7_deploy.py` - GAP-14 & GAP-15 fixes):**
   - Build rootless, digest-pinned container images; scan with `trivy`.
   - Take a pre-migration PostgreSQL snapshot (or create a transactional branch/savepoint).
   - Apply Helm chart / Compose stack with Kubernetes `NetworkPolicy`, `PodDisruptionBudget`, CPU/memory requests & limits, and mounted `Secret`s.
   - Run `alembic upgrade head`, execute smoke suite (`/healthz`, `/readyz`, 1 call per `ApiContract` operation) and `OWASP ZAP` baseline scan.
   - **Transactional Rollback Rule:** If any smoke or ZAP check fails, execute `alembic downgrade` to the pre-deploy revision (or restore DB snapshot) **before** executing `helm rollback`, then emit a structured `DeploymentFailureReport`.
   - Emit `ReleaseBundle` containing all 8 templated review/traceability artifacts, SBOM (`syft`), provenance attestation, and runbook.

## Part 4: Recommendations for Section 18 Open Items & Artifact Generation Plan

### 4.1 Recommendations on Your Section 18 Confirmation Items

| # | Item from Draft v0.2 (Section 18) | Critical Reviewer Recommendation |
| :--- | :--- | :--- |
| **1** | **Phase 1 Handoff Changes:** Who owns NFRs, responsibilities, dependencies, relationships, AC IDs, ADR summaries, and the new Vision Glossary/Invariants? | **Phase 1 HLD Agent emits them; H0 deterministically assigns `AC-xxx-yy` IDs and flags default-filled NFRs (`assumption=True`).** If Phase 1 omits domain terms or NFRs, H0's intake preprocessor populates defaults from a strict domain template and marks `assumption=True` for G1/H0 visibility. |
| **2** | **Component IDs (`SVC-` vs `CMP-`):** Keep `SVC-` to preserve Phase 1 manifests? | **Keep `SVC-` (`ServiceId`).** Zero value in renaming; maintaining 100% backward compatibility with Phase 1 manifests avoids translation bugs. |
| **3** | **Skill Step Order:** `Understand -> Review -> Prioritize -> Secure -> Align -> Re-verify` vs. literal notes order? | **Keep your v0.2 order (`Understand -> Review -> Prioritize -> Secure -> Align -> Re-verify`).** Reviewing code before reading requirements, LLD, ADRs, and blast-radius files causes high false-positive rates and missed requirement drift. |
| **4** | **Convergence Threshold (`min_score`):** Default `4` (minors allowed and documented) vs. `5` (zero findings)? | **Keep `min_score = 4` for per-task L5 loops, but require `5` on `Correctness` and `Security` dimensions** (i.e., only `minor` findings in `conventions` or `performance` may remain at score 4 and land in `unresolved-findings.md`). |
| **5** | **QA-Checker Deviation:** Deterministic `decide_alignment()` from KG + test evidence instead of an LLM judge? | **Strongly endorse deterministic `decide_alignment()`.** Letting an LLM self-certify alignment is the #1 cause of silent requirement drift in multi-agent coding pipelines. |
| **6** | **Model Tiers (Reviewer, Validator, Coder):** Which model tiers for each role? | **Reviewer = Frontier Reasoning Model (Tier 1); Coder = Fast Frontier Coding Model (Tier 1/1.5); Validator = Independent Cross-Family Frontier Model (Tier 1).** Using an independent model family (or zero-context-bleed instance) for the Validator prevents correlated hallucinations on security suppressions and false positives. |
| **7** | **Default Stack & Target Platform:** Python 3.12 / FastAPI / PostgreSQL on k3s sandbox, G2 human in v1? | **Keep as the normative v1 reference stack.** Add `SQLAlchemy 2.0 (asyncpg) + Alembic + Pydantic v2 + OpenTelemetry + structlog` as the pinned enterprise library baseline inside the L2a FastAPI template. |

### 4.2 Artifact Build Plan (To Execute Immediately Upon Your Approval)

Once you approve this instruction set (and confirm or adjust the 7 decisions above), I will generate the complete, executable codebase for the pipeline in the following order:

1. **Module Group 1 — Contracts & Graph Core (`pipeline/contracts/`, `pipeline/graph/`):**
   - `base.py`, `graphutil.py` (with `assert_acyclic` and `topological_waves`), `envelope.py`, `handoff.py`, `lld.py` (with `DataModelSpec`, `TableSpec`, `ErrorSpec`, `ResiliencePolicy`, `LLDPatch`, `lld_violations`), `tasks.py`, `verification.py`, `review.py`, `conformance.py`, `release.py`.
   - `port.py`, `sqlite_adapter.py` (in-process MVCC KG implementation supporting `graph_epoch`, blast-radius 2-hop queries, staleness propagation, and the 5 invariant checks), and `invariants.cypher`.
2. **Module Group 2 — Deterministic Verification, Review-Fix Loop & Orchestration (`pipeline/review/`, `pipeline/orchestration/`, `pipeline/harness/`):**
   - `evidence.py`, `alignment.py`, `loop.py` (with hardened `FindingLedger`, `fix_proof` failure injection, and `PriorFindingStatus` checks).
   - `retry.py`, `context.py` (budgeted KG packet builder), `scheduler.py` (wave-based parallel worktree runner + pre-merge KG staleness check), `runner.py` (closed-loop stage state machine including `L1-Replan` loop).
   - `sandbox.py`, `package_gate.py`, and L4-Task / L4-Trunk tool adapters.
3. **Module Group 3 — Pipeline Stages (`pipeline/stages/`), LLM Clients (`pipeline/llm/`), Skills & Config (`pipeline/skills/`, `pipeline/config/`):**
   - `h0_intake.py` through `l7_deploy.py`, `base.py` / `mock.py` deterministic LLM harness, `skills/code-review/SKILL.md`, `skills/lld/SKILL.md`, `skills/oracle/SKILL.md`, and `config/gates.yaml`.
4. **Module Group 4 — Verification Test Suite (`pipeline/tests/`):**
   - Complete unit and integration test suite verifying every negative contract rule, topological wave ordering, KG staleness propagation, `L1-Replan` closed loop, `FindingLedger` state transitions, and a full end-to-end mock pipeline run from `HLDHandoff` to `ReleaseBundle`.
