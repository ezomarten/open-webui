"""Source-grep regression tests guarding the chat-timeout-msg fork wiring.

The helper module ``open_webui.utils.http_timeouts`` has unit tests under
``test_http_timeouts.py``. These wiring tests separately protect the
integration points in ``routers/openai.py`` and ``utils/misc.py`` that
silently disappeared during the v0.9.5 upstream sync (see FORK_NOTES.md,
maintenance record 2026-05-26). Without these, streaming chat completions
fall back to the upstream's blunt total-timeout and the idle-stream
diagnostic message is never raised.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '# fork:chat-timeout-msg'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_http_timeouts_helper_module_carries_sentinel():
    source = _read('backend', 'open_webui', 'utils', 'http_timeouts.py')

    # build_upstream_request_timeout + ..._for_payload + idle_timeout_message
    # + iterate_stream_with_post_first_chunk_timeout each get a sentinel.
    assert source.count(SENTINEL) >= 4


def test_openai_router_uses_payload_aware_timeout_at_chat_sites():
    source = _read('backend', 'open_webui', 'routers', 'openai.py')

    assert 'from open_webui.utils.http_timeouts import' in source
    assert 'build_upstream_request_timeout_for_payload' in source
    # Chat-completions, /responses and the generic proxy must all build the
    # payload-aware timeout so streaming requests get the idle-aware policy.
    assert source.count('build_upstream_request_timeout_for_payload(AIOHTTP_CLIENT_TIMEOUT, payload)') >= 3
    assert source.count(SENTINEL) >= 4  # import + 3 call sites


def test_misc_uses_first_chunk_idle_timeout_iterator():
    source = _read('backend', 'open_webui', 'utils', 'misc.py')

    # The shared stream wrapper used by both openai/ollama routers must
    # iterate via the fork helper so first-meaningful-chunk handling is
    # preserved.
    assert 'iterate_stream_with_post_first_chunk_timeout(' in source
    assert SENTINEL in source


def test_get_web_loader_accepts_and_forwards_timeout():
    """Guards the fetch_url Web Loader per-request timeout path. The v0.9.5
    upstream replay silently dropped the ``timeout`` parameter from
    ``get_web_loader`` while ``get_loader`` kept passing it, so ``fetch_url``
    failed at runtime with
    ``get_web_loader() got an unexpected keyword argument 'timeout'``.
    """
    web_utils = _read('backend', 'open_webui', 'retrieval', 'web', 'utils.py')
    retrieval_utils = _read('backend', 'open_webui', 'retrieval', 'utils.py')

    # Callee must declare the parameter and carry the sentinel.
    assert 'timeout: Optional[float] = None' in web_utils
    assert SENTINEL in web_utils
    # Caller must forward it under the sentinel.
    assert 'timeout=timeout,' in retrieval_utils
    assert SENTINEL in retrieval_utils
