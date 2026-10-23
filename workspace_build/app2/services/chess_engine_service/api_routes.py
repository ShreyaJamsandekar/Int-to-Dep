"""Enterprise implementation for MOD-004 (Tasks: TSK-003; ACs: AC-002-01)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
__all__ = ['handle_chess_engine_service_endpoint']
from services.chess_engine_service.domain_service import process_chess_engine_service, ChessEngineServiceRequest, ChessEngineServiceResponse, ChessEngineServiceDomainError

def handle_chess_engine_service_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose HTTP endpoint for chess-engine-service and delegate to MOD-003. Implements AC-002-01."""
    req = ChessEngineServiceRequest(
        game_id=str(payload.get("game_id", "")),
        quantity=int(payload.get("quantity", 0)),
    )
    res = process_chess_engine_service(req)
    return asdict(res)
