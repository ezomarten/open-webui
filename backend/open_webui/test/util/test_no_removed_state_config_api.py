"""Repo-wide ban on the removed ``app.state.config`` runtime API.

Background
----------
Upstream v0.10.x replaced the ``app.state.config`` attribute with the async
persistent-config API (``await Config.get(...)`` / ``Config.get_many``) plus
dedicated ``app.state`` fields. The fork-only ``public_shares.py`` router
kept reading ``request.app.state.config``, so after the v0.10.2 sync every
public-link operation failed with ``AttributeError: 'State' object has no
attribute 'config'`` — and the regression survived four upstream syncs
because grep-based wiring tests matched the stale code and the router unit
tests mocked ``app.state.config`` back into existence.

This test is the *general* guard: no backend module (source or test) may
reference an attribute chain ``<something>.state.config`` again. If a future
upstream legitimately reintroduces an attribute with this shape, removal
from ``ALLOWED`` is a deliberate act recorded here.

The check is AST-based so explanatory comments and docstrings (like this
one) do not trigger it.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / 'backend'

# (relpath, lineno) tuples known and accepted. Each entry MUST carry a
# justification. Intentionally empty.
ALLOWED: set[tuple[str, int]] = set()


def _find_state_config_accesses(tree: ast.AST) -> list[int]:
    hits: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == 'config'
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == 'state'
        ):
            hits.append(node.lineno)
    return hits


def test_backend_has_no_state_config_attribute_access():
    findings: list[str] = []
    for path in sorted(BACKEND.rglob('*.py')):
        if '__pycache__' in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf8', errors='ignore'))
        except SyntaxError:
            continue
        relpath = path.relative_to(BACKEND).as_posix()
        for lineno in _find_state_config_accesses(tree):
            if (relpath, lineno) not in ALLOWED:
                findings.append(f'  {relpath}:{lineno}')

    if findings:
        raise AssertionError(
            "Removed runtime API 'app.state.config' referenced again. "
            'Upstream v0.10.x removed app.state.config in favor of the async '
            'persistent-config API (await Config.get(...)) and dedicated '
            'app.state fields; the stale reference in public_shares.py broke '
            'public-link creation for four releases (2026-09 incident). Use '
            'await Config.get(...) or the matching app.state field instead, '
            'or add an ALLOWED entry with a justification.\n' + '\n'.join(findings)
        )


def test_ban_detector_works():
    """Self-test: the AST detector must flag the historical bug shape but
    ignore prose mentioning it (comments/docstrings)."""
    bad = ast.parse('def f(request):\n    return request.app.state.config.FOO\n')
    assert _find_state_config_accesses(bad) == [2]

    good = ast.parse(
        'def f(request):\n'
        '    # v0.10.x removed app.state.config; do not use it.\n'
        '    """References like app.state.config.X are banned."""\n'
        "    return getattr(request.app.state, 'PUBLIC_SHARE_BASE_URL', '')\n"
    )
    assert _find_state_config_accesses(good) == []
