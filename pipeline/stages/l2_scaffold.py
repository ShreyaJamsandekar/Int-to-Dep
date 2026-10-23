"""Stage L2a: Deterministic Scaffold & Auto-Discovery Registry Generator."""
from __future__ import annotations

import json
from pathlib import Path
from pipeline.contracts.handoff import HLDHandoff
from pipeline.contracts.lld import LLDPack


def run_l2_scaffold(handoff: HLDHandoff, lld: LLDPack, repo_root: Path) -> list[str]:
    repo_root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    def write(rel: str, content: str) -> None:
        p = repo_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        created.append(rel)

    write("app/__init__.py", "# Enterprise FastAPI application root\n")
    write("app/api/__init__.py", "# API package\n")
    write("app/db/__init__.py", "# Database package\n")
    write("services/__init__.py", "# Generated service modules\n")
    write("tests/__init__.py", "# Test package\n")
    write("tests/unit/__init__.py", "# Unit tests\n")
    write("tests/acceptance/__init__.py", "# Frozen black-box acceptance oracle suite\n")
    write("tests/harness/__init__.py", "# Deterministic test state seeder harness\n")

    api_modules = [m.path[:-3].replace("/", ".") for m in lld.modules if m.layer == "api"]
    router_reg_lines = [
        "# Auto-generated router registry from LLDPack. DO NOT EDIT IN WORKER.",
        "from __future__ import annotations",
        "import importlib",
        "from typing import Any",
        f"REGISTERED_API_MODULES: list[str] = {json.dumps(api_modules)}",
        "def load_registered_handlers() -> dict[str, Any]:",
        "    handlers: dict[str, Any] = {}",
        "    for mod_path in REGISTERED_API_MODULES:",
        "        mod = importlib.import_module(mod_path)",
        "        for attr in dir(mod):",
        "            if attr.startswith('handle_'):",
        "                handlers[attr] = getattr(mod, attr)",
        "    return handlers",
    ]
    write("app/api/router_registry.py", "\n".join(router_reg_lines) + "\n")

    tables = [t.table_name for m in lld.modules for t in m.tables]
    model_reg_lines = [
        "# Auto-generated persistence table registry from LLDPack. DO NOT EDIT IN WORKER.",
        "from __future__ import annotations",
        f"REGISTERED_TABLES: list[str] = {json.dumps(tables)}",
    ]
    write("app/db/model_registry.py", "\n".join(model_reg_lines) + "\n")
    from pipeline.stages.ui_template import DASHBOARD_HTML
    write("app/ui.py", f"DASHBOARD_HTML = {repr(DASHBOARD_HTML)}\n")

    main_lines = [
        "# Enterprise service entrypoint with health/readiness probes and RFC 7807 error formatting.",
        "from __future__ import annotations",
        "from typing import Any",
        "from app.api.router_registry import load_registered_handlers",
        "from app.db.model_registry import REGISTERED_TABLES",
        "def healthz() -> dict[str, str]:",
        "    return {'status': 'ok'}",
        "def readyz() -> dict[str, Any]:",
        "    return {'status': 'ready', 'tables_registered': len(REGISTERED_TABLES)}",
        "def problem_details(status: int, title: str, detail: str, type_uri: str = 'about:blank') -> dict[str, Any]:",
        "    return {'type': type_uri, 'title': title, 'status': status, 'detail': detail}",
        "def dispatch_request(endpoint_name: str, payload: dict[str, Any], traceparent: str = '00-default-01') -> dict[str, Any]:",
        "    handlers = load_registered_handlers()",
        "    if endpoint_name not in handlers:",
        "        return problem_details(404, 'Not Found', f'Endpoint {endpoint_name} not registered')",
        "    try:",
        "        res = handlers[endpoint_name](payload)",
        "        return {'status': 200, 'traceparent': traceparent, 'data': res}",
        "    except Exception as exc:",
        "        return problem_details(422, exc.__class__.__name__, str(exc))",
        "",
        "try:",
        "    from fastapi import FastAPI, Request",
        "    from fastapi.responses import JSONResponse, HTMLResponse",
        "    from app.ui import DASHBOARD_HTML",
        "    app = FastAPI(",
        "        title='HLD-to-Deployable-Code Enterprise Service',",
        "        description='Autonomous Enterprise Microservices generated from High-Level Design',",
        "        version='1.0.0',",
        "        docs_url='/docs',",
        "        redoc_url='/redoc',",
        "    )",
        "",
        "    @app.get('/', response_class=HTMLResponse)",
        "    def index():",
        "        return HTMLResponse(content=DASHBOARD_HTML, status_code=200)",
        "",
        "    @app.get('/healthz')",
        "    def api_healthz():",
        "        return healthz()",
        "",
        "    @app.get('/readyz')",
        "    def api_readyz():",
        "        return readyz()",
        "",
        "    @app.post('/api/order')",
        "    async def api_order_post(request: Request):",
        "        payload = await request.json()",
        "        res = dispatch_request('handle_order_service_endpoint', payload)",
        "        return JSONResponse(status_code=res.get('status', 200), content=res)",
        "",
        "    @app.get('/api/order')",
        "    def api_order_get():",
        "        return {'endpoint': 'POST /api/order', 'sample': {'order_sku': 'SKU-LAPTOP-X1', 'quantity': 2}}",
        "",
        "    @app.post('/api/inventory')",
        "    async def api_inventory_post(request: Request):",
        "        payload = await request.json()",
        "        res = dispatch_request('handle_inventory_service_endpoint', payload)",
        "        return JSONResponse(status_code=res.get('status', 200), content=res)",
        "",
        "    @app.get('/api/inventory')",
        "    def api_inventory_get():",
        "        return {'endpoint': 'POST /api/inventory', 'sample': {'order_sku': 'INV-CHIP-99', 'quantity': 50}}",
        "",
        "    @app.api_route('/api/{endpoint_name}', methods=['GET', 'POST'])",
        "    async def api_dispatch(endpoint_name: str, request: Request):",
        "        if request.method == 'GET':",
        "            return {'endpoint': f'/api/{endpoint_name}', 'method': 'POST required'}",
        "        payload = await request.json()",
        "        res = dispatch_request(endpoint_name, payload)",
        "        status_code = res.get('status', 200)",
        "        return JSONResponse(status_code=status_code, content=res)",
        "except ImportError:",
        "    app = None",
    ]
    write("app/main.py", "\n".join(main_lines) + "\n")

    seeder_lines = [
        "# Deterministic state seeding harness for black-box acceptance tests.",
        "from __future__ import annotations",
        "from typing import Any",
        "class StateSeeder:",
        "    def __init__(self) -> None:",
        "        self._store: dict[str, list[dict[str, Any]]] = {}",
        "    def given_entity_exists(self, table_name: str, record: dict[str, Any]) -> dict[str, Any]:",
        "        self._store.setdefault(table_name, []).append(dict(record))",
        "        return record",
        "    def list_entities(self, table_name: str) -> list[dict[str, Any]]:",
        "        return list(self._store.get(table_name, []))",
    ]
    write("tests/harness/state_seeder.py", "\n".join(seeder_lines) + "\n")

    for con in lld.api_contracts:
        write(
            con.path,
            f"openapi: 3.1.0\ninfo:\n  title: {handoff.handoff_id}\n  version: {lld.lld_version}\npaths: {{}}\n",
        )

    for mod in lld.modules:
        for tbl in mod.tables:
            cols_sql = ", ".join(f"{c.name} {c.type_annotation}" for c in tbl.columns)
            write(
                f"migrations/001_{tbl.table_name}.sql",
                f"-- UP\nCREATE TABLE IF NOT EXISTS {tbl.table_name} ({cols_sql});\n-- DOWN\nDROP TABLE IF EXISTS {tbl.table_name};\n",
            )

    for mod in lld.modules:
        pkg_dir = Path(mod.path).parent
        write(str(pkg_dir / "__init__.py"), "# Service component package.\n")
        stub_lines = [
            f"# Stub for {mod.id} ({mod.path}).",
            "from __future__ import annotations",
            "from dataclasses import dataclass",
            "",
        ]
        for err in mod.errors:
            stub_lines += [f"class {err.exception_name}(Exception):", "    pass", ""]
        for dto in mod.data_models:
            stub_lines.append("@dataclass")
            stub_lines.append(f"class {dto.name}:")
            for fld in dto.fields:
                stub_lines.append(f"    {fld.name}: {fld.type_annotation}")
            stub_lines.append("")
        for fn in mod.public_interface:
            stub_lines += [
                f"{fn.signature}:",
                "    raise NotImplementedError('Stub pending L3 build')",
                "",
            ]
        write(mod.path, "\n".join(stub_lines))

    write("Dockerfile", "FROM python:3.12-slim\nRUN useradd -m -u 10001 appuser\nUSER 10001\nWORKDIR /app\nCOPY . /app\n")
    write("helm/values.yaml", f"targetPlatform: {handoff.target_platform}\nreplicaCount: 2\npodDisruptionBudget:\n  minAvailable: 1\nnetworkPolicy:\n  enabled: true\n")
    write("suppressions.yaml", "suppressions: []\n")
    return created
