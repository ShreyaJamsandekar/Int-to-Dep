"""AST symbol extraction and sandbox code indexer for the Knowledge Graph."""
from __future__ import annotations

import ast
from pathlib import Path
from pipeline.contracts.lld import ModuleSpec
from pipeline.graph.sqlite_adapter import SQLiteKnowledgeGraph


def index_python_module_symbols(
    repo_root: Path,
    build_id: str,
    module_spec: ModuleSpec,
    kg: SQLiteKnowledgeGraph,
    run_id: str = "run-default",
) -> list[str]:
    """
    Parse a module's Python AST, extract public functions and classes, and register
    `CodeSymbol` nodes and `REALIZES` edges in the Knowledge Graph.
    """
    file_path = repo_root / module_spec.path
    if not file_path.is_file():
        return []

    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    fn_specs = {f.name: f"{module_spec.id}::{f.name}" for f in module_spec.public_interface}
    dto_specs = {d.name: d.id for d in module_spec.data_models}
    tbl_specs = {t.table_name: t.id for t in module_spec.tables}
    err_specs = {e.exception_name: e.id for e in module_spec.errors}

    explicit_all: set[str] | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        explicit_all = {
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        }

    indexed_ids: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            if explicit_all is not None:
                is_public = name in explicit_all
            else:
                is_public = not name.startswith("_")

            realizes_id = (
                fn_specs.get(name)
                or dto_specs.get(name)
                or err_specs.get(name)
                or tbl_specs.get(name.lower())
            )
            sym_id = f"SYM-{module_spec.id}-{name}"
            kg.register_code_symbol(
                symbol_id=sym_id,
                name=name,
                build_id=build_id,
                module_id=module_spec.id,
                public=is_public,
                realizes_id=realizes_id,
                run_id=run_id,
            )
            indexed_ids.append(sym_id)
    return indexed_ids
