"""Unit tests for API router module MOD-002 (BLD-002)."""
from __future__ import annotations
from services.user_registration_service.api_routes import handle_user_registration_service_endpoint

def test_handle_user_registration_service_endpoint_endpoint() -> None:
    out = handle_user_registration_service_endpoint({"user_id": "SKU-200", "quantity": 5})
    assert out["status"] == "PROCESSED"
    assert out["quantity"] == 5
