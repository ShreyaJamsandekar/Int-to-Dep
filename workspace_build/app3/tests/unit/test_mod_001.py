"""Unit and property tests for MOD-001 (BLD-001)."""
from __future__ import annotations
import unittest
from services.user_registration_service.domain_service import process_user_registration_service, UserRegistrationServiceRequest, UserRegistrationServiceDomainError

def test_process_user_registration_service_happy_path() -> None:
    res = process_user_registration_service(UserRegistrationServiceRequest(user_id="SKU-100", quantity=3))
    assert res.status == "PROCESSED"
    assert res.quantity == 3

def test_process_user_registration_service_rejects_non_positive_quantity() -> None:
    try:
        process_user_registration_service(UserRegistrationServiceRequest(user_id="SKU-100", quantity=0))
        raise AssertionError('Expected domain error')
    except UserRegistrationServiceDomainError:
        pass
