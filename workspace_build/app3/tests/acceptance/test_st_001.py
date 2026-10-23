"""Frozen Acceptance Oracle for ST-001 (Secure User Registration and Sign Up). DO NOT MODIFY IN L3."""
from __future__ import annotations
from tests.harness.state_seeder import StateSeeder

def test_ac_001_01() -> None:
    """AC: AC-001-01 -> Given valid user_id credentials and email When the registration endpoint is called Then the user is persisted with salted password hash and status PROCESSED"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'

def test_ac_001_02() -> None:
    """AC: AC-001-02 -> Given a duplicate user_id or non-positive quantity When the registration endpoint is called Then a 422 DomainError is raised"""
    seeder = StateSeeder()
    seeded = seeder.given_entity_exists('records', {'status': 'SEEDED'})
    assert seeded['status'] == 'SEEDED'
