import asyncio

import pytest

from open_webui.utils.http_timeouts import (
    DEFAULT_STREAM_CONNECT_TIMEOUT_SECONDS,
    build_upstream_request_timeout,
    build_upstream_request_timeout_for_payload,
    chunk_contains_meaningful_stream_output,
    get_stream_idle_timeout_message,
    get_stream_prelude_timeout_message,
    iterate_stream_with_post_first_chunk_timeout,
)


async def delayed_stream(delays_and_chunks):
    for delay_seconds, chunk in delays_and_chunks:
        await asyncio.sleep(delay_seconds)
        yield chunk


def test_build_upstream_request_timeout_uses_total_timeout_for_non_stream_requests():
    timeout = build_upstream_request_timeout(300, stream=False)

    assert timeout.total == 300
    assert timeout.sock_read is None


def test_build_upstream_request_timeout_uses_idle_timeout_for_stream_requests():
    timeout = build_upstream_request_timeout(300, stream=True)

    assert timeout.total is None
    assert timeout.sock_read is None
    assert timeout.sock_connect == DEFAULT_STREAM_CONNECT_TIMEOUT_SECONDS


def test_build_upstream_request_timeout_for_payload_defaults_to_non_stream_requests():
    timeout = build_upstream_request_timeout_for_payload(300, None)

    assert timeout.total == 300
    assert timeout.sock_read is None


def test_build_upstream_request_timeout_for_payload_uses_stream_timeout_when_requested():
    timeout = build_upstream_request_timeout_for_payload(300, {"stream": True})

    assert timeout.total is None
    assert timeout.sock_read is None
    assert timeout.sock_connect == DEFAULT_STREAM_CONNECT_TIMEOUT_SECONDS


def test_get_stream_idle_timeout_message_describes_stall():
    assert (
        get_stream_idle_timeout_message(300)
        == "Upstream streaming response stalled for 300 seconds without receiving data."
    )


def test_get_stream_prelude_timeout_message_describes_missing_output():
    assert (
        get_stream_prelude_timeout_message(300)
        == "Upstream streaming response did not produce meaningful output within 300 seconds."
    )


