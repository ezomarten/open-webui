import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_session
from open_webui.models.chats import Chats
from open_webui.models.public_shares import (
    PublicShareAccessResponse,
    PublicShareListResponse,
    PublicShareSnapshotResponse,
    PublicShares,
)
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user


log = logging.getLogger(__name__)

router = APIRouter()


def _get_public_share_base_url(request: Request) -> str:
    public_share_base_url = str(getattr(request.app.state, "PUBLIC_SHARE_BASE_URL", "") or "")
    if not public_share_base_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return public_share_base_url


def _assert_share_permission(request: Request, user) -> None:
    if user.role != "admin" and not has_permission(
        user.id, "chat.share", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


def _set_public_share_headers(response: Response) -> None:
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-store"


@router.get("/list", response_model=PublicShareListResponse)
async def get_public_share_list(
    request: Request,
    page: Optional[int] = 1,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    public_share_base_url = _get_public_share_base_url(request)
    _assert_share_permission(request, user)

    page = max(1, page or 1)
    limit = 60
    skip = (page - 1) * limit
    filter = {
        **({"query": query} if query else {}),
        **({"order_by": order_by} if order_by else {}),
        **({"direction": direction} if direction else {}),
    }

    return PublicShares.get_public_share_list_by_user_id(
        user.id,
        public_share_base_url,
        filter=filter,
        skip=skip,
        limit=limit,
        db=db,
    )


@router.get("/chats/{chat_id}", response_model=PublicShareAccessResponse)
async def get_public_share_by_chat_id(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    public_share_base_url = _get_public_share_base_url(request)
    _assert_share_permission(request, user)

    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id, db=db)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    public_share = PublicShares.get_public_share_by_chat_id_and_user_id(chat_id, user.id, db=db)
    if public_share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return PublicShareAccessResponse(
        id=public_share.id,
        chat_id=public_share.chat_id,
        title=public_share.title,
        url=f"{public_share_base_url.rstrip('/')}/p/{public_share.id}",
        message_count=public_share.message_count,
        source_chat_updated_at=public_share.source_chat_updated_at,
        created_at=public_share.created_at,
        updated_at=public_share.updated_at,
        is_stale=chat.updated_at > public_share.source_chat_updated_at,
    )


@router.post("/chats/{chat_id}", response_model=PublicShareAccessResponse)
async def upsert_public_share_by_chat_id(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    public_share_base_url = _get_public_share_base_url(request)
    _assert_share_permission(request, user)

    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id, db=db)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        return PublicShares.upsert_public_share(
            chat,
            user.id,
            public_share_base_url,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.delete("/chats/{chat_id}", response_model=bool)
async def delete_public_share_by_chat_id(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    _get_public_share_base_url(request)
    _assert_share_permission(request, user)

    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id, db=db)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return PublicShares.delete_public_share_by_chat_id_and_user_id(chat_id, user.id, db=db)


@router.get("/{public_share_id}", response_model=PublicShareSnapshotResponse)
async def get_public_share_snapshot(
    request: Request,
    response: Response,
    public_share_id: str,
    db: Session = Depends(get_session),
):
    _get_public_share_base_url(request)
    public_share = PublicShares.get_public_share_by_id(public_share_id, db=db)
    if public_share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    _set_public_share_headers(response)
    snapshot = public_share.snapshot_json or {}

    return PublicShareSnapshotResponse(
        id=public_share.id,
        title=str(snapshot.get("title") or public_share.title),
        models=list(snapshot.get("models") or []),
        messages=list(snapshot.get("messages") or []),
        message_count=public_share.message_count,
        created_at=public_share.created_at,
        updated_at=public_share.updated_at,
    )


@router.head("/{public_share_id}")
async def head_public_share_snapshot(
    request: Request,
    public_share_id: str,
    db: Session = Depends(get_session),
):
    _get_public_share_base_url(request)
    public_share = PublicShares.get_public_share_by_id(public_share_id, db=db)
    if public_share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    response = Response(status_code=status.HTTP_200_OK)
    _set_public_share_headers(response)
    return response