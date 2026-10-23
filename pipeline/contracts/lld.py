"""Stage L1 Low-Level Design (LLD) contracts and closed-loop replan patch types."""
from __future__ import annotations

from typing import Literal
from pydantic import Field
from .base import (
    Contract,
    regex_field,
    ServiceId,
    TaskId,
    AcId,
    ModuleId,
    ContractId,
    DtoId,
    TableId,
    ErrorId,
    SecId,
    ConfigId,
)
from .graphutil import assert_acyclic
from .handoff import HLDHandoff, DataClassification, _min_list


class FieldSpec(Contract):
    name: str = regex_field("^[a-z][a-z0-9_]*$")
    type_annotation: str
    required: bool = True
    constraints: str | None = None
    classification: DataClassification = DataClassification.INTERNAL


class DataModelSpec(Contract):
    id: DtoId
    name: str = regex_field("^[A-Z][A-Za-z0-9]+$")
    module_id: ModuleId
    fields: list[FieldSpec] = _min_list(1)
    validators: list[str] = []


class TableSpec(Contract):
    id: TableId
    table_name: str = regex_field("^[a-z][a-z0-9_]*$")
    owner_component_id: ServiceId
    module_id: ModuleId
    primary_key: list[str] = _min_list(1)
    columns: list[FieldSpec] = _min_list(1)
    foreign_keys: list[str] = []
    indexes: list[list[str]] = []


class ErrorSpec(Contract):
    id: ErrorId
    exception_name: str = regex_field("^[A-Z][A-Za-z0-9]+Error$")
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
    name: str = regex_field("^[a-z_][a-z0-9_]*$")
    signature: str
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
    path: str
    layer: Literal["domain", "application", "adapters", "api", "worker", "config"] = "domain"
    responsibilities: list[str] = _min_list(1)
    public_interface: list[FunctionSpec] = _min_list(1)
    data_models: list[DataModelSpec] = []
    tables: list[TableSpec] = []
    errors: list[ErrorSpec] = []
    config_keys: list[ConfigId] = []
    depends_on: list[ModuleId] = []
    task_ids: list[TaskId] = _min_list(1)
    ac_ids: list[AcId] = _min_list(1)
    tags: list[Literal["core_logic", "io", "persistence", "api", "worker"]] = []


class ApiContract(Contract):
    id: ContractId
    kind: Literal["openapi", "asyncapi"]
    path: str
    sha256: str
    auth_scopes: list[SecId] = []


class LLDDefectTicket(Contract):
    ticket_id: str
    module_id: ModuleId
    reason: Literal["replan_lld", "split_task"]
    failed_ac_ids: list[AcId] = []
    verification_errors: list[str] = []
    open_finding_summaries: list[str] = []


class LLDPatch(Contract):
    target_lld_version: str
    new_lld_version: str
    defect_ticket_id: str
    replaced_modules: list[ModuleSpec] = _min_list(1)
    removed_module_ids: list[ModuleId] = []
    rationale: str = Field(min_length=15)


class LLDPack(Contract):
    lld_version: str
    handoff_hash: str
    modules: list[ModuleSpec] = _min_list(1)
    api_contracts: list[ApiContract] = []
    ddl_files: list[str] = []


LAYER_ALLOWED_DEPS: dict[str, set[str]] = {
    "domain": {"domain"},
    "application": {"domain", "application", "config"},
    "adapters": {"domain", "application", "adapters", "config"},
    "api": {"domain", "application", "adapters", "api", "config"},
    "worker": {"domain", "application", "adapters", "worker", "config"},
    "config": {"config"},
}


def lld_violations(lld: LLDPack, h: HLDHandoff) -> list[str]:
    v: list[str] = []
    if lld.handoff_hash != h.content_hash():
        v.append("handoff_hash mismatch")
    comps = {c.id for c in h.components}
    tasks = {t for s in h.stories for t in s.task_ids}
    acs = {a.id for s in h.stories for a in s.criteria}
    mods = {m.id: m for m in lld.modules}
    if len(mods) != len(lld.modules):
        v.append("duplicate module ids")

    done_tasks = {t for m in lld.modules for t in m.task_ids}
    done_acs = {a for m in lld.modules for a in m.ac_ids}
    all_dtos = {d.id for m in lld.modules for d in m.data_models}
    all_errs = {e.id for m in lld.modules for e in m.errors}

    v += [f"{m.id}: unknown component {m.component_id}" for m in lld.modules if m.component_id not in comps]
    v += [f"{m.id}: unknown dependency {d}" for m in lld.modules for d in m.depends_on if d not in mods]
    v += [f"task not implemented: {t}" for t in sorted(tasks - done_tasks)]
    v += [f"unknown task: {t}" for t in sorted(done_tasks - tasks)]
    v += [f"AC not covered: {a}" for a in sorted(acs - done_acs)]
    v += [f"unknown AC: {a}" for a in sorted(done_acs - acs)]

    for m in lld.modules:
        for dep_id in m.depends_on:
            if dep_id in mods:
                dep_layer = mods[dep_id].layer
                if dep_layer not in LAYER_ALLOWED_DEPS.get(m.layer, set()):
                    v.append(f"{m.id} ({m.layer}) cannot depend on {dep_id} ({dep_layer})")
        for fn in m.public_interface:
            for dto_id in fn.input_dtos:
                if dto_id not in all_dtos:
                    v.append(f"{m.id}.{fn.name}: unknown input DTO {dto_id}")
            if fn.output_dto and fn.output_dto not in all_dtos:
                v.append(f"{m.id}.{fn.name}: unknown output DTO {fn.output_dto}")
            for err_id in fn.raises:
                if err_id not in all_errs:
                    v.append(f"{m.id}.{fn.name}: unknown error spec {err_id}")

    have = {c.id for c in lld.api_contracts}
    v += [
        f"missing contract {r.contract_ref}"
        for r in h.relationships
        if r.contract_ref and r.contract_ref not in have
    ]
    try:
        assert_acyclic([(m.id, d) for m in lld.modules for d in m.depends_on])
    except ValueError as e:
        v.append(f"module {e}")
    return v


def apply_lld_patch(lld: LLDPack, patch: LLDPatch) -> LLDPack:
    if lld.lld_version != patch.target_lld_version:
        raise ValueError(f"patch version mismatch: {patch.target_lld_version} != {lld.lld_version}")
    removed = set(patch.removed_module_ids) | {m.id for m in patch.replaced_modules}
    kept = [m for m in lld.modules if m.id not in removed]
    new_modules = kept + list(patch.replaced_modules)
    return LLDPack(
        lld_version=patch.new_lld_version,
        handoff_hash=lld.handoff_hash,
        modules=new_modules,
        api_contracts=lld.api_contracts,
        ddl_files=lld.ddl_files,
    )
