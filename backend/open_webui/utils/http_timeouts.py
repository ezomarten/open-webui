import asyncio
import json

from collections.abc import Callable
from typing import Any

import aiohttp

DEFAULT_STREAM_CONNECT_TIMEOUT_SECONDS = 30


def build_upstream_request_timeout(timeout_seconds: int | None, stream: bool = False) -> aiohttp.ClientTimeout:
    if not stream:
        return aiohttp.ClientTimeout(total=timeout_seconds)

    sock_connect_timeout = DEFAULT_STREAM_CONNECT_TIMEOUT_SECONDS
    if timeout_seconds is not None:
        sock_connect_timeout = min(sock_connect_timeout, timeout_seconds)

    return aiohttp.ClientTimeout(
        total=None,
        sock_connect=sock_connect_timeout,
        sock_read=None,
    )


def get_stream_idle_timeout_message(timeout_seconds: int | None) -> str:
    if timeout_seconds:
        return "Upstream streaming response stalled " f"for {timeout_seconds} seconds without receiving data."

    return "Upstream streaming response stalled without receiving data."


def _is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _tool_call_has_meaningful_output(tool_call: Any) -> bool:
    if not isinstance(tool_call, dict):
        return False

    if _is_non_empty_text(tool_call.get("arguments")):
        return True

    function = tool_call.get("function")
    if isinstance(function, dict) and _is_non_empty_text(function.get("arguments")):
        return True

    return False


def _extract_stream_payloads(chunk_text: str) -> list[str]:
    stripped_text = chunk_text.strip()
    if not stripped_text:
        return []

    payloads = []
    saw_data_prefix = False
    plain_payloads = []

    for raw_line in chunk_text.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith(":")
            or line.startswith("event:")
            or line.startswith("id:")
            or line.startswith("retry:")
        ):
            continue

        if line.startswith("data:"):
            saw_data_prefix = True
            payload = line[5:].strip()
            if payload:
                payloads.append(payload)
            continue

        plain_payloads.append(line)

    if saw_data_prefix:
        return payloads

    return plain_payloads


def _payload_contains_meaningful_stream_output(payload: Any) -> bool:
    if _is_non_empty_text(payload):
        return True

    if isinstance(payload, list):
        return any(_payload_contains_meaningful_stream_output(item) for item in payload)

    if not isinstance(payload, dict):
        return False

    for key in (
        "content",
        "text",
        "delta",
        "response",
        "reasoning",
        "reasoning_content",
        "reasoning_text",
        "reasoning_summary_text",
        "output_text",
        "arguments",
        "refusal",
    ):
        if _is_non_empty_text(payload.get(key)):
            return True

    tool_calls = payload.get("tool_calls")
    if isinstance(tool_calls, list) and any(_tool_call_has_meaningful_output(tool_call) for tool_call in tool_calls):
        return True

    function_call = payload.get("function_call")
    if _tool_call_has_meaningful_output(function_call):
        return True

    for key in (
        "choices",
        "delta",
        "message",
        "item",
        "items",
        "output",
        "content",
        "response",
        "data",
        "part",
        "parts",
    ):
        value = payload.get(key)
        if isinstance(value, (dict, list)) and _payload_contains_meaningful_stream_output(value):
            return True

    return False


def chunk_contains_meaningful_stream_output(chunk: Any) -> bool:
    if isinstance(chunk, bytes):
        chunk_text = chunk.decode("utf-8", errors="ignore")
    elif isinstance(chunk, str):
        chunk_text = chunk
    else:
        return True

    payloads = _extract_stream_payloads(chunk_text)
    if not payloads:
        return False

    for payload_text in payloads:
        if payload_text == "[DONE]":
            return True

        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            return True

        if _payload_contains_meaningful_stream_output(payload):
            return True

    return False


async def iterate_stream_with_post_first_chunk_timeout(
    stream,
    timeout_seconds: int | None = None,
    timeout_starts_after_chunk: Callable[[Any], bool] | None = None,
):
    stream_iter = stream.__aiter__()
    timeout_started = False

    if timeout_starts_after_chunk is None:
        timeout_starts_after_chunk = lambda _chunk: True

    while True:
        try:
            if timeout_started and timeout_seconds is not None:
                chunk = await asyncio.wait_for(anext(stream_iter), timeout=timeout_seconds)
            else:
                chunk = await anext(stream_iter)
        except StopAsyncIteration:
            break
        except asyncio.TimeoutError as exc:
            raise asyncio.TimeoutError(get_stream_idle_timeout_message(timeout_seconds)) from exc

        if not timeout_started and timeout_starts_after_chunk(chunk):
            timeout_started = True

        yield chunk
