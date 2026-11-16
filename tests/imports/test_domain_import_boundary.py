"""Guard the framework-free domain boundary required by ADR-0005.

The domain layer holds prediction, statistics and value objects. It must not
import Home Assistant, an HTTP client or a schema library, so its tests can run
in plain Python. This check is an AST walk rather than a runtime import guard:
it catches a forbidden import even when the symbol is never used at runtime.
"""

from __future__ import annotations

import ast
from pathlib import Path

INTEGRATION_DIR = (
    Path(__file__).resolve().parents[2] / "custom_components" / "cycle_tracker"
)
DOMAIN_DIR = INTEGRATION_DIR / "domain"

FORBIDDEN_ROOTS = frozenset({"homeassistant", "aiohttp", "voluptuous", "requests"})


def _forbidden_imports(path: Path) -> list[str]:
    """Return forbidden imports in one module, as `path:line: module` strings."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        roots: list[str] = []
        if isinstance(node, ast.Import):
            roots = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots = [node.module]
        for root in roots:
            if root.split(".")[0] in FORBIDDEN_ROOTS:
                violations.append(f"{path}:{node.lineno}: {root}")
    return violations


def test_domain_imports_no_framework() -> None:
    """Every module under the domain package stays framework-free."""
    violations = [
        violation
        for path in sorted(DOMAIN_DIR.rglob("*.py"))
        for violation in _forbidden_imports(path)
    ]
    assert not violations, "Domain layer imports a framework:\n" + "\n".join(violations)
