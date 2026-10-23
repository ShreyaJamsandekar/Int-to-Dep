"""Unit tests for API router module MOD-002 (BLD-002)."""
from __future__ import annotations
from services.order_service.api_routes import handle_order_service_endpoint

def test_handle_order_service_endpoint_endpoint() -> None:
    out = handle_order_service_endpoint({"order_sku": "SKU-200", "quantity": 5})
    assert out["status"] == "PROCESSED"
    assert out["quantity"] == 5
