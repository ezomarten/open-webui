from types import SimpleNamespace

from open_webui.utils.task_metadata import (
    build_task_metadata,
    request_metadata_override,
)


def make_request(metadata=None):
    state = SimpleNamespace()
    if metadata is not None:
        state.metadata = metadata
    return SimpleNamespace(state=state)


def test_build_task_metadata_disables_native_function_calling_and_tools():
    request = make_request(
        {
            'chat_id': 'chat-original',
            'tool_ids': ['custom-tool'],
            'tool_servers': [{'id': 'server-1'}],
            'features': {'memory': True, 'web_search': True},
            'params': {
                'function_calling': 'native',
                'reasoning_tags': 'detailed',
            },
            'variables': {'{{USER_NAME}}': 'Takanobu IKEDA'},
        }
    )
    form_data = {'model': 'model-id', 'messages': [], 'chat_id': 'chat-123'}

    metadata = build_task_metadata(request, 'follow_up_generation', form_data)

    assert metadata['task'] == 'follow_up_generation'
    assert metadata['task_body'] == form_data
    assert metadata['chat_id'] == 'chat-123'
    assert metadata['tool_ids'] is None
    assert metadata['tool_servers'] == []
    assert metadata['features'] == {}
    assert metadata['params']['function_calling'] == 'default'
    assert metadata['params']['reasoning_tags'] == 'detailed'
    assert metadata['variables'] == {'{{USER_NAME}}': 'Takanobu IKEDA'}


def test_build_task_metadata_without_inherited_metadata_uses_default_params():
    request = make_request()
    form_data = {'model': 'model-id', 'messages': []}

    metadata = build_task_metadata(request, 'title_generation', form_data)

    assert metadata['task'] == 'title_generation'
    assert metadata['task_body'] == form_data
    assert metadata['chat_id'] is None
    assert metadata['tool_ids'] is None
    assert metadata['tool_servers'] == []
    assert metadata['features'] == {}
    assert metadata['params'] == {'function_calling': 'default'}


def test_request_metadata_override_restores_original_request_metadata():
    original_metadata = {
        'params': {'function_calling': 'native'},
        'chat_id': 'chat-original',
    }
    override_metadata = {
        'params': {'function_calling': 'default'},
        'chat_id': 'chat-task',
    }
    request = make_request(original_metadata)

    with request_metadata_override(request, override_metadata):
        assert request.state.metadata == override_metadata

    assert request.state.metadata == original_metadata