"""Source-grep regression tests guarding the OpenRouter ZDR fork wiring.

The helper module in ``open_webui.utils.openrouter`` has its own unit tests
under ``test_openrouter_zdr.py``. These wiring tests instead protect the
integration points that have silently disappeared during past upstream syncs
(see FORK_NOTES.md, maintenance record 2026-05-26). If any of these
assertions fail, the ZDR feature is broken in the running product even when
the helper unit tests still pass.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _read_repo_file(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_openai_router_imports_zdr_helpers():
    source = _read_repo_file('backend', 'open_webui', 'routers', 'openai.py')

    assert 'from open_webui.utils.openrouter import' in source
    assert 'apply_openrouter_zdr_preferences' in source
    assert 'get_models_list_url' in source
    assert 'is_openrouter_zdr_model_list_enabled' in source
    assert 'normalize_models_response' in source


def test_openai_router_uses_zdr_for_model_discovery():
    source = _read_repo_file('backend', 'open_webui', 'routers', 'openai.py')

    # The hard-coded ``f'{url}/models'`` calls used for model discovery and
    # verify-connection must be routed through ``get_models_list_url`` so the
    # OpenRouter ZDR endpoint is honored.
    assert "f'{url}/models'" not in source
    assert source.count('get_models_list_url(url, api_config') >= 3
    # Response normalization must run for both verify-connection and the
    # multi-URL ``/models`` aggregator.
    assert 'normalize_models_response(url, api_config' in source
    assert 'is_openrouter_zdr_model_list_enabled(url, api_config)' in source


def test_openai_router_applies_zdr_preferences_to_outgoing_payloads():
    source = _read_repo_file('backend', 'open_webui', 'routers', 'openai.py')

    # ``apply_openrouter_zdr_preferences`` must be invoked for chat
    # completions, the Responses API, and the legacy passthrough proxy so
    # that ``provider.zdr`` is forced server-side.
    assert source.count('apply_openrouter_zdr_preferences(url, api_config') >= 3


def test_add_connection_modal_exposes_zdr_toggle():
    source = _read_repo_file('src', 'lib', 'components', 'AddConnectionModal.svelte')

    assert 'openrouterZdrOnly' in source
    assert 'isOpenRouterUrl' in source
    assert 'openrouter_zdr_only' in source
    assert "$i18n.t('OpenRouter ZDR Only')" in source
    assert ('Use OpenRouter Zero Retention endpoints for model discovery and force provider.zdr on requests') in source
    assert '{{url}}/endpoints/zdr' in source


def test_openrouter_zdr_ja_jp_translations_are_not_empty():
    translations = json.loads(_read_repo_file('src', 'lib', 'i18n', 'locales', 'ja-JP', 'translation.json'))
    required_keys = [
        'OpenRouter ZDR Only',
        'Use OpenRouter Zero Retention endpoints for model discovery and force provider.zdr on requests',
        'Leave empty to include all models from "{{url}}/endpoints/zdr" endpoint',
    ]

    for key in required_keys:
        assert key in translations, f'missing ja-JP key: {key}'
        assert translations[key], f'empty ja-JP translation for: {key}'
