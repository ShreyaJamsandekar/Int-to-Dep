"""Unit tests for API router module MOD-004 (BLD-004)."""
from __future__ import annotations
from services.inventory_service.api_routes import handle_inventory_service_endpoint

def test_handle_inventory_service_endpoint_endpoint() -> None:
    out = handle_inventory_service_endpoint({"order_sku": "SKU-200", "quantity": 5})
    assert out["status"] == "PROCESSED"
    assert out["quantity"] == 5
