from types import SimpleNamespace

from open_webui.utils.public_share import (
    ATTACHMENT_OMITTED_TEXT,
    PUBLIC_SHARE_SCHEMA_VERSION,
    PUBLIC_SHARE_PAGE_CONTENT_SECURITY_POLICY,
    build_public_share_snapshot,
    get_public_share_response_headers,
    sanitize_public_message,
)


def test_sanitize_public_message_keeps_public_web_citations_only():
    message = {
        'id': 'msg_1',
        'role': 'assistant',
        'content': 'Answer with a web citation [1].',
        'sources': [
            {
                'source': {'name': 'search_web', 'id': 'search_web'},
                'document': ['Example title\nExample snippet'],
                'metadata': [
                    {
                        'source': 'https://example.com/article',
                        'name': 'Example title',
                        'url': 'https://example.com/article',
                    }
                ],
                'distances': [0.12],
            },
            {
                'source': {'id': 'file_123', 'name': 'internal.pdf', 'type': 'file'},
                'document': ['Private document chunk'],
                'metadata': [
                    {
                        'source': 'internal.pdf',
                        'name': 'internal.pdf',
                        'file_id': 'file_123',
                    }
                ],
                'distances': [0.03],
            },
        ],
    }

    sanitized = sanitize_public_message(message)

    assert sanitized is not None
    assert sanitized['content'] == 'Answer with a web citation [1].'
    assert len(sanitized['sources']) == 1
    assert sanitized['sources'][0]['metadata'] == [
        {
            'source': 'https://example.com/article',
            'url': 'https://example.com/article',
            'name': 'Example title',
        }
    ]
    assert sanitized['sources'][0]['document'] == ['Example title\nExample snippet']
    assert sanitized['sources'][0]['distances'] == [0.12]


def test_sanitize_public_message_does_not_leak_private_citations():
    message = {
        'id': 'msg_2',
        'role': 'assistant',
        'content': '',
        'sources': [
            {
                'source': {'id': 'file_123', 'name': 'internal.pdf', 'type': 'file'},
                'document': ['Private document chunk'],
                'metadata': [
                    {
                        'source': 'internal.pdf',
                        'name': 'internal.pdf',
                        'file_id': 'file_123',
                    }
                ],
            }
        ],
    }

    sanitized = sanitize_public_message(message)

    assert sanitized is not None
    assert sanitized['content'] == ATTACHMENT_OMITTED_TEXT
    assert 'sources' not in sanitized


def test_sanitize_public_message_marks_mixed_source_entries_as_partially_omitted():
    message = {
        'id': 'msg_3',
        'role': 'assistant',
        'content': '',
        'sources': [
            {
                'source': {'name': 'search_web', 'id': 'search_web'},
                'document': ['Public snippet', 'Private snippet'],
                'metadata': [
                    {
                        'source': 'https://example.com/article',
                        'name': 'Example title',
                        'url': 'https://example.com/article',
                    },
                    {
                        'source': 'internal.pdf',
                        'name': 'internal.pdf',
                        'file_id': 'file_123',
                    },
                ],
            }
        ],
    }

    sanitized = sanitize_public_message(message)

    assert sanitized is not None
    assert sanitized['content'] == ATTACHMENT_OMITTED_TEXT
    assert len(sanitized['sources']) == 1
    assert sanitized['sources'][0]['document'] == ['Public snippet']


def test_build_public_share_snapshot_preserves_public_sources_and_schema_version():
    chat = SimpleNamespace(
        title='Public Share',
        chat={
            'title': 'Public Share',
            'messages': [
                {
                    'id': 'msg_1',
                    'role': 'assistant',
                    'content': 'Answer with citation [1].',
                    'sources': [
                        {
                            'source': {'name': 'search_web', 'id': 'search_web'},
                            'document': ['Example title\nExample snippet'],
                            'metadata': [
                                {
                                    'source': 'https://example.com/article',
                                    'name': 'Example title',
                                    'url': 'https://example.com/article',
                                }
                            ],
                        }
                    ],
                }
            ],
            'models': ['demo-model'],
        },
    )

    snapshot = build_public_share_snapshot(chat)

    assert snapshot['schema_version'] == PUBLIC_SHARE_SCHEMA_VERSION
    assert snapshot['models'] == ['demo-model']
    assert snapshot['messages'][0]['sources'][0]['metadata'][0]['url'] == 'https://example.com/article'
    assert snapshot['history']['currentId'] == 'msg_1'


