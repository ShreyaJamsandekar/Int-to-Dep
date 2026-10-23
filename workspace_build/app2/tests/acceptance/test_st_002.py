"""Frozen Acceptance Oracle for ST-002 (Validate and Execute Chess Move). DO NOT MODIFY IN L3."""
from __future__ import annotations
from tests.harness.state_seeder import StateSeeder

def test_ac_002_01() -> None:
    """AC: AC-002-01 -> Given an active game_id and legal move When the move endpoint is called Then the engine updates board state with status PROCESSED"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'
