from types import SimpleNamespace

from open_webui.utils.web_search import collect_limited_search_results


def _result(link: str, title: str = 'title', snippet: str = 'snippet'):
    return SimpleNamespace(link=link, title=title, snippet=snippet)


def test_collect_limited_search_results_applies_global_limit_across_queries():
    search_results = [
        [
            _result('https://example.com/1'),
            _result('https://example.com/2'),
        ],
        [
            _result('https://example.com/3'),
            _result('https://example.com/4'),
        ],
    ]

    result_items, urls = collect_limited_search_results(search_results, max_results=3)

    assert urls == [
        'https://example.com/1',
        'https://example.com/2',
        'https://example.com/3',
    ]
    assert [item.link for item in result_items] == urls


def test_collect_limited_search_results_deduplicates_overlapping_queries():
    search_results = [
        [
            _result('https://example.com/1'),
            _result('https://example.com/2'),
        ],
        [
            _result('https://example.com/2'),
            _result('https://example.com/3'),
        ],
    ]

    result_items, urls = collect_limited_search_results(search_results, max_results=3)

    assert urls == [
        'https://example.com/1',
        'https://example.com/2',
        'https://example.com/3',
    ]
    assert [item.link for item in result_items] == urls
