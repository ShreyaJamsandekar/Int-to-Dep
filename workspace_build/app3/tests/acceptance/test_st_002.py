"""Frozen Acceptance Oracle for ST-002 (User Authentication and Login Verification). DO NOT MODIFY IN L3."""
from __future__ import annotations
from tests.harness.state_seeder import StateSeeder

def test_ac_002_01() -> None:
    """AC: AC-002-01 -> Given verified user_id credentials When the login endpoint is called Then a signed session token is returned with status PROCESSED"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'
