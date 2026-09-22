import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from open_webui.routers import public_shares as public_shares_router


def _build_request():
    # v0.10.x removed app.state.config: only PUBLIC_SHARE_BASE_URL lives in
    # app state now. Keep this mock free of `config` so a regression back to
    # `request.app.state.config.*` fails loudly here instead of in production.
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(PUBLIC_SHARE_BASE_URL='https://share.example.com'))
    )


@pytest.fixture
def patch_config(monkeypatch):
    """Patch Config.get so 'ui.enable_public_chat_sharing' is enabled and
    'user.permissions' resolves to an empty default dict."""

    async def fake_get(key, default=None):
        if key == 'ui.enable_public_chat_sharing':
            return True
        if key == 'user.permissions':
            return {}
        return default

    monkeypatch.setattr(public_shares_router.Config, 'get', staticmethod(fake_get))


def test_upsert_public_share_route_awaits_chat_lookup(monkeypatch, patch_config):
    chat = SimpleNamespace(id='chat-1')
    user = SimpleNamespace(id='user-1', role='admin')
    request = _build_request()
    chat_lookup = AsyncMock(return_value=chat)
    captured = {}

    def fake_upsert_public_share(chat_arg, user_id, public_share_base_url, db=None):
        captured['chat'] = chat_arg
        captured['user_id'] = user_id
        captured['public_share_base_url'] = public_share_base_url
        captured['db'] = db
        assert not inspect.iscoroutine(chat_arg)
        return SimpleNamespace(id='share-1')

    monkeypatch.setattr(public_shares_router.Chats, 'get_chat_by_id_and_user_id', chat_lookup)
    monkeypatch.setattr(public_shares_router.PublicShares, 'upsert_public_share', fake_upsert_public_share)

    result = asyncio.run(
        public_shares_router.upsert_public_share_by_chat_id(
            request,
            'chat-1',
            user=user,
            db='sync-db',
        )
    )

    chat_lookup.assert_awaited_once_with('chat-1', 'user-1')
    assert captured == {
        'chat': chat,
        'user_id': 'user-1',
        'public_share_base_url': 'https://share.example.com',
        'db': 'sync-db',
    }
    assert result.id == 'share-1'


def test_get_public_share_route_awaits_chat_lookup(monkeypatch, patch_config):
    chat = SimpleNamespace(id='chat-1', updated_at=10)
    user = SimpleNamespace(id='user-1', role='admin')
    request = _build_request()
    chat_lookup = AsyncMock(return_value=chat)
    public_share = SimpleNamespace(
        id='share-1',
        chat_id='chat-1',
        title='Shared Chat',
        message_count=2,
        source_chat_updated_at=10,
        created_at=1,
        updated_at=2,
        snapshot_json={'schema_version': public_shares_router.PUBLIC_SHARE_SCHEMA_VERSION},
    )

    monkeypatch.setattr(public_shares_router.Chats, 'get_chat_by_id_and_user_id', chat_lookup)
    monkeypatch.setattr(
        public_shares_router.PublicShares,
        'get_public_share_by_chat_id_and_user_id',
        lambda chat_id, user_id, db=None: public_share,
    )

    result = asyncio.run(
        public_shares_router.get_public_share_by_chat_id(
            request,
            'chat-1',
            user=user,
            db='sync-db',
        )
    )

    chat_lookup.assert_awaited_once_with('chat-1', 'user-1')
    assert result.id == 'share-1'
    assert result.url == 'https://share.example.com/p/share-1'
    assert result.is_stale is False


def test_delete_public_share_route_awaits_chat_lookup(monkeypatch, patch_config):
    chat = SimpleNamespace(id='chat-1')
    user = SimpleNamespace(id='user-1', role='admin')
    request = _build_request()
    chat_lookup = AsyncMock(return_value=chat)

    monkeypatch.setattr(public_shares_router.Chats, 'get_chat_by_id_and_user_id', chat_lookup)
    monkeypatch.setattr(
        public_shares_router.PublicShares,
        'delete_public_share_by_chat_id_and_user_id',
        lambda chat_id, user_id, db=None: True,
    )

    result = asyncio.run(
        public_shares_router.delete_public_share_by_chat_id(
            request,
            'chat-1',
            user=user,
            db='sync-db',
        )
    )

    chat_lookup.assert_awaited_once_with('chat-1', 'user-1')
    assert result is True


def test_non_admin_without_share_permission_is_rejected(monkeypatch, patch_config):
    """has_permission is async and default permissions come from persistent
    config; a non-admin user without 'chat.share' must get a 403, and the
    await must actually happen (a missing await would silently pass)."""
    request = _build_request()
    user = SimpleNamespace(id='user-2', role='user')
    has_permission = AsyncMock(return_value=False)
    monkeypatch.setattr(public_shares_router, 'has_permission', has_permission)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(public_shares_router._assert_share_permission(request, user))

    assert excinfo.value.status_code == 403
    has_permission.assert_awaited_once_with('user-2', 'chat.share', {})


def test_non_admin_with_share_permission_passes(monkeypatch, patch_config):
    request = _build_request()
    user = SimpleNamespace(id='user-2', role='user')
    has_permission = AsyncMock(return_value=True)
    monkeypatch.setattr(public_shares_router, 'has_permission', has_permission)

    asyncio.run(public_shares_router._assert_share_permission(request, user))

    has_permission.assert_awaited_once()


def test_disabled_public_sharing_returns_404(monkeypatch):
    async def fake_get(key, default=None):
        if key == 'ui.enable_public_chat_sharing':
            return False
        return default

    monkeypatch.setattr(public_shares_router.Config, 'get', staticmethod(fake_get))
    request = _build_request()

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(public_shares_router._get_public_share_base_url(request))

    assert excinfo.value.status_code == 404


def test_missing_app_state_base_url_disables_sharing(monkeypatch):
    """If initialize_runtime_config has not set PUBLIC_SHARE_BASE_URL the
    helper must 404 instead of building links from an empty base."""

    async def fake_get(key, default=None):
        if key == 'ui.enable_public_chat_sharing':
            return True
        return default

    monkeypatch.setattr(public_shares_router.Config, 'get', staticmethod(fake_get))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(public_shares_router._get_public_share_base_url(request))

    assert excinfo.value.status_code == 404
