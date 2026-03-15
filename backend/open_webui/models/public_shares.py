import time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Integer, JSON, Text
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context
from open_webui.utils.public_share import (
    PUBLIC_SHARE_SCHEMA_VERSION,
    build_public_share_snapshot,
    build_public_share_url,
    new_public_share_id,
)


class PublicShare(Base):
    __tablename__ = "public_share"

    id = Column(Text, primary_key=True, unique=True)
    chat_id = Column(
        Text, ForeignKey("chat.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user_id = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    message_count = Column(Integer, nullable=False, default=0)
    source_chat_updated_at = Column(BigInteger, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (Index("public_share_user_updated_idx", "user_id", "updated_at"),)


class PublicShareModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    user_id: str
    title: str
    snapshot_json: dict
    message_count: int
    source_chat_updated_at: int
    created_at: int
    updated_at: int


class PublicShareAccessResponse(BaseModel):
    id: str
    chat_id: str
    title: str
    url: str
    message_count: int
    source_chat_updated_at: int
    created_at: int
    updated_at: int
    is_stale: bool


class PublicShareListItemResponse(BaseModel):
    id: str
    chat_id: str
    title: str
    url: str
    message_count: int
    created_at: int
    updated_at: int


class PublicShareListResponse(BaseModel):
    items: list[PublicShareListItemResponse]
    total: int


class PublicShareSnapshotResponse(BaseModel):
    id: str
    title: str
    models: list[str]
    messages: list[dict]
    message_count: int
    created_at: int
    updated_at: int


class PublicShareTable:
    def _is_snapshot_schema_stale(self, public_share: PublicShare) -> bool:
        snapshot = getattr(public_share, "snapshot_json", None) or {}

        try:
            snapshot_schema_version = int(snapshot.get("schema_version") or 0)
        except (TypeError, ValueError, AttributeError):
            snapshot_schema_version = 0

        return snapshot_schema_version < PUBLIC_SHARE_SCHEMA_VERSION

    def _to_access_response(
        self,
        public_share: PublicShare,
        public_share_base_url: str,
        source_chat_updated_at: Optional[int] = None,
    ) -> PublicShareAccessResponse:
        effective_source_updated_at = (
            source_chat_updated_at
            if source_chat_updated_at is not None
            else public_share.source_chat_updated_at
        )
        return PublicShareAccessResponse(
            id=public_share.id,
            chat_id=public_share.chat_id,
            title=public_share.title,
            url=build_public_share_url(public_share_base_url, public_share.id),
            message_count=public_share.message_count,
            source_chat_updated_at=public_share.source_chat_updated_at,
            created_at=public_share.created_at,
            updated_at=public_share.updated_at,
            is_stale=(
                effective_source_updated_at > public_share.source_chat_updated_at
                or self._is_snapshot_schema_stale(public_share)
            ),
        )

    def _to_list_item(
        self, public_share: PublicShare, public_share_base_url: str
    ) -> PublicShareListItemResponse:
        return PublicShareListItemResponse(
            id=public_share.id,
            chat_id=public_share.chat_id,
            title=public_share.title,
            url=build_public_share_url(public_share_base_url, public_share.id),
            message_count=public_share.message_count,
            created_at=public_share.created_at,
            updated_at=public_share.updated_at,
        )

    def get_public_share_by_chat_id_and_user_id(
        self, chat_id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[PublicShareModel]:
        with get_db_context(db) as db:
            public_share = (
                db.query(PublicShare)
                .filter_by(chat_id=chat_id, user_id=user_id)
                .first()
            )
            return (
                PublicShareModel.model_validate(public_share) if public_share else None
            )

    def get_public_share_by_id(
        self, public_share_id: str, db: Optional[Session] = None
    ) -> Optional[PublicShareModel]:
        with get_db_context(db) as db:
            public_share = db.get(PublicShare, public_share_id)
            return (
                PublicShareModel.model_validate(public_share) if public_share else None
            )

    def get_public_share_list_by_user_id(
        self,
        user_id: str,
        public_share_base_url: str,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> PublicShareListResponse:
        with get_db_context(db) as db:
            query = db.query(PublicShare).filter_by(user_id=user_id)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(PublicShare.title.ilike(f"%{query_key}%"))

                order_by = filter.get("order_by")
                direction = str(filter.get("direction") or "desc").lower()
                order_field = getattr(PublicShare, order_by, None) if order_by else None
                if order_field is not None:
                    query = query.order_by(
                        order_field.asc() if direction == "asc" else order_field.desc(),
                        PublicShare.id,
                    )
                else:
                    query = query.order_by(
                        PublicShare.updated_at.desc(), PublicShare.id
                    )
            else:
                query = query.order_by(PublicShare.updated_at.desc(), PublicShare.id)

            total = query.count()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            items = query.all()
            return PublicShareListResponse(
                items=[
                    self._to_list_item(item, public_share_base_url) for item in items
                ],
                total=total,
            )

    def upsert_public_share(
        self,
        chat: Any,
        user_id: str,
        public_share_base_url: str,
        db: Optional[Session] = None,
    ) -> PublicShareAccessResponse:
        with get_db_context(db) as db:
            snapshot = build_public_share_snapshot(chat)
            now = int(time.time())
            chat_updated_at = int(getattr(chat, "updated_at", now) or now)
            title = str(
                snapshot.get("title") or getattr(chat, "title", "Untitled Chat")
            )
            message_count = len(snapshot.get("messages") or [])

            public_share = (
                db.query(PublicShare)
                .filter_by(chat_id=getattr(chat, "id"), user_id=user_id)
                .first()
            )

            if public_share is None:
                public_share = PublicShare(
                    id=new_public_share_id(),
                    chat_id=getattr(chat, "id"),
                    user_id=user_id,
                    title=title,
                    snapshot_json=snapshot,
                    message_count=message_count,
                    source_chat_updated_at=chat_updated_at,
                    created_at=now,
                    updated_at=now,
                )
                db.add(public_share)
            else:
                public_share.title = title
                public_share.snapshot_json = snapshot
                public_share.message_count = message_count
                public_share.source_chat_updated_at = chat_updated_at
                public_share.updated_at = now

            db.commit()
            db.refresh(public_share)

            return self._to_access_response(
                public_share, public_share_base_url, chat_updated_at
            )

    def delete_public_share_by_chat_id_and_user_id(
        self, chat_id: str, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(PublicShare).filter_by(
                    chat_id=chat_id, user_id=user_id
                ).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_public_share_by_chat_id(
        self, chat_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(PublicShare).filter_by(chat_id=chat_id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_public_shares_by_chat_ids(
        self, chat_ids: list[str], db: Optional[Session] = None
    ) -> bool:
        if len(chat_ids) == 0:
            return True

        try:
            with get_db_context(db) as db:
                db.query(PublicShare).filter(PublicShare.chat_id.in_(chat_ids)).delete(
                    synchronize_session=False
                )
                db.commit()
                return True
        except Exception:
            return False

    def delete_public_shares_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(PublicShare).filter_by(user_id=user_id).delete()
                db.commit()
                return True
        except Exception:
            return False


PublicShares = PublicShareTable()
