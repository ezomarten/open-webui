import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

from open_webui.routers import public_shares as public_shares_router


def _build_request():
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                PUBLIC_SHARE_BASE_URL="https://share.example.com",
                config=SimpleNamespace(
                    ENABLE_PUBLIC_CHAT_SHARING=True,
                    USER_PERMISSIONS={},
                ),
            )
        )
    )


def test_upsert_public_share_route_awaits_chat_lookup(monkeypatch):
    chat = SimpleNamespace(id="chat-1")
    user = SimpleNamespace(id="user-1", role="admin")
    request = _build_request()
    chat_lookup = AsyncMock(return_value=chat)
    captured = {}

    def fake_upsert_public_share(chat_arg, user_id, public_share_base_url, db=None):
        captured["chat"] = chat_arg
        captured["user_id"] = user_id
        captured["public_share_base_url"] = public_share_base_url
        captured["db"] = db
        assert not inspect.iscoroutine(chat_arg)
        return SimpleNamespace(id="share-1")

    monkeypatch.setattr(public_shares_router.Chats, "get_chat_by_id_and_user_id", chat_lookup)
    monkeypatch.setattr(public_shares_router.PublicShares, "upsert_public_share", fake_upsert_public_share)

    result = asyncio.run(
        public_shares_router.upsert_public_share_by_chat_id(
            request,
            "chat-1",
            user=user,
            db="sync-db",
        )
    )

    chat_lookup.assert_awaited_once_with("chat-1", "user-1")
    assert captured == {
        "chat": chat,
        "user_id": "user-1",
        "public_share_base_url": "https://share.example.com",
        "db": "sync-db",
    }
    assert result.id == "share-1"


def test_get_public_share_route_awaits_chat_lookup(monkeypatch):
    chat = SimpleNamespace(id="chat-1", updated_at=10)
    user = SimpleNamespace(id="user-1", role="admin")
    request = _build_request()
    chat_lookup = AsyncMock(return_value=chat)
    public_share = SimpleNamespace(
        id="share-1",
        chat_id="chat-1",
        title="Shared Chat",
        message_count=2,
        source_chat_updated_at=10,
        created_at=1,
        updated_at=2,
        snapshot_json={"schema_version": public_shares_router.PUBLIC_SHARE_SCHEMA_VERSION},
    )

    monkeypatch.setattr(public_shares_router.Chats, "get_chat_by_id_and_user_id", chat_lookup)
    monkeypatch.setattr(
        public_shares_router.PublicShares,
        "get_public_share_by_chat_id_and_user_id",
        lambda chat_id, user_id, db=None: public_share,
    )

    result = asyncio.run(
        public_shares_router.get_public_share_by_chat_id(
            request,
            "chat-1",
            user=user,
            db="sync-db",
        )
    )

    chat_lookup.assert_awaited_once_with("chat-1", "user-1")
    assert result.id == "share-1"
    assert result.url == "https://share.example.com/p/share-1"
    assert result.is_stale is False


def test_delete_public_share_route_awaits_chat_lookup(monkeypatch):
    chat = SimpleNamespace(id="chat-1")
    user = SimpleNamespace(id="user-1", role="admin")
    request = _build_request()
    chat_lookup = AsyncMock(return_value=chat)

    monkeypatch.setattr(public_shares_router.Chats, "get_chat_by_id_and_user_id", chat_lookup)
    monkeypatch.setattr(
        public_shares_router.PublicShares,
        "delete_public_share_by_chat_id_and_user_id",
        lambda chat_id, user_id, db=None: True,
    )

    result = asyncio.run(
        public_shares_router.delete_public_share_by_chat_id(
            request,
            "chat-1",
            user=user,
            db="sync-db",
        )
    )

    chat_lookup.assert_awaited_once_with("chat-1", "user-1")
    assert result is True
