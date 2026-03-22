import asyncio

from fastapi import HTTPException

import open_webui.utils.error_handling as error_handling


def test_get_exception_message_uses_http_exception_detail():
    exc = HTTPException(status_code=500, detail="Open WebUI: Server Connection Error")

    assert (
        error_handling.get_exception_message(exc)
        == "Open WebUI: Server Connection Error"
    )


def test_get_exception_message_formats_timeout_error():
    assert (
        error_handling.get_exception_message(
            asyncio.TimeoutError(), request_timeout_seconds=300
        )
        == "Upstream response exceeded the 300-second request timeout."
    )


def test_get_exception_message_preserves_explicit_timeout_message():
    exc = asyncio.TimeoutError(
        "Upstream streaming response stalled for 300 seconds without receiving data."
    )

    assert (
        error_handling.get_exception_message(exc, request_timeout_seconds=300)
        == "Upstream streaming response stalled for 300 seconds without receiving data."
    )


def test_get_exception_message_falls_back_to_exception_type_for_blank_errors():
    assert error_handling.get_exception_message(Exception()) == "Exception."
