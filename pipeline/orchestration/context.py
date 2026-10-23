"""Budgeted Knowledge Graph context slice assembly and single-file package splitting."""
from __future__ import annotations

from dataclasses import dataclass
from pipeline.contracts.handoff import HLDHandoff
from pipeline.contracts.lld import LLDPack, ModuleSpec, LLDPatch
from pipeline.contracts.tasks import BuildTask
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


@dataclass
class ContextPacket:
    build_id: str
    module_id: str
    base_graph_epoch: int
    token_estimate: int
    token_budget: int
    within_budget: bool
    p0_contracts_and_acs: dict[str, object]
    p1_dependency_stubs_and_glossary: dict[str, object]
    p2_adrs_and_risk_patterns: dict[str, object]
    p3_neighbor_files: list[str]


def estimate_tokens(text: str) -> int:
    """Deterministic ~4 chars per token estimator."""
    return max(1, len(text) // 4)


def build_context_packet(
    task: BuildTask,
    handoff: HLDHandoff,
    lld: LLDPack,
    kg: SQLiteKnowledgeGraph,
) -> ContextPacket:
    mod_map = {m.id: m for m in lld.modules}
    mod = mod_map[task.module_id]
    ac_map = {a.id: a.dump_json_dict() for s in handoff.stories for a in s.criteria}
    con_map = {c.id: c.dump_json_dict() for c in lld.api_contracts}

    p0 = {
        "module_spec": mod.dump_json_dict(),
        "acceptance_criteria": [ac_map[a] for a in task.ac_ids if a in ac_map],
        "api_contracts": [con_map[c] for c in task.contract_ids if c in con_map],
        "business_invariants": [i.dump_json_dict() for i in handoff.business_invariants],
    }
    dep_stubs = {
        dep_id: [fn.signature for fn in mod_map[dep_id].public_interface]
        for dep_id in mod.depends_on
        if dep_id in mod_map
    }
    p1 = {
        "dependency_signatures": dep_stubs,
        "domain_glossary": [t.dump_json_dict() for t in handoff.domain_glossary],
    }
    p2 = {
        "adrs": [a.dump_json_dict() for a in handoff.adrs],
        "risk_patterns": [n["payload"] for n in kg.list_nodes("RiskPattern")],
    }
    p3 = kg.blast_radius_files(mod.id)

    p0_p1_tokens = estimate_tokens(str(p0) + str(p1))
    total_tokens = p0_p1_tokens + estimate_tokens(str(p2)) + estimate_tokens(str(p3))

    if total_tokens > task.token_budget:
        p3 = []
        total_tokens = p0_p1_tokens + estimate_tokens(str(p2))
    if total_tokens > task.token_budget:
        p2 = {"adrs": [], "risk_patterns": []}
        total_tokens = p0_p1_tokens

    return ContextPacket(
        build_id=task.id,
        module_id=mod.id,
        base_graph_epoch=kg.epoch,
        token_estimate=total_tokens,
        token_budget=task.token_budget,
        within_budget=p0_p1_tokens <= task.token_budget,
        p0_contracts_and_acs=p0,
        p1_dependency_stubs_and_glossary=p1,
        p2_adrs_and_risk_patterns=p2,
        p3_neighbor_files=p3,
    )


def split_module_into_submodules(lld: LLDPack, module_id: str, ticket_id: str = "TKT-SPLIT") -> LLDPatch:
    """
    Deterministically split a multi-function single-file ModuleSpec into two disjoint
    submodule files so parallel `BuildTask`s never share ownership of the same file (fixes GAP-09).
    """
    mod = next(m for m in lld.modules if m.id == module_id)
    funcs = mod.public_interface
    mid_idx = max(1, len(funcs) // 2)
    funcs_a = funcs[:mid_idx]
    funcs_b = funcs[mid_idx:] or funcs[:1]

    acs_a = sorted({a for f in funcs_a for a in f.ac_ids}) or [mod.ac_ids[0]]
    acs_b = sorted({a for f in funcs_b for a in f.ac_ids}) or [mod.ac_ids[-1]]

    base_num = int(mod.id.split("-")[1])
    id_a = f"MOD-{base_num * 10 + 1:03d}"
    id_b = f"MOD-{base_num * 10 + 2:03d}"
    stem = mod.path[:-3] if mod.path.endswith(".py") else mod.path

    mod_a = ModuleSpec(
        id=id_a,
        component_id=mod.component_id,
        path=f"{stem}_part1.py",
        layer=mod.layer,
        responsibilities=mod.responsibilities[:1],
        public_interface=funcs_a,
        data_models=[d.copy_with(update={"module_id": id_a}) for d in mod.data_models],
        tables=[t.copy_with(update={"module_id": id_a}) for t in mod.tables],
        errors=[e.copy_with(update={"module_id": id_a}) for e in mod.errors],
        config_keys=mod.config_keys,
        depends_on=mod.depends_on,
        task_ids=mod.task_ids,
        ac_ids=acs_a,
        tags=mod.tags,
    )
    mod_b = ModuleSpec(
        id=id_b,
        component_id=mod.component_id,
        path=f"{stem}_part2.py",
        layer=mod.layer,
        responsibilities=mod.responsibilities[-1:],
        public_interface=funcs_b,
        data_models=[],
        tables=[],
        errors=[],
        config_keys=[],
        depends_on=[*mod.depends_on, id_a],
        task_ids=mod.task_ids,
        ac_ids=acs_b,
        tags=mod.tags,
    )

    parts = [int(x) for x in lld.lld_version.split(".")]
    new_ver = f"{parts[0]}.{parts[1]}.{parts[2] + 1}"
    return LLDPatch(
        target_lld_version=lld.lld_version,
        new_lld_version=new_ver,
        defect_ticket_id=ticket_id,
        replaced_modules=[
            mod_a,
            mod_b,
            *[
                m.copy_with(
                    {
                        "depends_on": [
                            x
                            for d in m.depends_on
                            for x in ([id_a, id_b] if d == mod.id else [d])
                        ]
                    }
                )
                for m in lld.modules
                if mod.id in m.depends_on
            ],
        ],
        removed_module_ids=[mod.id],
        rationale=f"Split module {mod.id} into {id_a} and {id_b} with disjoint file ownership.",
    )
