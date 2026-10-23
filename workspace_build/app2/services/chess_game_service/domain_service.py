"""Enterprise implementation for MOD-001 (Tasks: TSK-001, TSK-002; ACs: AC-001-01, AC-001-02)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
__all__ = ['ChessGameServiceDomainError', 'ChessGameServiceRequest', 'ChessGameServiceResponse', 'process_chess_game_service']

class ChessGameServiceDomainError(ValueError):
    """Domain Error ERR-001 (HTTP 422): https://errors.enterprise.internal/chess_game_service/domain-error."""

@dataclass(frozen=True)
class ChessGameServiceRequest:
    game_id: str
    quantity: int

@dataclass(frozen=True)
class ChessGameServiceResponse:
    record_id: str
    game_id: str
    quantity: int
    status: str

def process_chess_game_service(payload: ChessGameServiceRequest) -> ChessGameServiceResponse:
    """Validate business invariants and execute domain logic for chess-game-service. Implements AC-001-01, AC-001-02."""
    if payload.quantity <= 0:
        raise ChessGameServiceDomainError("quantity must be strictly positive")
    if not getattr(payload, 'game_id', '').strip():
        raise ChessGameServiceDomainError("game_id must be non-empty")
    return ChessGameServiceResponse(
        record_id=f"rec-{payload.game_id}",
        game_id=getattr(payload, 'game_id'),
        quantity=payload.quantity,
        status="PROCESSED",
    )
