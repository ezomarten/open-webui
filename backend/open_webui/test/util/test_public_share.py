from types import SimpleNamespace

from open_webui.utils.public_share import (
    ATTACHMENT_OMITTED_TEXT,
    PUBLIC_SHARE_SCHEMA_VERSION,
    build_public_share_snapshot,
    sanitize_public_message,
)


def test_sanitize_public_message_keeps_public_web_citations_only():
    message = {
        "id": "msg_1",
        "role": "assistant",
        "content": "Answer with a web citation [1].",
        "sources": [
            {
                "source": {"name": "search_web", "id": "search_web"},
                "document": ["Example title\nExample snippet"],
                "metadata": [
                    {
                        "source": "https://example.com/article",
                        "name": "Example title",
                        "url": "https://example.com/article",
                    }
                ],
                "distances": [0.12],
            },
            {
                "source": {"id": "file_123", "name": "internal.pdf", "type": "file"},
                "document": ["Private document chunk"],
                "metadata": [
                    {
                        "source": "internal.pdf",
                        "name": "internal.pdf",
                        "file_id": "file_123",
                    }
                ],
                "distances": [0.03],
            },
        ],
    }

    sanitized = sanitize_public_message(message)

    assert sanitized is not None
    assert sanitized["content"] == "Answer with a web citation [1]."
    assert len(sanitized["sources"]) == 1
    assert sanitized["sources"][0]["metadata"] == [
        {
            "source": "https://example.com/article",
            "url": "https://example.com/article",
            "name": "Example title",
        }
    ]
    assert sanitized["sources"][0]["document"] == ["Example title\nExample snippet"]
    assert sanitized["sources"][0]["distances"] == [0.12]


def test_sanitize_public_message_does_not_leak_private_citations():
    message = {
        "id": "msg_2",
        "role": "assistant",
        "content": "",
        "sources": [
            {
                "source": {"id": "file_123", "name": "internal.pdf", "type": "file"},
                "document": ["Private document chunk"],
                "metadata": [
                    {
                        "source": "internal.pdf",
                        "name": "internal.pdf",
                        "file_id": "file_123",
                    }
                ],
            }
        ],
    }

    sanitized = sanitize_public_message(message)

    assert sanitized is not None
    assert sanitized["content"] == ATTACHMENT_OMITTED_TEXT
    assert "sources" not in sanitized


def test_sanitize_public_message_marks_mixed_source_entries_as_partially_omitted():
    message = {
        "id": "msg_3",
        "role": "assistant",
        "content": "",
        "sources": [
            {
                "source": {"name": "search_web", "id": "search_web"},
                "document": ["Public snippet", "Private snippet"],
                "metadata": [
                    {
                        "source": "https://example.com/article",
                        "name": "Example title",
                        "url": "https://example.com/article",
                    },
                    {
                        "source": "internal.pdf",
                        "name": "internal.pdf",
                        "file_id": "file_123",
                    },
                ],
            }
        ],
    }

    sanitized = sanitize_public_message(message)

    assert sanitized is not None
    assert sanitized["content"] == ATTACHMENT_OMITTED_TEXT
    assert len(sanitized["sources"]) == 1
    assert sanitized["sources"][0]["document"] == ["Public snippet"]


def test_build_public_share_snapshot_preserves_public_sources_and_schema_version():
    chat = SimpleNamespace(
        title="Public Share",
        chat={
            "title": "Public Share",
            "messages": [
                {
                    "id": "msg_1",
                    "role": "assistant",
                    "content": "Answer with citation [1].",
                    "sources": [
                        {
                            "source": {"name": "search_web", "id": "search_web"},
                            "document": ["Example title\nExample snippet"],
                            "metadata": [
                                {
                                    "source": "https://example.com/article",
                                    "name": "Example title",
                                    "url": "https://example.com/article",
                                }
                            ],
                        }
                    ],
                }
            ],
            "models": ["demo-model"],
        },
    )

    snapshot = build_public_share_snapshot(chat)

    assert snapshot["schema_version"] == PUBLIC_SHARE_SCHEMA_VERSION
    assert snapshot["models"] == ["demo-model"]
    assert snapshot["messages"][0]["sources"][0]["metadata"][0]["url"] == "https://example.com/article"
