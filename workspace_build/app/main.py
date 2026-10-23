# Enterprise service entrypoint with health/readiness probes and RFC 7807 error formatting.
from __future__ import annotations
from typing import Any
from app.api.router_registry import load_registered_handlers
from app.db.model_registry import REGISTERED_TABLES
def healthz() -> dict[str, str]:
    return {'status': 'ok'}
def readyz() -> dict[str, Any]:
    return {'status': 'ready', 'tables_registered': len(REGISTERED_TABLES)}
def problem_details(status: int, title: str, detail: str, type_uri: str = 'about:blank') -> dict[str, Any]:
    return {'type': type_uri, 'title': title, 'status': status, 'detail': detail}
def dispatch_request(endpoint_name: str, payload: dict[str, Any], traceparent: str = '00-default-01') -> dict[str, Any]:
    handlers = load_registered_handlers()
    if endpoint_name not in handlers:
        return problem_details(404, 'Not Found', f'Endpoint {endpoint_name} not registered')
    try:
        res = handlers[endpoint_name](payload)
        return {'status': 200, 'traceparent': traceparent, 'data': res}
    except Exception as exc:
        return problem_details(422, exc.__class__.__name__, str(exc))

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, HTMLResponse
    from app.ui import DASHBOARD_HTML

    app = FastAPI(
        title='HLD-to-Deployable-Code Enterprise Service',
        description='Autonomous Enterprise Microservices generated from High-Level Design',
        version='1.0.0',
        docs_url='/docs',
        redoc_url='/redoc',
    )

    @app.get('/', response_class=HTMLResponse)
    def index():
        return HTMLResponse(content=DASHBOARD_HTML, status_code=200)

    @app.get('/healthz')
    def api_healthz():
        return healthz()

    @app.get('/readyz')
    def api_readyz():
        return readyz()

    @app.post('/api/order')
    async def api_order_post(request: Request):
        payload = await request.json()
        res = dispatch_request('handle_order_service_endpoint', payload)
        return JSONResponse(status_code=res.get('status', 200), content=res)

    @app.get('/api/order')
    def api_order_get():
        return {
            'endpoint': 'POST /api/order or /api/handle_order_service_endpoint',
            'sample_payload': {'order_sku': 'SKU-LAPTOP-X1', 'quantity': 2},
            'web_ui': 'Visit http://localhost:8000 for interactive testing',
        }

    @app.post('/api/inventory')
    async def api_inventory_post(request: Request):
        payload = await request.json()
        res = dispatch_request('handle_inventory_service_endpoint', payload)
        return JSONResponse(status_code=res.get('status', 200), content=res)

    @app.get('/api/inventory')
    def api_inventory_get():
        return {
            'endpoint': 'POST /api/inventory or /api/handle_inventory_service_endpoint',
            'sample_payload': {'order_sku': 'INV-CHIP-99', 'quantity': 50},
            'web_ui': 'Visit http://localhost:8000 for interactive testing',
        }

    @app.api_route('/api/{endpoint_name}', methods=['GET', 'POST'])
    async def api_dispatch(endpoint_name: str, request: Request):
        if request.method == 'GET':
            return {
                'endpoint': f'/api/{endpoint_name}',
                'method': 'POST required for execution',
                'sample': {'order_sku': 'SKU-100', 'quantity': 2},
            }
        payload = await request.json()
        res = dispatch_request(endpoint_name, payload)
        status_code = res.get('status', 200)
        return JSONResponse(status_code=status_code, content=res)
except ImportError:
    app = None

