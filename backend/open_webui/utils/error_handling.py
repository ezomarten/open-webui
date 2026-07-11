import asyncio
import json

from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException


def _stringify_error_detail(detail) -> str:
    if detail is None:
        return ''

    if isinstance(detail, str):
        return detail.strip()

    if isinstance(detail, (dict, list, tuple)):
        try:
            return json.dumps(detail, ensure_ascii=False)
        except TypeError:
            pass

    return str(detail).strip()


def get_exception_message(exc: BaseException, request_timeout_seconds: int | None = None) -> str:
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        message = _stringify_error_detail(exc.detail)
    elif isinstance(exc, asyncio.TimeoutError):
        message = _stringify_error_detail(exc)
        if not message and request_timeout_seconds:
            message = f'Upstream response exceeded the {request_timeout_seconds}-second request timeout.'
        elif not message:
            message = 'Upstream response timed out.'
    else:
        message = _stringify_error_detail(exc)

    if message:
        return message

    return f'{exc.__class__.__name__}.'
