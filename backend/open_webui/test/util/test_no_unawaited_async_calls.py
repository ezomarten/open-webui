"""General unawaited-async-call drift guard (fork upstream-sync hygiene).

Background
----------
The v0.10.2 upstream sync turned ``get_content_from_url`` into ``async def``.
The fork's ``fetch_url`` timeout patch kept calling it through
``asyncio.to_thread(...)``, so every URL fetch failed at runtime with
``cannot unpack non-iterable coroutine object`` — and no per-feature wiring
test noticed, because grep-based wiring tests match strings, not call shapes.

This test is the *general* counterpart to ``test_no_kwarg_signature_drift.py``
for the sync->async failure mode. It statically scans the whole backend for
bare-name calls whose resolved, single, repo-level callee is a module-level
``async def`` **and** whose surrounding call shape cannot legally defer the
resulting coroutine:

* a plain expression statement (fire-and-forget) — almost always a bug;
* an unpacking assignment (``a, b = ...``) or attribute/subscript target —
  always a runtime ``TypeError`` against a coroutine object;
* anything else the scanner cannot prove is collected/awaited later.

Call shapes that legitimately defer awaiting are allowed: ``await``,
``return fn()`` delegation, lambda bodies, collection literals and
comprehensions, ``tasks.append(fn())`` collectors, task-style ``x = fn()``
assignments to a plain name, ternary task selection, combinator wrappers
(``asyncio.wait_for`` / ``gather`` / ``create_task`` / ``ensure_future`` /
``as_completed`` / ``run_coroutine_threadsafe``), and ``async with`` /
``async for``.

Scope / false-positive control
------------------------------
* bare ``name(...)`` calls only (attribute calls are statically ambiguous);
* ``name`` must resolve to exactly one module-level ``async def`` in this
  repo, either defined in the same module or imported via an explicit
  ``from x import y [as z]``;
* async-generator functions (calling one never yields a coroutine) and
  decorated callees are skipped;
* test/ and migrations/ trees are not scanned.

Known, intentionally-allowed mismatches can be added to ``ALLOWED`` with a
justification; the test fails on anything not in that set. See
FORK_NOTES.md > Fork Management Contract.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / 'backend'

SKIP_PARTS = {'test', 'tests', 'migrations', '__pycache__'}

# Combinator calls that receive the un-awaited coroutine on purpose.
WRAPPERS = {
    'wait_for',
    'gather',
    'create_task',
    'ensure_future',
    'as_completed',
    'run_coroutine_threadsafe',
}

# Method names that collect callables into a task list awaited later.
COLLECTORS = {'append', 'extend', 'add', 'insert'}

# Threadpool executors: passing an async function here creates the coroutine
# inside a worker thread that nothing ever awaits — the exact v0.10.2
# fetch_url failure (``asyncio.to_thread(get_content_from_url, ...)``).
THREAD_EXECUTORS = {'to_thread', 'run_in_executor', 'run_sync'}

# (caller_relpath, lineno, callee_name) tuples known and accepted.
# Each entry MUST carry a justification.
ALLOWED: set[tuple[str, int, str]] = set()


def _is_async_generator(node: ast.AsyncFunctionDef) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub is not node:
            continue
        if isinstance(sub, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _parent_map(tree: ast.AST) -> dict[int, ast.AST]:
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _call_is_legally_deferred(call: ast.Call, parents: dict[int, ast.AST]) -> bool:
    par = parents.get(id(call))

    if isinstance(par, ast.Await):
        return True
    if isinstance(par, ast.Return):
        return True
    if isinstance(par, ast.Lambda):
        return True
    if isinstance(
        par,
        (
            ast.List,
            ast.Set,
            ast.Tuple,
            ast.Dict,
            ast.ListComp,
            ast.SetComp,
            ast.DictComp,
            ast.GeneratorExp,
            ast.IfExp,
        ),
    ):
        return True
    if isinstance(par, ast.Call):
        func_name = None
        if isinstance(par.func, ast.Name):
            func_name = par.func.id
        elif isinstance(par.func, ast.Attribute):
            func_name = par.func.attr
        if func_name in WRAPPERS:
            return True
        if isinstance(par.func, ast.Attribute) and par.func.attr in COLLECTORS:
            return True
    if isinstance(par, ast.Assign):
        # `task = fn()` is the collect-then-await idiom; unpacking a coroutine
        # (``a, b = fn()``) or storing on an attribute is always a runtime bug.
        return all(isinstance(t, ast.Name) for t in par.targets)
    if isinstance(par, ast.AsyncWith):
        return any(item.context_expr is call for item in par.items)
    if isinstance(par, ast.AsyncFor):
        return par.iter is call
    return False


def scan_module(
    tree: ast.AST,
    module: str,
    async_defs: dict[tuple[str, str], tuple[str, ast.AsyncFunctionDef]],
    relpath: str,
) -> list[tuple[str, int, str]]:
    """Scan one parsed module; returns (relpath, lineno, callee_name) findings.

    ``async_defs`` maps (module_dotted, function_name) to (relpath, node) for
    every repo-level non-generator ``async def`` under scan.
    """
    alias_map: dict[str, tuple[str, str]] = {}
    local_async: dict[str, ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for n in node.names:
                alias_map[n.asname or n.name] = (node.module, n.name)
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and not _is_async_generator(node):
            local_async[node.name] = node

    parents = _parent_map(tree)
    findings: list[tuple[str, int, str]] = []
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue

        if isinstance(call.func, (ast.Name, ast.Attribute)):
            func_name = call.func.id if isinstance(call.func, ast.Name) else call.func.attr
            if func_name in THREAD_EXECUTORS:
                # Flag any bare-name async def handed to a threadpool executor.
                for arg in call.args:
                    if isinstance(arg, ast.Name) and arg.id in local_async and not local_async[arg.id].decorator_list:
                        findings.append((relpath, call.lineno, arg.id))
                    elif isinstance(arg, ast.Name) and arg.id in alias_map:
                        resolved = async_defs.get(alias_map[arg.id])
                        if resolved is not None and not resolved[1].decorator_list:
                            findings.append((relpath, call.lineno, arg.id))

        if not isinstance(call.func, ast.Name):
            continue
        name = call.func.id
        if name in local_async:
            callee = local_async[name]
        elif name in alias_map:
            resolved = async_defs.get(alias_map[name])
            if resolved is None:
                continue
            callee = resolved[1]
        else:
            continue
        if callee.decorator_list:
            continue
        if not _call_is_legally_deferred(call, parents):
            findings.append((relpath, call.lineno, name))
    return findings


def scan_backend() -> list[tuple[str, int, str]]:
    files = [p for p in BACKEND.rglob('*.py') if not (set(p.relative_to(BACKEND).parts) & SKIP_PARTS)]

    async_defs: dict[tuple[str, str], tuple[str, ast.AsyncFunctionDef]] = {}
    parsed: dict[Path, ast.AST] = {}
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding='utf8', errors='ignore'))
        except SyntaxError:
            continue
        parsed[path] = tree
        module = '.'.join(path.relative_to(BACKEND).with_suffix('').parts)
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef) and not _is_async_generator(node):
                async_defs[(module, node.name)] = (
                    path.relative_to(BACKEND).as_posix(),
                    node,
                )

    findings: list[tuple[str, int, str]] = []
    for path, tree in parsed.items():
        relpath = path.relative_to(BACKEND).as_posix()
        findings.extend(scan_module(tree, relpath, async_defs, relpath))
    return findings


def test_backend_has_no_unawaited_async_calls():
    findings = scan_backend()
    unexpected = [f for f in findings if (f[0], f[1], f[2]) not in ALLOWED]
    if unexpected:
        lines = [
            f'  {caller}:{lineno}: {callee}(...) is called but never awaited'
            for caller, lineno, callee in sorted(unexpected)
        ]
        raise AssertionError(
            'Unawaited async-call drift detected. A callee became `async def` '
            '(or a fork patch started calling one) and the result is used in a '
            'shape that cannot await it — the exact failure mode that broke '
            'fetch_url after the v0.10.2 sync ("cannot unpack non-iterable '
            'coroutine object"). Await the call or route it through a combinator; '
            'if the mismatch exists identically in upstream and is intentionally '
            'left unpatched, add it to ALLOWED with a justification.\n' + '\n'.join(lines)
        )


def _synthetic_module(source: str) -> ast.Module:
    return ast.parse(source)


def test_scanner_detects_planted_historical_bug():
    """Self-test: the pre-fix fetch_url shape must be flagged."""
    source = """
