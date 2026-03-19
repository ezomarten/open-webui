from typing import Any, Sequence


def _get_search_result_link(item: Any) -> str | None:
    if isinstance(item, dict):
        return item.get("link") or item.get("url") or item.get("href")

    return getattr(item, "link", None)


def collect_limited_search_results(
    search_results: Sequence[Sequence[Any] | None], max_results: int | None
) -> tuple[list[Any], list[str]]:
    result_items: list[Any] = []
    urls: list[str] = []
    seen_urls: set[str] = set()
    unlimited = max_results is None or max_results <= 0

    for result in search_results:
        if not result:
            continue

        for item in result:
            link = _get_search_result_link(item)
            if not link or link in seen_urls:
                continue

            seen_urls.add(link)
            result_items.append(item)
            urls.append(link)

            if not unlimited and len(urls) >= max_results:
                return result_items, urls

    return result_items, urls
