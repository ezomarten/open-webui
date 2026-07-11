import asyncio
import inspect
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
    request = _request_with_timeout('')

    assert get_web_loader_timeout_seconds(request) == 30.0


def test_get_web_loader_timeout_seconds_uses_positive_config_value():
    request = _request_with_timeout('12.5')

    assert get_web_loader_timeout_seconds(request) == 12.5


def test_fetch_url_returns_timeout_error_when_fetch_exceeds_budget():
    request = _request_with_timeout('0.01')

    async def slow_to_thread(*args, **kwargs):
        await asyncio.sleep(0.05)
        return ('never reached', [])

    with patch('open_webui.tools.builtin.asyncio.to_thread', side_effect=slow_to_thread):
        result = asyncio.run(fetch_url('https://example.com', __request__=request))

    payload = json.loads(result)
    assert payload['error'] == 'URL fetch timed out after 0.01 seconds'


def test_get_web_loader_accepts_timeout_param():
    """Regression guard: the fork passes an explicit per-request timeout into
    get_web_loader (via get_loader). If an upstream sync drops the `timeout`
    parameter from get_web_loader's signature, fetch_url fails at runtime with
    'get_web_loader() got an unexpected keyword argument timeout'."""
    from open_webui.retrieval.web.utils import get_web_loader

    assert 'timeout' in inspect.signature(get_web_loader).parameters


def test_get_loader_forwards_timeout_to_get_web_loader():
    """Regression guard for the full integration path: get_loader must forward
    the resolved timeout to get_web_loader without raising TypeError."""
    from open_webui.retrieval import utils as retrieval_utils

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                config=SimpleNamespace(
                    ENABLE_WEB_LOADER_SSL_VERIFICATION=True,
                    WEB_LOADER_CONCURRENT_REQUESTS=2,
                    WEB_SEARCH_TRUST_ENV=False,
                    YOUTUBE_LOADER_LANGUAGE=['en'],
                    YOUTUBE_LOADER_PROXY_URL='',
                )
            )
        )
    )

    captured = {}

    def fake_get_web_loader(urls, **kwargs):
        captured.update(kwargs)
        return object()

    with patch('open_webui.retrieval.utils.get_web_loader', fake_get_web_loader):
        retrieval_utils.get_loader(request, 'https://example.com', timeout=15.0)

    assert captured.get('timeout') == 15.0