import asyncio

async def get_content_from_url(request, url):
    return None, None

def fetch_url(request, url):
    content, _ = asyncio.wait_for(asyncio.to_thread(get_content_from_url, request, url), 1)
    return content

async def other():
    get_content_from_url(None, 'https://x')
"""
    tree = _synthetic_module(source)
    async_defs = {
        ('m', 'get_content_from_url'): ('m.py', tree.body[1]),
    }
    findings = scan_module(tree, 'm', async_defs, 'm.py')
    flagged = {name for _, _, name in findings}
    assert flagged == {'get_content_from_url'}, findings


def test_scanner_allows_legitimate_deferral_shapes():
    source = """
import asyncio

async def helper():
    return None

async def ok_all():
    a = await helper()
    return helper()

def collector():
    tasks = [helper()]
    tasks.append(helper())
    task = helper()
    pick = helper() if task else None
    wrapped = asyncio.wait_for(helper(), 1)
    gathered = asyncio.gather(helper(), helper())
    return tasks, task, pick, wrapped, gathered

async def delegator():
    return helper()

LAMBDA = lambda: helper()
"""
    tree = _synthetic_module(source)
    async_defs = {('m', 'helper'): ('m.py', tree.body[0])}
    findings = scan_module(tree, 'm', async_defs, 'm.py')
    assert findings == [], findings


def test_scanner_skips_async_generators_and_decorated_defs():
    source = """
async def gen():
    yield 1

async def runner():
    gen()

def deco(f):
    return f

@deco
async def decorated():
    return 1

async def runner2():
    decorated()
"""
    tree = _synthetic_module(source)
    # Index exactly like scan_backend does (only module-level async defs).
    async_defs = {}
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef):
            async_defs[('m', node.name)] = ('m.py', node)
    assert scan_module(tree, 'm', async_defs, 'm.py') == []
