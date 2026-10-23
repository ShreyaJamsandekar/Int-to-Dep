"""Anti-hallucination dependency allowlist and protected-path enforcement."""
from __future__ import annotations

import ast
from pathlib import Path

APPROVED_STDLIB_AND_PACKAGES = {
    "__future__",
    "abc",
    "annotations",
    "asyncio",
    "collections",
    "contextlib",
    " dataclasses",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "functools",
    "hashlib",
    "httpx",
    "inspect",
    "itertools",
    "json",
    "logging",
    "math",
    "os",
    "pathlib",
    "pydantic",
    "pytest",
    "unittest",
    "re",
    "shutil",
    "sqlite3",
    "sqlalchemy",
    "statistics",
    " structlog",
    "structlog",
    "sys",
    "tempfile",
    "time",
    "typing",
    "uuid",
    "fastapi",
    "starlette",
    "app",
    "services",
    "tests",
}

PROTECTED_PATH_PREFIXES = (
    "tests/acceptance/",
    "tests/harness/",
    ".github/",
    "helm/",
    "Dockerfile",
    "pyproject.toml",
    "suppressions.yaml",
    "app/main.py",
    "app/api/router_registry.py",
    "app/db/model_registry.py",
)


def check_imports_allowed(py_file: Path, extra_allowed: set[str] | None = None) -> list[str]:
    allowed = set(APPROVED_STDLIB_AND_PACKAGES) | (extra_allowed or set())
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [f"{py_file}: SyntaxError at line {e.lineno}: {e.msg}"]

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg not in allowed:
                    violations.append(f"{py_file}:{node.lineno}: unapproved package '{root_pkg}'")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg not in allowed:
                    violations.append(f"{py_file}:{node.lineno}: unapproved package '{root_pkg}'")
    return violations


def check_protected_paths_untouched(modified_files: list[str]) -> list[str]:
    violations: list[str] = []
    for f in modified_files:
        norm = f.lstrip("./")
        if any(norm == p or norm.startswith(p) for p in PROTECTED_PATH_PREFIXES):
            violations.append(f"worker touched protected path: {norm}")
    return violations
