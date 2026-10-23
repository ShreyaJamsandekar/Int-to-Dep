"""Stage L3 BuildTask and TaskGraph contracts with wave computation."""
from __future__ import annotations

from typing import Any
from pydantic import Field
from .base import PYDANTIC_V2, Contract, BuildId, ModuleId, ContractId, TaskId, AcId
from .handoff import _min_list
from .graphutil import assert_acyclic, topological_waves

if PYDANTIC_V2:
    from pydantic import model_validator
else:
    from pydantic import root_validator  # type: ignore


class BuildTask(Contract):
    id: BuildId
    module_id: ModuleId
    files_owned: list[str] = _min_list(1)
    contract_ids: list[ContractId] = []
    depends_on: list[BuildId] = []
    task_ids: list[TaskId] = _min_list(1)
    ac_ids: list[AcId] = _min_list(1)
    token_budget: int = Field(default=24000, ge=4000)


def _validate_tasks(tasks: list[BuildTask]) -> None:
    errs: list[str] = []
    owners: dict[str, str] = {}
    for t in tasks:
        for f in t.files_owned:
            if f in owners:
                errs.append(f"{f} owned by {owners[f]} and {t.id}")
            owners[f] = t.id
    ids = {t.id for t in tasks}
    if len(ids) != len(tasks):
        errs.append("duplicate build task ids")
    errs += [
        f"{t.id}: unknown dependency {d}"
        for t in tasks
        for d in t.depends_on
        if d not in ids
    ]
    try:
        assert_acyclic([(t.id, d) for t in tasks for d in t.depends_on])
    except ValueError as e:
        errs.append(f"task {e}")
    if errs:
        raise ValueError("; ".join(errs))


class TaskGraph(Contract):
    tasks: list[BuildTask] = _min_list(1)

    if PYDANTIC_V2:
        @model_validator(mode="after")
        def valid(self):
            _validate_tasks(self.tasks)
            return self
    else:
        @root_validator
        def valid(cls, values: dict[str, Any]) -> dict[str, Any]:
            if "tasks" in values:
                _validate_tasks(values["tasks"])
            return values

    def execution_waves(self) -> list[list[str]]:
        nodes = {t.id for t in self.tasks}
        edges = [(t.id, d) for t in self.tasks for d in t.depends_on]
        return topological_waves(nodes, edges)
