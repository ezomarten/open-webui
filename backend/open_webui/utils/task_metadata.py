from contextlib import contextmanager
from typing import Any


# fork:task-metadata-sanitize
def build_task_metadata(request: Any, task: str, form_data: dict) -> dict:
    inherited_metadata = dict(request.state.metadata) if hasattr(request.state, 'metadata') else {}

    params = dict(inherited_metadata.get('params') or {})
    params['function_calling'] = 'default'

    return {
        **inherited_metadata,
        'task': str(task),
        'task_body': form_data,
        'chat_id': form_data.get('chat_id', None),
        'tool_ids': None,
        'tool_servers': [],
        'features': {},
        'params': params,
    }


# fork:task-metadata-sanitize
@contextmanager
def request_metadata_override(request: Any, metadata_override: dict | None):
    if metadata_override is None:
        yield
        return

    had_metadata = hasattr(request.state, 'metadata')
    original_metadata = request.state.metadata if had_metadata else None
    request.state.metadata = metadata_override

    try:
        yield
    finally:
        if had_metadata:
            request.state.metadata = original_metadata
        else:
            delattr(request.state, 'metadata')
