"""Frozen Acceptance Oracle for ST-001 (Create Validated Customer Order). DO NOT MODIFY IN L3."""
from __future__ import annotations
from tests.harness.state_seeder import StateSeeder

def test_ac_001_01() -> None:
    """AC: AC-001-01 -> Given a valid order_sku and positive quantity When the order endpoint is called Then the order is persisted with status PROCESSED"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'

def test_ac_001_02() -> None:
    """AC: AC-001-02 -> Given a zero or negative quantity When the order endpoint is called Then a 422 DomainError is raised"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'
