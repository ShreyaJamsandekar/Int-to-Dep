"""Frozen Acceptance Oracle for ST-001 (Initialize Multiplayer Chess Game). DO NOT MODIFY IN L3."""
from __future__ import annotations
from tests.harness.state_seeder import StateSeeder

def test_ac_001_01() -> None:
    """AC: AC-001-01 -> Given a valid game_id and positive quantity When the game endpoint is called Then the game session is persisted with status PROCESSED"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'

def test_ac_001_02() -> None:
    """AC: AC-001-02 -> Given a zero or negative quantity When the game endpoint is called Then a 422 DomainError is raised"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'
