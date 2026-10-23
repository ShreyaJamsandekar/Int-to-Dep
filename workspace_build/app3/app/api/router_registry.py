# Auto-generated router registry from LLDPack. DO NOT EDIT IN WORKER.
from __future__ import annotations
import importlib
from typing import Any
REGISTERED_API_MODULES: list[str] = ["services.user_registration_service.api_routes", "services.auth_credential_service.api_routes"]
def load_registered_handlers() -> dict[str, Any]:
    handlers: dict[str, Any] = {}
    for mod_path in REGISTERED_API_MODULES:
        mod = importlib.import_module(mod_path)
        for attr in dir(mod):
            if attr.startswith('handle_'):
                handlers[attr] = getattr(mod, attr)
    return handlers
