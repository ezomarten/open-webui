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

    # v0.9.6 renamed PersistentConfig → ConfigVar; match either form
    assert ('PUBLIC_SHARE_BASE_URL = PersistentConfig(' in source
            or 'PUBLIC_SHARE_BASE_URL = ConfigVar(' in source)
    assert ('ENABLE_PUBLIC_CHAT_SHARING = PersistentConfig(' in source
            or 'ENABLE_PUBLIC_CHAT_SHARING = ConfigVar(' in source)
    assert "'ui.public_share_base_url'" in source
    assert "'ui.enable_public_chat_sharing'" in source


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


def test_env_source_tolerates_unreleased_changelog_heading():
    source = _read_repo_file('backend', 'open_webui', 'env.py')

    assert "heading_parts = heading_text.split(' - ', 1)" in source
    assert 'if len(heading_parts) > 1:' in source


def test_public_share_ja_jp_translations_are_not_empty():
    translations = json.loads(_read_repo_file('src', 'lib', 'i18n', 'locales', 'ja-JP', 'translation.json'))
    required_keys = [
        'Copied public link to clipboard!',
        'Copy Public Link',
        'Create Public Link',
        'Creates an anonymous read-only public page. Image attachments and public web citations are included. Other files and private citations are omitted.',
        'Enable Public Links',
        'Enter the public base URL used for anonymous public links. Leave empty to disable link generation until configured.',
        'Failed to stop public link.',
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
