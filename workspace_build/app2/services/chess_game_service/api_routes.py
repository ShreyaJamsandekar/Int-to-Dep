"""Enterprise implementation for MOD-002 (Tasks: TSK-001, TSK-002; ACs: AC-001-01, AC-001-02)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
__all__ = ['handle_chess_game_service_endpoint']
from services.chess_game_service.domain_service import process_chess_game_service, ChessGameServiceRequest, ChessGameServiceResponse, ChessGameServiceDomainError

def handle_chess_game_service_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose HTTP endpoint for chess-game-service and delegate to MOD-001. Implements AC-001-01, AC-001-02."""
    req = ChessGameServiceRequest(
        game_id=str(payload.get("game_id", "")),
        quantity=int(payload.get("quantity", 0)),
    )
    res = process_chess_game_service(req)
    return asdict(res)
