"""Source-grep regression tests guarding the web-search-result-count fork wiring.

``collect_limited_search_results`` in ``open_webui.utils.web_search`` has unit
tests under ``test_web_search.py``. This wiring test protects the
integration point in ``routers/retrieval.py`` (see FORK_NOTES.md,
maintenance record 2026-05-26).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SENTINEL = '# fork:web-search-result-count'


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_web_search_helper_carries_sentinel():
    source = _read('backend', 'open_webui', 'utils', 'web_search.py')

    assert SENTINEL in source
    assert 'def collect_limited_search_results(' in source


def test_retrieval_router_uses_collect_limited_search_results():
    source = _read('backend', 'open_webui', 'routers', 'retrieval.py')

    assert 'from open_webui.utils.web_search import collect_limited_search_results' in source
    assert 'collect_limited_search_results(' in source
    assert 'WEB_SEARCH_RESULT_COUNT' in source
    assert SENTINEL in source
