# Enterprise Runbook — HND-ORDER-INVENTORY-001

- Health Probe: `GET /healthz`
- Readiness Probe: `GET /readyz`
- Rollback Command: `alembic downgrade -1 && helm rollback release-sandbox`
