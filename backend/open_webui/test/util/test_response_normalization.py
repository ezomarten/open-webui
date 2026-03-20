from open_webui.utils.misc import (
    ensure_output_timing,
    mark_output_item_completed,
    normalize_task_response,
)


def test_normalize_task_response_converts_responses_api_output_to_chat_completion():
    response = {
        "id": "resp_123",
        "object": "response",
        "created_at": 1774000000,
        "model": "google/gemini-3.1-flash-lite-preview",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"queries": ["Sapporo weather today"]}',
                    }
                ],
                "status": "completed",
            }
        ],
        "usage": {"input_tokens": 12, "output_tokens": 8, "total_tokens": 20},
    }

    normalized = normalize_task_response(response)

    assert normalized["object"] == "chat.completion"
    assert normalized["id"] == "resp_123"
    assert normalized["created"] == 1774000000
    assert (
        normalized["choices"][0]["message"]["content"]
        == '{"queries": ["Sapporo weather today"]}'
    )
    assert normalized["output"] == response["output"]
    assert normalized["usage"] == response["usage"]


def test_ensure_output_timing_backfills_started_at_for_completed_items():
    output = [
        {
            "type": "reasoning",
            "status": "completed",
            "content": [{"type": "output_text", "text": "thinking"}],
        }
    ]

    normalized = ensure_output_timing(output, now=42.0)

    assert normalized[0]["started_at"] == 42.0
    assert normalized[0]["ended_at"] == 42.0
    assert normalized[0]["duration"] == 0


def test_mark_output_item_completed_handles_missing_started_at():
    item = {
        "type": "reasoning",
        "status": "in_progress",
        "content": [{"type": "output_text", "text": "thinking"}],
    }

    mark_output_item_completed(item, ended_at=55.0)

    assert item["started_at"] == 55.0
    assert item["ended_at"] == 55.0
    assert item["duration"] == 0
    assert item["status"] == "completed"
