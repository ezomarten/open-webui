"""Source-grep regression tests guarding the task-metadata-sanitize fork wiring.

The helper module ``open_webui.utils.task_metadata`` already has unit tests
under ``test_task_metadata.py``. These wiring tests separately protect the
integration points in ``routers/tasks.py`` that have silently disappeared
during past upstream syncs (see FORK_NOTES.md, maintenance record
2026-05-26). If these assertions fail, task LLM calls leak builtin tool
exposure and non-default function_calling mode even when helper unit tests
still pass.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '# fork:task-metadata-sanitize'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_task_metadata_helper_module_carries_sentinel():
    source = _read('backend', 'open_webui', 'utils', 'task_metadata.py')

    assert source.count(SENTINEL) >= 2  # build_task_metadata + request_metadata_override


def test_tasks_router_imports_task_metadata_helpers():
    source = _read('backend', 'open_webui', 'routers', 'tasks.py')

    assert 'from open_webui.utils.task_metadata import' in source
    assert 'build_task_metadata' in source
    assert 'request_metadata_override' in source


def test_tasks_router_local_wrapper_applies_metadata_override():
    source = _read('backend', 'open_webui', 'routers', 'tasks.py')

    # Upstream's generate_chat_completion must be renamed so the local
    # wrapper can intercept calls and apply the metadata override.
    assert 'generate_chat_completion as _generate_chat_completion' in source
    assert 'with request_metadata_override(request, metadata_override):' in source


def test_tasks_router_each_endpoint_builds_sanitized_metadata():
    source = _read('backend', 'open_webui', 'routers', 'tasks.py')

    # 8 task endpoints must each call build_task_metadata so they no longer
    # inherit the chat's tool_ids / tool_servers / params.function_calling.
    assert source.count('build_task_metadata(request, TASKS.') >= 8
    # And they must forward the override into the local wrapper, otherwise
    # downstream filters re-inherit the unsanitized request metadata.
    assert source.count('metadata_override=task_metadata') >= 8


def test_tasks_router_carries_sentinel_at_every_call_site():
    source = _read('backend', 'open_webui', 'routers', 'tasks.py')

    # One per import block + one per endpoint + one inside the local wrapper.
    assert source.count(SENTINEL) >= 10
