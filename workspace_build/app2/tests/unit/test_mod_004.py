"""Unit tests for API router module MOD-004 (BLD-004)."""
from __future__ import annotations
from services.chess_engine_service.api_routes import handle_chess_engine_service_endpoint

def test_handle_chess_engine_service_endpoint_endpoint() -> None:
    out = handle_chess_engine_service_endpoint({"game_id": "SKU-200", "quantity": 5})
    assert out["status"] == "PROCESSED"
    assert out["quantity"] == 5
