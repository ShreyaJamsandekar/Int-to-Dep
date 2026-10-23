"""Stage L1: Two-phase closed-loop LLD generation (L1.1 Global Contracts + L1.2 Component LLD)."""
from __future__ import annotations

from pipeline.contracts.base import utc_now_iso, sha256_obj
from pipeline.contracts.envelope import StageResult
from pipeline.contracts.handoff import HLDHandoff, DataClassification
from pipeline.contracts.lld import (
    LLDPack,
    ModuleSpec,
    FunctionSpec,
    DataModelSpec,
    TableSpec,
    ErrorSpec,
    FieldSpec,
    ApiContract,
    ResiliencePolicy,
    TelemetrySpec,
    lld_violations,
)
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


def synthesize_lld_from_handoff(handoff: HLDHandoff) -> LLDPack:
    """
    Two-phase LLD synthesizer:
      - Phase L1.1 freezes global API contracts (`CON-xxx`), error envelopes (`ERR-xxx`),
        and database table ownership (`TBL-xxx`).
      - Phase L1.2 decomposes each HLD Component (`SVC-xxx`) into hexagonal `ModuleSpec`s
        (`domain` and `api` layers) mapped to every Story Task and Acceptance Criterion.
    """
    api_contracts: list[ApiContract] = []
    seen_con: set[str] = set()
    for rel in handoff.relationships:
        if rel.contract_ref and rel.contract_ref not in seen_con:
            seen_con.add(rel.contract_ref)
            api_contracts.append(
                ApiContract(
                    id=rel.contract_ref,
                    kind="openapi" if rel.protocol in ("http", "grpc") else "asyncapi",
                    path=f"contracts/{rel.contract_ref.lower()}.yaml",
                    sha256=sha256_obj({"contract_id": rel.contract_ref, "handoff": handoff.handoff_id}),
                    auth_scopes=["SEC-001"],
                )
            )
    if not api_contracts:
        api_contracts.append(
            ApiContract(
                id="CON-001",
                kind="openapi",
                path="contracts/con-001.yaml",
                sha256=sha256_obj({"contract_id": "CON-001", "handoff": handoff.handoff_id}),
                auth_scopes=["SEC-001"],
            )
        )

    story_by_task: dict[str, list[str]] = {}
    for st in handoff.stories:
        ac_list = [a.id for a in st.criteria]
        for tid in st.task_ids:
            story_by_task.setdefault(tid, []).extend(ac_list)

    modules: list[ModuleSpec] = []
    ddl_files: list[str] = []
    mod_seq = 1

    for comp_idx, comp in enumerate(handoff.components, start=1):
        comp_slug = comp.name.replace("-", "_")
        comp_acs = sorted({ac for tid in comp.linked_task_ids for ac in story_by_task.get(tid, [])})
        if not comp_acs:
            comp_acs = [handoff.stories[0].criteria[0].id]

        # 1. Domain & Persistence Module (Wave 0 leaf dependency)
        dom_mod_id = f"MOD-{mod_seq:03d}"
        mod_seq += 1
        dto_in_id = f"DTO-{comp_idx * 2 - 1:03d}"
        dto_out_id = f"DTO-{comp_idx * 2:03d}"
        tbl_id = f"TBL-{comp_idx:03d}"
        err_id = f"ERR-{comp_idx:03d}"

        primary_term = (
            handoff.domain_glossary[0].canonical_snake
            if handoff.domain_glossary
            else f"{comp_slug}_record"
        )

        dom_mod = ModuleSpec(
            id=dom_mod_id,
            component_id=comp.id,
            path=f"services/{comp_slug}/domain_service.py",
            layer="domain",
            responsibilities=[f"Core domain logic and persistence for {comp.name}"],
            public_interface=[
                FunctionSpec(
                    name=f"process_{comp_slug}",
                    signature=f"def process_{comp_slug}(payload: {comp_slug.title().replace('_', '')}Request) -> {comp_slug.title().replace('_', '')}Response",
                    purpose=f"Validate business invariants and execute domain logic for {comp.name}.",
                    input_dtos=[dto_in_id],
                    output_dto=dto_out_id,
                    raises=[err_id],
                    preconditions=["payload.quantity > 0"],
                    postconditions=["result.status == 'PROCESSED'"],
                    transaction_boundary="required",
                    resilience=ResiliencePolicy(timeout_ms=2000, max_retries=1, idempotency_required=True),
                    telemetry=TelemetrySpec(
                        span_name=f"{comp_slug}.process",
                        structured_log_events=[f"{comp_slug}_processed"],
                        metrics_emitted=[f"{comp_slug}_processed_total"],
                    ),
                    max_cyclomatic=10,
                    ac_ids=comp_acs,
                )
            ],
            data_models=[
                DataModelSpec(
                    id=dto_in_id,
                    name=f"{comp_slug.title().replace('_', '')}Request",
                    module_id=dom_mod_id,
                    fields=[
                        FieldSpec(name=primary_term, type_annotation="str", required=True),
                        FieldSpec(name="quantity", type_annotation="int", required=True),
                    ],
                ),
                DataModelSpec(
                    id=dto_out_id,
                    name=f"{comp_slug.title().replace('_', '')}Response",
                    module_id=dom_mod_id,
                    fields=[
                        FieldSpec(name="record_id", type_annotation="str", required=True),
                        FieldSpec(name=primary_term, type_annotation="str", required=True),
                        FieldSpec(name="quantity", type_annotation="int", required=True),
                        FieldSpec(name="status", type_annotation="str", required=True),
                    ],
                ),
            ],
            tables=[
                TableSpec(
                    id=tbl_id,
                    table_name=f"{comp_slug}_records",
                    owner_component_id=comp.id,
                    module_id=dom_mod_id,
                    primary_key=["record_id"],
                    columns=[
                        FieldSpec(name="record_id", type_annotation="TEXT"),
                        FieldSpec(
                            name=primary_term,
                            type_annotation="TEXT",
                            classification=DataClassification.CONFIDENTIAL,
                        ),
                        FieldSpec(name="quantity", type_annotation="INTEGER"),
                        FieldSpec(name="status", type_annotation="TEXT"),
                    ],
                    indexes=[[primary_term]],
                )
            ],
            errors=[
                ErrorSpec(
                    id=err_id,
                    exception_name=f"{comp_slug.title().replace('_', '')}DomainError",
                    http_status=422,
                    problem_type_uri=f"https://errors.enterprise.internal/{comp_slug}/domain-error",
                    module_id=dom_mod_id,
                )
            ],
            config_keys=[f"CFG-{comp_idx:03d}"],
            depends_on=[],
            task_ids=comp.linked_task_ids,
            ac_ids=comp_acs,
            tags=["core_logic", "persistence"],
        )
        modules.append(dom_mod)
        ddl_files.append(f"migrations/00{comp_idx}_{comp_slug}_records.sql")

        # 2. API Adapter Module (Wave 1, depends on Domain Module)
        api_mod_id = f"MOD-{mod_seq:03d}"
        mod_seq += 1
        api_mod = ModuleSpec(
            id=api_mod_id,
            component_id=comp.id,
            path=f"services/{comp_slug}/api_routes.py",
            layer="api",
            responsibilities=[f"HTTP endpoint router and RFC 7807 error mapping for {comp.name}"],
            public_interface=[
                FunctionSpec(
                    name=f"handle_{comp_slug}_endpoint",
                    signature=f"def handle_{comp_slug}_endpoint(payload: dict) -> dict",
                    purpose=f"Expose HTTP endpoint for {comp.name} and delegate to {dom_mod_id}.",
                    input_dtos=[dto_in_id],
                    output_dto=dto_out_id,
                    raises=[err_id],
                    transaction_boundary="none",
                    resilience=ResiliencePolicy(timeout_ms=3000, idempotency_required=True),
                    telemetry=TelemetrySpec(span_name=f"http.post.{comp_slug}"),
                    max_cyclomatic=8,
                    ac_ids=comp_acs,
                )
            ],
            data_models=[],
            tables=[],
            errors=[],
            config_keys=[],
            depends_on=[dom_mod_id],
            task_ids=comp.linked_task_ids,
            ac_ids=comp_acs,
            tags=["api", "io"],
        )
        modules.append(api_mod)

    return LLDPack(
        lld_version="1.0.0",
        handoff_hash=handoff.content_hash(),
        modules=modules,
        api_contracts=api_contracts,
        ddl_files=ddl_files,
    )


def run_l1_lld(
    handoff: HLDHandoff,
    kg: SQLiteKnowledgeGraph,
    run_id: str = "run-2026-10-22-001",
) -> StageResult[LLDPack]:
    started = utc_now_iso()
    lld = synthesize_lld_from_handoff(handoff)
    violations = lld_violations(lld, handoff)
    if violations:
        raise ValueError("LLD validation failed: " + "; ".join(violations))

    ep = kg.load_lld(lld, run_id=run_id)
    finished = utc_now_iso()
    return StageResult[LLDPack](
        stage="L1_LLD",
        run_id=run_id,
        graph_epoch=ep,
        input_hash=handoff.content_hash(),
        model_id="lld-synthesizer-v1",
        payload=lld,
        validators_passed=[
            "lld_violations_empty",
            "hexagonal_layer_direction",
            "module_dependency_acyclicity",
            "dto_and_error_refs_resolved",
            "kg_lld_loaded",
        ],
        started_at=started,
        finished_at=finished,
    )
