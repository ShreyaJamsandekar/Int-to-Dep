# Deterministic state seeding harness for black-box acceptance tests.
from __future__ import annotations
from typing import Any
class StateSeeder:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}
    def given_entity_exists(self, table_name: str, record: dict[str, Any]) -> dict[str, Any]:
        self._store.setdefault(table_name, []).append(dict(record))
        return record
    def list_entities(self, table_name: str) -> list[dict[str, Any]]:
        return list(self._store.get(table_name, []))
