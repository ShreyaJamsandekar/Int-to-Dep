"""Enterprise implementation for MOD-002 (Tasks: TSK-001, TSK-002; ACs: AC-001-01, AC-001-02)."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
__all__ = ['handle_order_service_endpoint']
from services.order_service.domain_service import process_order_service, OrderServiceRequest, OrderServiceResponse, OrderServiceDomainError

def handle_order_service_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Expose HTTP endpoint for order-service and delegate to MOD-001. Implements AC-001-01, AC-001-02."""
    req = OrderServiceRequest(
        order_sku=str(payload.get("order_sku", "")),
        quantity=int(payload.get("quantity", 0)),
    )
    res = process_order_service(req)
    return asdict(res)
