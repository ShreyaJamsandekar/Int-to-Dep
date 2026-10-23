"""Unit and property tests for MOD-001 (BLD-001)."""
from __future__ import annotations
import unittest
from services.chess_game_service.domain_service import process_chess_game_service, ChessGameServiceRequest, ChessGameServiceDomainError

def test_process_chess_game_service_happy_path() -> None:
    res = process_chess_game_service(ChessGameServiceRequest(game_id="SKU-100", quantity=3))
    assert res.status == "PROCESSED"
    assert res.quantity == 3

def test_process_chess_game_service_rejects_non_positive_quantity() -> None:
    try:
        process_chess_game_service(ChessGameServiceRequest(game_id="SKU-100", quantity=0))
        raise AssertionError('Expected domain error')
    except ChessGameServiceDomainError:
        pass
