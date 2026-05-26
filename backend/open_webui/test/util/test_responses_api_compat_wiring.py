"""Source-grep regression tests guarding the responses-api-compat fork wiring.

``normalize_task_response`` lives in ``open_webui.utils.misc`` and has unit
tests under ``test_response_normalization.py``. These wiring tests guard the
``routers/tasks.py`` integration that silently disappeared during the v0.9.5
upstream sync (see FORK_NOTES.md, maintenance record 2026-05-26).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '# fork:responses-api-compat'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_normalize_task_response_helper_carries_sentinel():
    source = _read('backend', 'open_webui', 'utils', 'misc.py')

    assert SENTINEL in source
    assert 'def normalize_task_response(' in source


def test_tasks_router_imports_normalize_helper():
    source = _read('backend', 'open_webui', 'routers', 'tasks.py')

    assert 'from open_webui.utils.misc import normalize_task_response' in source


def test_tasks_router_normalizes_every_response():
    source = _read('backend', 'open_webui', 'routers', 'tasks.py')

    # The local wrapper must call normalize_task_response so Responses-API
    # output (e.g. OpenRouter) is converted to chat-completion shape before
    # task callers see it.
    assert 'return normalize_task_response(response)' in source
    # And the sentinel must be present so this wiring cannot disappear
    # without tripping the gate.
    assert source.count(SENTINEL) >= 2  # import + return site
