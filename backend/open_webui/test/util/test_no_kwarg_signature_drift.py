"""General signature-drift guard (fork upstream-sync hygiene).

Background
----------
The v0.9.5 upstream replay silently dropped the ``timeout`` parameter from
``get_web_loader`` while its caller ``get_loader`` kept forwarding
``timeout=``. That produced a *runtime* ``TypeError`` (the native ``fetch_url``
tool crashed) that none of the per-feature wiring tests caught, because a
wiring test only greps the integration points its author remembered to list.

This test is the *general* counterpart to the per-feature wiring tests: it
statically scans the whole backend for bare-name calls whose resolved,
single, repo-level callee does **not** accept a keyword argument the call
passes (and the callee has no ``**kwargs`` catch-all). That is exactly the
"caller kept, callee patch dropped" failure mode. Any future upstream sync
that drops a parameter while leaving its callers intact will turn this test
red, regardless of whether the affected code is a documented fork feature.

Scope / false-positive control
------------------------------
To stay low-noise the scan only flags a call when ALL of the following hold:

* the call target is a bare ``name(...)`` (attribute calls like ``obj.f(...)``
  are too ambiguous to resolve statically and are skipped);
* ``name`` resolves to exactly one module-level ``def``/``async def`` in this
  repository, either defined in the same module or imported via an explicit
  ``from x import y [as z]`` (so overloaded names such as the two
  ``generate_chat_completion`` definitions resolve to the *imported* one);
* that callee is not decorated (decorators may rewrite the signature);
* that callee has no ``**kwargs`` catch-all.

Known, intentionally-allowed mismatches (e.g. a defect that exists identically
in upstream and is therefore out of scope for this minimal fork) are listed in
``ALLOWED_MISMATCHES`` with a justification. The test fails on any mismatch not
in that allowlist.

See FORK_NOTES.md > Fork Management Contract.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / 'backend'
PKG_ROOT = BACKEND  # dotted module names are relative to backend/ (open_webui.*)

# Directory names whose contents are not scanned for callers/callees.
SKIP_PARTS = {'test', 'tests', 'migrations'}

# (caller_relpath, callee_name, keyword) tuples that are known and accepted.
# Each entry MUST carry a justification. Remove an entry once upstream fixes it.
ALLOWED_MISMATCHES = {
    # Upstream v0.9.5 ships this exact mismatch: routers/retrieval.py passes
    # user= to query_doc_with_hybrid_search, whose def has neither a `user`
    # parameter nor **kwargs. Verified identical in upstream (both the def and
    # the call site), so it is an upstream defect, not a fork regression. We do
    # not patch it to keep the fork minimal; track it here so it cannot mask a
    # *new* drift, and so removing it is a deliberate act once upstream fixes it.
    ('open_webui/routers/retrieval.py', 'query_doc_with_hybrid_search', 'user'),
}


def _module_dotted(path: Path) -> str:
    rel = path.relative_to(PKG_ROOT).with_suffix('')
    return '.'.join(rel.parts)


def _accepted_kwargs(fn: ast.AST):
    a = fn.args
    names = set()
    for group in (a.posonlyargs, a.args, a.kwonlyargs):
        for arg in group:
            names.add(arg.arg)
    return names, a.kwarg is not None


def _scan():
    files = [p for p in BACKEND.rglob('*.py') if not (set(p.relative_to(PKG_ROOT).parts) & SKIP_PARTS)]

    # Index every module-level function: (module_dotted, name) -> (path, node)
    defs_by_modname: dict[tuple[str, str], tuple[Path, ast.AST]] = {}
    parsed: dict[Path, ast.AST] = {}
    for p in files:
        try:
            tree = ast.parse(p.read_text(encoding='utf8', errors='ignore'))
        except SyntaxError:
            continue
        parsed[p] = tree
        mod = _module_dotted(p)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs_by_modname[(mod, node.name)] = (p, node)

    findings = []  # (caller_relpath, lineno, callee_name, kw, callee_relpath, callee_lineno)
    for p, tree in parsed.items():
        alias_map: dict[str, tuple[str, str]] = {}
        local_defs: dict[str, ast.AST] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                for n in node.names:
                    alias_map[n.asname or n.name] = (node.module, n.name)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local_defs[node.name] = node

        for call in ast.walk(tree):
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                continue
            passed = [k.arg for k in call.keywords if k.arg is not None]
            if not passed:
                continue
            name = call.func.id
            target = None
            if name in alias_map:
                target = defs_by_modname.get(alias_map[name])
            elif name in local_defs:
                target = (p, local_defs[name])
            if target is None:
                continue
            tpath, tnode = target
            if tnode.decorator_list:
                continue
            accepted, has_kwargs = _accepted_kwargs(tnode)
            if has_kwargs:
                continue
            for kw in passed:
                if kw not in accepted:
                    findings.append(
                        (
                            p.relative_to(PKG_ROOT).as_posix(),
                            call.lineno,
                            name,
                            kw,
                            tpath.relative_to(PKG_ROOT).as_posix(),
                            tnode.lineno,
                        )
                    )
    return findings


def test_no_new_kwarg_signature_drift():
    findings = _scan()
    unexpected = [f for f in findings if (f[0], f[2], f[3]) not in ALLOWED_MISMATCHES]
    if unexpected:
        lines = [
            f'  {caller}:{lineno}: {callee}(... {kw}=) ' f'is not accepted by {cpath}:{cline}'
            for caller, lineno, callee, kw, cpath, cline in sorted(unexpected)
        ]
        raise AssertionError(
            'Keyword-argument signature drift detected (a caller passes a '
            'keyword the resolved callee no longer accepts). This is the '
            '"caller kept, callee patch dropped" failure mode that silently '
            'broke get_web_loader(timeout=...) during the v0.9.5 upstream '
            'sync. Restore the dropped parameter, or — if the mismatch exists '
            'identically in upstream and is intentionally left unpatched — add '
            'it to ALLOWED_MISMATCHES with a justification.\n' + '\n'.join(lines)
        )


def test_allowlist_entries_are_stable_shape():
    # Guard against typos in the allowlist that would silently disable the test.
    for entry in ALLOWED_MISMATCHES:
        assert isinstance(entry, tuple) and len(entry) == 3, entry
        caller, callee, kw = entry
        assert caller.endswith('.py') and '/' in caller, caller
        assert callee.isidentifier(), callee
        assert kw.isidentifier(), kw
