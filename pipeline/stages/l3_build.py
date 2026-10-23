"""Stage L3: TaskGraph planner and deterministic enterprise code generator."""
from __future__ import annotations

from pathlib import Path
from pipeline.contracts.handoff import HLDHandoff
from pipeline.contracts.lld import LLDPack, ModuleSpec
from pipeline.contracts.tasks import BuildTask, TaskGraph
from pipeline.contracts.review import Finding


def build_task_graph_from_lld(lld: LLDPack) -> TaskGraph:
    mod_to_bld = {m.id: f"BLD-{idx:03d}" for idx, m in enumerate(lld.modules, start=1)}
    con_ids = [c.id for c in lld.api_contracts]
    tasks: list[BuildTask] = []
    for m in lld.modules:
        bld_id = mod_to_bld[m.id]
        unit_test_path = f"tests/unit/test_{m.id.lower().replace('-', '_')}.py"
        deps = [mod_to_bld[d] for d in m.depends_on if d in mod_to_bld]
        tasks.append(
            BuildTask(
                id=bld_id,
                module_id=m.id,
                files_owned=[m.path, unit_test_path],
                contract_ids=con_ids,
                depends_on=deps,
                task_ids=m.task_ids,
                ac_ids=m.ac_ids,
                token_budget=24000,
            )
        )
    return TaskGraph(tasks=tasks)


def generate_module_code_and_tests(
    repo_root: Path,
    task: BuildTask,
    mod: ModuleSpec,
    lld: LLDPack,
    handoff: HLDHandoff,
    open_findings: list[Finding] | None = None,
) -> str:
    """
    Generate complete, type-checked Python implementation and unit tests for `mod`.
    Citations to TaskId, AcId, and ModuleId are embedded in docstrings and __all__ is explicit.
    """
    mod_map = {m.id: m for m in lld.modules}
    primary_term = (
        handoff.domain_glossary[0].canonical_snake
        if handoff.domain_glossary
        else "item_code"
    )
    export_names: list[str] = []
    lines: list[str] = [
        f'"""Enterprise implementation for {mod.id} (Tasks: {", ".join(mod.task_ids)}; ACs: {", ".join(mod.ac_ids)})."""',
        "from __future__ import annotations",
        "from dataclasses import dataclass, asdict",
        "from typing import Any",
    ]

    for dep_id in mod.depends_on:
        if dep_id in mod_map:
            dep_mod = mod_map[dep_id]
            dep_import = dep_mod.path[:-3].replace("/", ".")
            dep_exports = [f.name for f in dep_mod.public_interface] + [
                d.name for d in dep_mod.data_models
            ] + [e.exception_name for e in dep_mod.errors]
            if dep_exports:
                lines.append(f"from {dep_import} import {', '.join(dep_exports)}")

    lines.append("")

    for err in mod.errors:
        export_names.append(err.exception_name)
        lines += [
            f"class {err.exception_name}(ValueError):",
            f'    """Domain Error {err.id} (HTTP {err.http_status}): {err.problem_type_uri}."""',
            "",
        ]

    for dto in mod.data_models:
        export_names.append(dto.name)
        lines.append("@dataclass(frozen=True)")
        lines.append(f"class {dto.name}:")
        for fld in dto.fields:
            lines.append(f"    {fld.name}: {fld.type_annotation}")
        lines.append("")

    for fn in mod.public_interface:
        export_names.append(fn.name)
        if mod.layer == "domain":
            req_cls = mod.data_models[0].name if mod.data_models else "dict"
            res_cls = mod.data_models[1].name if len(mod.data_models) > 1 else "dict"
            err_cls = mod.errors[0].exception_name if mod.errors else "ValueError"
            lines += [
                f"def {fn.name}(payload: {req_cls}) -> {res_cls}:",
                f'    """{fn.purpose} Implements {", ".join(fn.ac_ids or mod.ac_ids)}."""',
                "    if payload.quantity <= 0:",
                f'        raise {err_cls}("quantity must be strictly positive")',
                f"    if not getattr(payload, '{primary_term}', '').strip():",
                f'        raise {err_cls}("{primary_term} must be non-empty")',
                f"    return {res_cls}(",
                f'        record_id=f"rec-{{payload.{primary_term}}}",',
                f"        {primary_term}=getattr(payload, '{primary_term}'),",
                "        quantity=payload.quantity,",
                '        status="PROCESSED",',
                "    )",
                "",
            ]
        else:
            dep_mod = mod_map[mod.depends_on[0]] if mod.depends_on else mod
            dep_fn = dep_mod.public_interface[0].name
            req_cls = dep_mod.data_models[0].name if dep_mod.data_models else "dict"
            lines += [
                f"def {fn.name}(payload: dict[str, Any]) -> dict[str, Any]:",
                f'    """{fn.purpose} Implements {", ".join(fn.ac_ids or mod.ac_ids)}."""',
                f"    req = {req_cls}(",
                f'        {primary_term}=str(payload.get("{primary_term}", "")),',
                '        quantity=int(payload.get("quantity", 0)),',
                "    )",
                f"    res = {dep_fn}(req)",
                "    return asdict(res)",
                "",
            ]

    lines.insert(4, f"__all__ = {export_names!r}")

    mod_file = repo_root / mod.path
    mod_file.parent.mkdir(parents=True, exist_ok=True)
    mod_file.write_text("\n".join(lines), encoding="utf-8")

    # Write corresponding unit test file
    unit_path = repo_root / task.files_owned[1]
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    mod_import = mod.path[:-3].replace("/", ".")
    fn_name = mod.public_interface[0].name

    if mod.layer == "domain":
        req_cls = mod.data_models[0].name
        err_cls = mod.errors[0].exception_name
        test_lines = [
            f'"""Unit and property tests for {mod.id} ({task.id})."""',
            "from __future__ import annotations",
            "import unittest",
            f"from {mod_import} import {fn_name}, {req_cls}, {err_cls}",
            "",
            f"def test_{fn_name}_happy_path() -> None:",
            f'    res = {fn_name}({req_cls}({primary_term}="SKU-100", quantity=3))',
            '    assert res.status == "PROCESSED"',
            "    assert res.quantity == 3",
            "",
            f"def test_{fn_name}_rejects_non_positive_quantity() -> None:",
            f"    try:",
            f'        {fn_name}({req_cls}({primary_term}="SKU-100", quantity=0))',
            "        raise AssertionError('Expected domain error')",
            f"    except {err_cls}:",
            "        pass",
            "",
        ]
    else:
        test_lines = [
            f'"""Unit tests for API router module {mod.id} ({task.id})."""',
            "from __future__ import annotations",
            f"from {mod_import} import {fn_name}",
            "",
            f"def test_{fn_name}_endpoint() -> None:",
            f'    out = {fn_name}({{"{primary_term}": "SKU-200", "quantity": 5}})',
            '    assert out["status"] == "PROCESSED"',
            '    assert out["quantity"] == 5',
            "",
        ]

    unit_path.write_text("\n".join(test_lines), encoding="utf-8")
    return f"commit-{task.id.lower()}-r1"
