import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

from open_webui.retrieval.utils import get_web_loader_timeout_seconds
from open_webui.tools.builtin import fetch_url


def _request_with_timeout(timeout_value):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    WEB_LOADER_TIMEOUT=timeout_value,
                    WEB_FETCH_MAX_CONTENT_LENGTH=None,
                )
            )
        )
    )


def test_get_web_loader_timeout_seconds_uses_fallback_when_config_missing():
    request = _request_with_timeout("")

    assert get_web_loader_timeout_seconds(request) == 30.0


def test_get_web_loader_timeout_seconds_uses_positive_config_value():
    request = _request_with_timeout("12.5")

    assert get_web_loader_timeout_seconds(request) == 12.5


def test_fetch_url_returns_timeout_error_when_fetch_exceeds_budget():
    request = _request_with_timeout("0.01")

    async def slow_to_thread(*args, **kwargs):
        await asyncio.sleep(0.05)
        return ("never reached", [])

    with patch("open_webui.tools.builtin.asyncio.to_thread", side_effect=slow_to_thread):
        result = asyncio.run(fetch_url("https://example.com", __request__=request))

    payload = json.loads(result)
    assert payload["error"] == "URL fetch timed out after 0.01 seconds"
