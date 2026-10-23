"""Enterprise implementation for MOD-002 (Tasks: TSK-001, TSK-002; ACs: AC-001-01, AC-001-02)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
__all__ = ['handle_user_registration_service_endpoint']
from services.user_registration_service.domain_service import process_user_registration_service, UserRegistrationServiceRequest, UserRegistrationServiceResponse, UserRegistrationServiceDomainError

def handle_user_registration_service_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose HTTP endpoint for user-registration-service and delegate to MOD-001. Implements AC-001-01, AC-001-02."""
    req = UserRegistrationServiceRequest(
        user_id=str(payload.get("user_id", "")),
        quantity=int(payload.get("quantity", 0)),
    )
    res = process_user_registration_service(req)
    return asdict(res)
