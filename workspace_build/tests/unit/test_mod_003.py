"""Unit and property tests for MOD-003 (BLD-003)."""
from __future__ import annotations
import unittest
from services.inventory_service.domain_service import process_inventory_service, InventoryServiceRequest, InventoryServiceDomainError

def test_process_inventory_service_happy_path() -> None:
    res = process_inventory_service(InventoryServiceRequest(order_sku="SKU-100", quantity=3))
    assert res.status == "PROCESSED"
    assert res.quantity == 3

def test_process_inventory_service_rejects_non_positive_quantity() -> None:
    try:
        process_inventory_service(InventoryServiceRequest(order_sku="SKU-100", quantity=0))
        raise AssertionError('Expected domain error')
    except InventoryServiceDomainError:
        pass
