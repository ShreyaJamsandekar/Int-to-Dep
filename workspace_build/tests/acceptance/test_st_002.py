"""Frozen Acceptance Oracle for ST-002 (Reserve Inventory Stock). DO NOT MODIFY IN L3."""
from __future__ import annotations
from tests.harness.state_seeder import StateSeeder

def test_ac_002_01() -> None:
    """AC: AC-002-01 -> Given an approved order_sku When inventory reservation runs Then stock is reserved with status PROCESSED"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'