def test_stream_chunk_detector_ignores_role_only_openai_prelude():
    assert not chunk_contains_meaningful_stream_output(b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n')


def test_stream_chunk_detector_ignores_responses_api_status_prelude():
    assert not chunk_contains_meaningful_stream_output(b"event: response.created\n")
    assert not chunk_contains_meaningful_stream_output(
        b'data: {"type":"response.created","response":{"status":"in_progress","output":[],"error":null}}\n'
    )
    assert not chunk_contains_meaningful_stream_output(
        b'data: {"type":"response.in_progress","response":{"status":"in_progress","output":[],"error":null}}\n'
    )


def test_stream_chunk_detector_ignores_openrouter_processing_comments():
    assert not chunk_contains_meaningful_stream_output(b': OPENROUTER PROCESSING\n\n')


def test_stream_chunk_detector_detects_responses_api_output_delta():
    assert chunk_contains_meaningful_stream_output(b'data: {"type":"response.output_text.delta","delta":"hello"}\n')


def test_stream_chunk_detector_detects_openai_and_ollama_output_content():
    assert chunk_contains_meaningful_stream_output(b'data: {"choices":[{"delta":{"content":"hello"}}]}\n')
    assert not chunk_contains_meaningful_stream_output(b'{"message":{"role":"assistant","content":""},"done":false}\n')
    assert chunk_contains_meaningful_stream_output(b'{"message":{"role":"assistant","content":"hello"},"done":false}\n')


def test_stream_iterator_allows_slow_first_chunk_before_idle_timeout_starts():
    async def consume():
        chunks = []
        async for chunk in iterate_stream_with_post_first_chunk_timeout(
            delayed_stream([(0.05, b"first"), (0.01, b"second")]),
            timeout_seconds=0.1,
        ):
            chunks.append(chunk)

        return chunks

    assert asyncio.run(consume()) == [b"first", b"second"]


def test_stream_iterator_waits_for_first_meaningful_chunk_before_idle_timeout_starts():
    prelude = b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n'
    content = b'data: {"choices":[{"delta":{"content":"hello"}}]}\n'

    async def consume():
        chunks = []
        async for chunk in iterate_stream_with_post_first_chunk_timeout(
            delayed_stream(
                [
                    (0, prelude),
                    (0, b"\n"),
                    (0.05, content),
                    (0, b"\n"),
                ]
            ),
            timeout_seconds=0.01,
            timeout_starts_after_chunk=chunk_contains_meaningful_stream_output,
        ):
            chunks.append(chunk)

        return chunks

    assert asyncio.run(consume()) == [prelude, b"\n", content, b"\n"]


def test_stream_iterator_waits_for_first_meaningful_responses_api_output():
    prelude_event = b"event: response.created\n"
    prelude_data = b'data: {"type":"response.created","response":{"status":"in_progress","output":[],"error":null}}\n'
    content = b'data: {"type":"response.output_text.delta","delta":"hello"}\n'

    async def consume():
        chunks = []
        async for chunk in iterate_stream_with_post_first_chunk_timeout(
            delayed_stream(
                [
                    (0, prelude_event),
                    (0, prelude_data),
                    (0.05, content),
                ]
            ),
            timeout_seconds=0.01,
            timeout_starts_after_chunk=chunk_contains_meaningful_stream_output,
        ):
            chunks.append(chunk)

        return chunks

    assert asyncio.run(consume()) == [prelude_event, prelude_data, content]


def test_stream_iterator_times_out_after_non_meaningful_openrouter_comments():
    comment = b': OPENROUTER PROCESSING\n'
    chunks = []

    async def consume():
        async for chunk in iterate_stream_with_post_first_chunk_timeout(
            delayed_stream(
                [
                    (0, comment),
                    (0, b'\n'),
                    (0.006, comment),
                    (0, b'\n'),
                    (0.006, comment),
                ]
            ),
            timeout_seconds=0.01,
            timeout_starts_after_chunk=chunk_contains_meaningful_stream_output,
            pre_meaningful_timeout_seconds=0.01,
        ):
            chunks.append(chunk)

    with pytest.raises(asyncio.TimeoutError, match="did not produce meaningful output within 0.01 seconds"):
        asyncio.run(consume())

    assert chunks[:2] == [comment, b'\n']
    assert all(chunk in (comment, b'\n') for chunk in chunks)


def test_stream_iterator_times_out_after_first_chunk_idle_gap():
    chunks = []

    async def consume():
        async for chunk in iterate_stream_with_post_first_chunk_timeout(
            delayed_stream([(0, b"first"), (0.05, b"second")]),
            timeout_seconds=0.01,
        ):
            chunks.append(chunk)

    with pytest.raises(asyncio.TimeoutError, match="stalled for 0.01 seconds"):
        asyncio.run(consume())

    assert chunks == [b"first"]


def test_stream_iterator_times_out_after_meaningful_chunk_idle_gap():
    prelude = b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n'
    content = b'data: {"choices":[{"delta":{"content":"hello"}}]}\n'
    chunks = []

    async def consume():
        async for chunk in iterate_stream_with_post_first_chunk_timeout(
            delayed_stream(
                [
                    (0, prelude),
                    (0, b"\n"),
                    (0.001, content),
                    (0, b"\n"),
                    (0.05, b'data: {"choices":[{"delta":{"content":"again"}}]}\n'),
                ]
            ),
            timeout_seconds=0.01,
            timeout_starts_after_chunk=chunk_contains_meaningful_stream_output,
        ):
            chunks.append(chunk)

    with pytest.raises(asyncio.TimeoutError, match="stalled for 0.01 seconds"):
        asyncio.run(consume())

    assert chunks == [prelude, b"\n", content, b"\n"]
