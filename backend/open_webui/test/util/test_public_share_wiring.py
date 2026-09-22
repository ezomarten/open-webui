import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def _read_repo_file(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding='utf8')


def test_main_source_keeps_public_share_app_wiring():
    source = _read_repo_file('backend', 'open_webui', 'main.py')

    assert 'class PublicShareHostMiddleware' in source
    assert 'app.add_middleware(PublicShareHostMiddleware, fastapi_app=app)' in source
    assert 'public_shares.router' in source
    assert "'enable_public_chat_sharing': is_public_share_enabled(" in source


def test_config_source_keeps_public_share_persistent_settings():
    source = _read_repo_file('backend', 'open_webui', 'config.py')

    # v0.10.x removed ConfigVar/PersistentConfig; config vars are now plain variables
    # registered in DEFAULT_CONFIG with dotted keys.
    assert 'PUBLIC_SHARE_BASE_URL' in source and "'ui.public_share_base_url'" in source
    assert 'ENABLE_PUBLIC_CHAT_SHARING' in source and "'ui.enable_public_chat_sharing'" in source


def test_public_shares_router_uses_post_v010_config_api():
    """Regression guard for the 2026-09 incident: public_shares.py kept
    reading ``request.app.state.config`` (removed upstream in v0.10.x) and
    calling the now-async ``has_permission`` without ``await``, so every
    public-link operation 500'd for four releases. The router must use the
    persistent-config API and await both helpers at every call site."""
    source = _read_repo_file('backend', 'open_webui', 'routers', 'public_shares.py')

    # No stale runtime API anywhere in the file (the .state.config ban is
    # enforced repo-wide by test_no_removed_state_config_api.py; here we pin
    # the *positive* wiring too).
    assert 'state.config' not in source
    assert 'from open_webui.models.config import Config' in source
    assert "await Config.get('ui.enable_public_chat_sharing')" in source
    assert "await Config.get('user.permissions')" in source
    assert 'await has_permission(' in source
    # The helpers are async and awaited at every endpoint call site.
    assert source.count('async def _get_public_share_base_url') == 1
    assert source.count('async def _assert_share_permission') == 1
    assert source.count('await _get_public_share_base_url(request)') >= 7
    assert source.count('await _assert_share_permission(request, user)') >= 4
    # Any call site missing the await would remain after stripping the good ones.
    assert '_get_public_share_base_url(request)' not in source.replace('await _get_public_share_base_url(request)', '')
    assert '_assert_share_permission(request, user)' not in source.replace(
        'await _assert_share_permission(request, user)', ''
    )
    # Sentinel for the fork wiring test contract.
    assert '# fork:public-link-settings' in source


def test_share_chat_modal_source_keeps_public_link_controls():
    source = _read_repo_file('src', 'lib', 'components', 'chat', 'ShareChatModal.svelte')

    assert 'upsertPublicShareByChatId' in source
    assert 'deletePublicShareByChatId' in source
    assert 'publicShareErrorMessage(error)' in source
    assert 'Create Public Link' in source
    assert 'Stop Public Link' in source


def test_public_shares_modal_source_translates_backend_errors():
    source = _read_repo_file('src', 'lib', 'components', 'layout', 'PublicSharesModal.svelte')

    assert 'publicShareErrorMessage(error)' in source


def test_admin_general_source_keeps_public_link_settings_block():
    # The v0.11.1-era sync silently dropped the Admin > General public-link UI
    # block while leaving the backend config wiring intact; guard the UI side too.
    source = _read_repo_file('src', 'lib', 'components', 'admin', 'Settings', 'General.svelte')

    assert 'adminConfig.ENABLE_PUBLIC_CHAT_SHARING' in source
    assert 'adminConfig.PUBLIC_SHARE_BASE_URL' in source
    assert "'Enable Public Links'" in source
    assert "'Public Link URL'" in source


def test_auths_source_keeps_public_link_admin_config_keys():
    source = _read_repo_file('backend', 'open_webui', 'routers', 'auths.py')

    assert "'ENABLE_PUBLIC_CHAT_SHARING': 'ui.enable_public_chat_sharing'" in source
    assert "'PUBLIC_SHARE_BASE_URL': 'ui.public_share_base_url'" in source
    assert 'validate_public_share_base_url' in source


def test_env_source_tolerates_unreleased_changelog_heading():
    source = _read_repo_file('backend', 'open_webui', 'env.py')

    assert "heading_parts = heading_text.split(' - ', 1)" in source
    assert 'if len(heading_parts) > 1:' in source


def test_public_share_ja_jp_translations_are_not_empty():
    translations = json.loads(_read_repo_file('src', 'lib', 'i18n', 'locales', 'ja-JP', 'translation.json'))
    required_keys = [
        'Copied public link to clipboard!',
        'Allow users to create anonymous read-only public links to their chats.',
        'Copy Public Link',
        'Create Public Link',
        'Creates an anonymous read-only public page. Image attachments and public web citations are included. Other files and private citations are omitted.',
        'Enable Public Links',
        'Enter the public base URL used for anonymous public links. Leave empty to disable link generation until configured.',
        'Failed to stop public link.',
        'Internal Server Error',
        'It may have been removed or the link may be invalid.',
        'No public messages found.',
        'Open Public Page',
        'Public link copied to clipboard.',
        'Public link stopped successfully.',
        'Public link stopped.',
        'Public Link',
        'Public Link URL',
        'Public Share',
        'Public Shares',
        'Stop Public Link',
        'This public share is unavailable',
        'This public snapshot is older than the current chat.',
        'Update and Copy Public Link',
        'You do not have permission to make this public',
        'You have no public shares.',
    ]

    for key in required_keys:
        assert translations.get(key)
        assert translations[key] != key