def test_build_public_share_snapshot_preserves_multi_model_history_tree():
    chat = SimpleNamespace(
        title='Parallel Share',
        chat={
            'title': 'Parallel Share',
            'history': {
                'currentId': 'assistant_b',
                'messages': {
                    'user_1': {
                        'id': 'user_1',
                        'role': 'user',
                        'content': 'Compare these models.',
                        'parentId': None,
                        'childrenIds': ['assistant_a', 'assistant_b'],
                        'models': ['model-a', 'model-b'],
                    },
                    'assistant_a': {
                        'id': 'assistant_a',
                        'role': 'assistant',
                        'content': 'Model A response',
                        'parentId': 'user_1',
                        'childrenIds': [],
                        'model': 'model-a',
                        'modelIdx': 0,
                    },
                    'assistant_b': {
                        'id': 'assistant_b',
                        'role': 'assistant',
                        'content': 'Model B response',
                        'parentId': 'user_1',
                        'childrenIds': [],
                        'model': 'model-b',
                        'modelIdx': 1,
                    },
                },
            },
            'models': ['model-a', 'model-b'],
        },
    )

    snapshot = build_public_share_snapshot(chat)
    history = snapshot['history']

    assert snapshot['schema_version'] == PUBLIC_SHARE_SCHEMA_VERSION
    assert snapshot['models'] == ['model-a', 'model-b']
    assert {message['id'] for message in snapshot['messages']} == {
        'user_1',
        'assistant_a',
        'assistant_b',
    }
    assert history['currentId'] == 'assistant_b'
    assert history['messages']['user_1']['childrenIds'] == ['assistant_a', 'assistant_b']
    assert history['messages']['user_1']['models'] == ['model-a', 'model-b']
    assert history['messages']['assistant_a']['modelIdx'] == 0
    assert history['messages']['assistant_b']['modelIdx'] == 1


def test_build_public_share_snapshot_skips_private_intermediate_nodes():
    chat = SimpleNamespace(
        title='Tool Share',
        chat={
            'title': 'Tool Share',
            'history': {
                'currentId': 'assistant_1',
                'messages': {
                    'user_1': {
                        'id': 'user_1',
                        'role': 'user',
                        'content': 'Use a tool.',
                        'parentId': None,
                        'childrenIds': ['tool_1'],
                        'models': ['tool-model'],
                    },
                    'tool_1': {
                        'id': 'tool_1',
                        'role': 'tool',
                        'content': 'hidden tool output',
                        'parentId': 'user_1',
                        'childrenIds': ['assistant_1'],
                    },
                    'assistant_1': {
                        'id': 'assistant_1',
                        'role': 'assistant',
                        'content': 'Visible answer',
                        'parentId': 'tool_1',
                        'childrenIds': [],
                        'model': 'tool-model',
                        'modelIdx': 0,
                    },
                },
            },
            'models': ['tool-model'],
        },
    )

    snapshot = build_public_share_snapshot(chat)
    history = snapshot['history']

    assert set(history['messages'].keys()) == {'user_1', 'assistant_1'}
    assert history['messages']['user_1']['childrenIds'] == ['assistant_1']
    assert history['messages']['assistant_1']['parentId'] == 'user_1'
    assert history['currentId'] == 'assistant_1'


def test_build_public_share_snapshot_falls_back_to_message_list_when_history_has_no_public_roles():
    chat = SimpleNamespace(
        title='Fallback Share',
        chat={
            'title': 'Fallback Share',
            'history': {
                'currentId': 'tool_1',
                'messages': {
                    'system_1': {
                        'id': 'system_1',
                        'role': 'system',
                        'content': 'hidden system prompt',
                        'parentId': None,
                        'childrenIds': ['tool_1'],
                    },
                    'tool_1': {
                        'id': 'tool_1',
                        'role': 'tool',
                        'content': 'hidden tool output',
                        'parentId': 'system_1',
                        'childrenIds': [],
                    },
                },
            },
            'messages': [
                {
                    'id': 'user_1',
                    'role': 'user',
                    'content': 'Visible prompt',
                },
                {
                    'id': 'assistant_1',
                    'role': 'assistant',
                    'content': 'Visible answer',
                    'model': 'fallback-model',
                },
            ],
            'models': ['fallback-model'],
        },
    )

    snapshot = build_public_share_snapshot(chat)
    history = snapshot['history']

    assert snapshot['schema_version'] == PUBLIC_SHARE_SCHEMA_VERSION
    assert [message['id'] for message in snapshot['messages']] == ['user_1', 'assistant_1']
    assert snapshot['models'] == ['fallback-model']
    assert set(history['messages'].keys()) == {'user_1', 'assistant_1'}
    assert history['currentId'] == 'assistant_1'


def test_public_share_page_headers_include_public_host_hardening():
    headers = get_public_share_response_headers('/p/public-share-id')

    assert headers['Cache-Control'] == 'no-store'
    assert headers['Content-Security-Policy'] == PUBLIC_SHARE_PAGE_CONTENT_SECURITY_POLICY
    assert headers['Permissions-Policy'] == (
        'camera=(), geolocation=(), microphone=(), payment=(), usb=(), xr-spatial-tracking=()'
    )
    assert headers['Referrer-Policy'] == 'no-referrer'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['X-Frame-Options'] == 'DENY'
    assert headers['X-Robots-Tag'] == 'noindex, nofollow, noarchive'


def test_public_share_static_assets_keep_cache_policy_untouched():
    headers = get_public_share_response_headers('/_app/immutable/app.js')

    assert 'Cache-Control' not in headers
    assert 'Content-Security-Policy' not in headers
    assert headers['X-Robots-Tag'] == 'noindex, nofollow, noarchive'
