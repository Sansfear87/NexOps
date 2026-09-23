import ast
from pathlib import Path


def test_agent_subsystem_has_no_direct_db_or_sdk_imports():
    """Verify architectural invariant: agent package must never directly import database or cloud SDKs."""
    agent_dir = Path(__file__).resolve().parent.parent.parent / "agent"
    forbidden_modules = [
        "sqlalchemy",
        "asyncpg",
        "psycopg2",
        "alembic",
        "requests",
        "httpx",
        "aiohttp",
        "github",
        "app.models",
        "app.db",
        "app.core.config",
    ]

    for py_file in agent_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), (
                            f"Architectural Violation: '{py_file.name}' imports '{alias.name}', "
                            f"which violates the agent isolation boundary!"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        assert not node.module.startswith(forbidden), (
                            f"Architectural Violation: '{py_file.name}' imports from '{node.module}', "
                            f"which violates the agent isolation boundary!"
                        )
