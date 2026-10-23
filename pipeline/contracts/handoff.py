"""Stage H0 HLD-to-LLD handoff contract (Pydantic v1 & v2 compatible)."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal
from pydantic import Field
from .base import (
    PYDANTIC_V2,
    Contract,
    regex_field,
    EpicId,
    StoryId,
    TaskId,
    ServiceId,
    NfrId,
    AdrId,
    AcId,
    ContractId,
    InvariantId,
)
from .graphutil import assert_acyclic

if PYDANTIC_V2:
    from pydantic import field_validator, model_validator
else:
    from pydantic import validator, root_validator  # type: ignore


class ArchitecturalStyle(str, Enum):
    BATCH_PROCESSING = "Batch Processing Pipeline"
    EVENT_DRIVEN = "Event-Driven Microservices"
    MODULAR_MONOLITH = "Modular Monolith (Layered)"
    CLIENT_SERVER_REST = "Client-Server RESTful Architecture"


class ServiceTier(str, Enum):
    API_GATEWAY = "API Gateway"
    APPLICATION_SERVICE = "Application Backend Service"
    STORAGE_DATABASE = "Storage / Database Service"
    MESSAGE_BROKER = "Messaging / Queue Service"
    BACKGROUND_WORKER = "Background Worker / Processing Job"


class DataClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED_PII = "restricted_pii"
    RESTRICTED_PCI = "restricted_pci"


def ac_id(story_id: str, seq: int) -> str:
    return f"AC-{int(story_id.split('-')[1]):03d}-{seq:02d}"


class DomainTerm(Contract):
    term: str = Field(min_length=2)
    canonical_snake: str = regex_field("^[a-z][a-z0-9_]*$")
    definition: str = Field(min_length=10)
    classification: DataClassification = DataClassification.INTERNAL


class BusinessInvariant(Contract):
    id: InvariantId
    statement: str = Field(min_length=15)
    applies_to_stories: list[StoryId] = Field(min_items=1) if not PYDANTIC_V2 else Field(min_length=1)


class AcceptanceCriterion(Contract):
    id: AcId
    gherkin: str

    if PYDANTIC_V2:
        @field_validator("gherkin")
        @classmethod
        def gwt(cls, v: str) -> str:
            if not all(k in v for k in ("Given", "When", "Then")):
                raise ValueError("criterion needs Given/When/Then")
            return v
    else:
        @validator("gherkin")
        def gwt(cls, v: str) -> str:
            if not all(k in v for k in ("Given", "When", "Then")):
                raise ValueError("criterion needs Given/When/Then")
            return v


def _min_list(n: int = 1) -> Any:
    return Field(min_length=n) if PYDANTIC_V2 else Field(min_items=n)


class StoryRef(Contract):
    story_id: StoryId
    epic_id: EpicId
    title: str = "Story"
    task_ids: list[TaskId] = _min_list(1)
    criteria: list[AcceptanceCriterion] = _min_list(1)
    source_anchor: str


class NonFunctionalRequirement(Contract):
    id: NfrId
    statement: str
    metric: str
    comparator: Literal["<=", ">=", "=="]
    threshold: float
    unit: str
    assumption: bool = False


class Component(Contract):
    id: ServiceId
    name: str = regex_field("^[a-z0-9-]+$")
    tier: ServiceTier
    responsibilities: list[str] = _min_list(1)
    technology_stack: str
    storage_type: str | None = None
    linked_task_ids: list[TaskId] = _min_list(1)
    satisfies_nfrs: list[NfrId] = []
    adr_ids: list[AdrId] = []
    architectural_reasoning: str = Field(min_length=20)


class Dependency(Contract):
    source: ServiceId
    target_component: ServiceId | None = None
    target_infra: str | None = None
    kind: Literal["runtime", "data", "build"]

    if PYDANTIC_V2:
        @model_validator(mode="after")
        def one_target(self):
            if (self.target_component is None) == (self.target_infra is None):
                raise ValueError("exactly one of target_component / target_infra")
            return self
    else:
        @root_validator
        def one_target(cls, values: dict[str, Any]) -> dict[str, Any]:
            if (values.get("target_component") is None) == (values.get("target_infra") is None):
                raise ValueError("exactly one of target_component / target_infra")
            return values


class Relationship(Contract):
    source: ServiceId
    target: ServiceId
    interaction: Literal["calls", "publishes", "subscribes", "reads", "writes"]
    protocol: Literal["http", "grpc", "amqp", "kafka", "sql", "file"]
    sync: bool
    contract_ref: ContractId | None = None


class TraceLink(Contract):
    from_id: str
    to_id: str
    relation: Literal["derives_from", "satisfies", "implements", "decided_by"]


class AdrSummary(Contract):
    id: AdrId
    level: Literal[0, 1, 2, 3]
    title: str
    decision: str
    status: Literal["proposed", "accepted", "superseded"]


def _validate_handoff_integrity(
    components: list[Component],
    stories: list[StoryRef],
    nfrs: list[NonFunctionalRequirement],
    dependencies: list[Dependency],
    relationships: list[Relationship],
    reasoning: str,
) -> None:
    errs: list[str] = []
    comp = {c.id for c in components}
    tasks = {t for s in stories for t in s.task_ids}
    nfr_ids = {n.id for n in nfrs}
    cited = {t for c in components for t in c.linked_task_ids}
    satisfied = {n for c in components for n in c.satisfies_nfrs}
    if len(comp) != len(components):
        errs.append("duplicate component ids")
    errs += [f"component cites unknown task {t}" for t in sorted(cited - tasks)]
    errs += [f"task without component {t}" for t in sorted(tasks - cited)]
    errs += [f"component cites unknown NFR {n}" for n in sorted(satisfied - nfr_ids)]
    errs += [f"NFR without component {n}" for n in sorted(nfr_ids - satisfied)]
    errs += [
        f"dangling dependency from {d.source}"
        for d in dependencies
        if d.source not in comp or (d.target_component and d.target_component not in comp)
    ]
    errs += [
        f"dangling relationship {r.source}->{r.target}"
        for r in relationships
        if r.source not in comp or r.target not in comp
    ]
    if not re.search("(NFR|ST)-[0-9]{3,5}", reasoning):
        errs.append("architecture reasoning must cite at least one NFR or story id")
    try:
        assert_acyclic([
            (d.source, d.target_component)
            for d in dependencies
            if d.kind == "runtime" and d.target_component
        ])
    except ValueError as e:
        errs.append(f"runtime {e}")
    if errs:
        raise ValueError("; ".join(errs))


class HLDHandoff(Contract):
    handoff_version: str = regex_field("^[0-9]+\.[0-9]+\.[0-9]+$")
    handoff_id: str
    source_run_id: str
    prd_sha256: str = regex_field("^[0-9a-f]{64}$")
    selected_architecture: ArchitecturalStyle
    architecture_selection_reasoning: str = Field(min_length=30)
    target_platform: Literal["kubernetes_k3s", "docker_compose", "cloud_vm_onprem"]
    stories: list[StoryRef] = _min_list(1)
    nfrs: list[NonFunctionalRequirement] = []
    components: list[Component] = _min_list(1)
    dependencies: list[Dependency] = []
    relationships: list[Relationship] = []
    traceability: list[TraceLink] = []
    adrs: list[AdrSummary] = []
    shared_infrastructure: list[str] = []
    domain_glossary: list[DomainTerm] = []
    business_invariants: list[BusinessInvariant] = []

    if PYDANTIC_V2:
        @model_validator(mode="after")
        def integrity(self):
            _validate_handoff_integrity(
                self.components,
                self.stories,
                self.nfrs,
                self.dependencies,
                self.relationships,
                self.architecture_selection_reasoning,
            )
            return self
    else:
        @root_validator
        def integrity(cls, values: dict[str, Any]) -> dict[str, Any]:
            if "components" in values and "stories" in values:
                _validate_handoff_integrity(
                    values.get("components", []),
                    values.get("stories", []),
                    values.get("nfrs", []),
                    values.get("dependencies", []),
                    values.get("relationships", []),
                    values.get("architecture_selection_reasoning", ""),
                )
            return values
