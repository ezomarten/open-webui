import logging
import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_session
from open_webui.models.chats import Chats
from open_webui.models.files import Files
from open_webui.models.public_shares import (
    PublicShareAccessResponse,
    PublicShareListResponse,
    PublicShareSnapshotResponse,
    PublicShares,
)
from open_webui.storage.provider import Storage
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user
from open_webui.utils.public_share import (
    PUBLIC_SHARE_SCHEMA_VERSION,
    apply_public_share_response_headers,
    is_public_share_enabled,
)

log = logging.getLogger(__name__)

router = APIRouter()


def _get_public_share_base_url(request: Request) -> str:
    public_share_base_url = str(getattr(request.app.state, 'PUBLIC_SHARE_BASE_URL', '') or '')
    if not is_public_share_enabled(
        bool(getattr(request.app.state.config, 'ENABLE_PUBLIC_CHAT_SHARING', False)),
        public_share_base_url,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return public_share_base_url


def _assert_share_permission(request: Request, user) -> None:
    if user.role != 'admin' and not has_permission(user.id, 'chat.share', request.app.state.config.USER_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


def _set_public_share_headers(response: Response) -> None:
    apply_public_share_response_headers(response)


def _find_snapshot_file(snapshot: dict, file_id: str) -> Optional[dict]:
    history = snapshot.get('history') or {}
    history_messages = history.get('messages') or {}

    if isinstance(history_messages, dict):
        message_iterable = history_messages.values()
    else:
        message_iterable = snapshot.get('messages') or []

    for message in message_iterable:
        if not isinstance(message, dict):
            continue

        for file in message.get('files') or []:
            if not isinstance(file, dict):
                continue

            if str(file.get('file_id') or '') == file_id:
                return file

    return None


def _resolve_image_content_type(file, snapshot_file: Optional[dict]) -> Optional[str]:
    content_type = None

    if isinstance(getattr(file, 'meta', None), dict):
        meta_content_type = file.meta.get('content_type')
        if isinstance(meta_content_type, str) and meta_content_type.strip():
            content_type = meta_content_type.strip()

    if not content_type and isinstance(snapshot_file, dict):
        snapshot_content_type = snapshot_file.get('content_type')
        if isinstance(snapshot_content_type, str) and snapshot_content_type.strip():
            content_type = snapshot_content_type.strip()

    if not content_type:
        guessed_content_type, _ = mimetypes.guess_type(getattr(file, 'filename', '') or '')
        content_type = guessed_content_type

    if not content_type or not content_type.lower().startswith('image/'):
        return None

    return content_type


def _is_snapshot_schema_stale(snapshot: dict | None) -> bool:
    if not isinstance(snapshot, dict):
        return True

    try:
        snapshot_schema_version = int(snapshot.get('schema_version') or 0)
    except (TypeError, ValueError, AttributeError):
        snapshot_schema_version = 0

    return snapshot_schema_version < PUBLIC_SHARE_SCHEMA_VERSION


@router.get('/list', response_model=PublicShareListResponse)
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
        **({'query': query} if query else {}),
        **({'order_by': order_by} if order_by else {}),
        **({'direction': direction} if direction else {}),
    }

    return PublicShares.get_public_share_list_by_user_id(
        user.id,
        public_share_base_url,
        filter=filter,
        skip=skip,
        limit=limit,
        db=db,
    )


@router.get('/chats/{chat_id}', response_model=PublicShareAccessResponse)
async def get_public_share_by_chat_id(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    public_share_base_url = _get_public_share_base_url(request)
    _assert_share_permission(request, user)

    chat = await Chats.get_chat_by_id_and_user_id(chat_id, user.id)
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
        url=f'{public_share_base_url.rstrip("/")}/p/{public_share.id}',
        message_count=public_share.message_count,
        source_chat_updated_at=public_share.source_chat_updated_at,
        created_at=public_share.created_at,
        updated_at=public_share.updated_at,
        is_stale=(
            chat.updated_at > public_share.source_chat_updated_at
            or _is_snapshot_schema_stale(public_share.snapshot_json)
        ),
    )


@router.post('/chats/{chat_id}', response_model=PublicShareAccessResponse)
async def upsert_public_share_by_chat_id(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    public_share_base_url = _get_public_share_base_url(request)
    _assert_share_permission(request, user)

    chat = await Chats.get_chat_by_id_and_user_id(chat_id, user.id)
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


@router.delete('/chats/{chat_id}', response_model=bool)
async def delete_public_share_by_chat_id(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    _get_public_share_base_url(request)
    _assert_share_permission(request, user)

    chat = await Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if chat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return PublicShares.delete_public_share_by_chat_id_and_user_id(chat_id, user.id, db=db)


@router.get('/{public_share_id}', response_model=PublicShareSnapshotResponse)
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
        title=str(snapshot.get('title') or public_share.title),
        models=list(snapshot.get('models') or []),
        messages=list(snapshot.get('messages') or []),
        history=snapshot.get('history') if isinstance(snapshot.get('history'), dict) else None,
        message_count=public_share.message_count,
        created_at=public_share.created_at,
        updated_at=public_share.updated_at,
    )


@router.get('/{public_share_id}/files/{file_id}/content')
async def get_public_share_file_content(
    request: Request,
    response: Response,
    public_share_id: str,
    file_id: str,
    db: Session = Depends(get_session),
):
    _get_public_share_base_url(request)
    public_share = PublicShares.get_public_share_by_id(public_share_id, db=db)
    if public_share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    snapshot = public_share.snapshot_json or {}
    snapshot_file = _find_snapshot_file(snapshot, file_id)
    if snapshot_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    file = Files.get_file_by_id_and_user_id(file_id, public_share.user_id, db=db)
    if file is None or not getattr(file, 'path', None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    content_type = _resolve_image_content_type(file, snapshot_file)
    if content_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        file_path = Path(Storage.get_file(file.path))
        if not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    except HTTPException:
        raise
    except Exception as error:
        log.exception(error)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        ) from error

    filename = None
    if isinstance(getattr(file, 'meta', None), dict):
        meta_name = file.meta.get('name')
        if isinstance(meta_name, str) and meta_name.strip():
            filename = meta_name.strip()
    if not filename:
        filename = getattr(file, 'filename', None) or f'{file_id}.img'

    response = FileResponse(
        file_path,
        headers={
            'Content-Disposition': f"inline; filename*=UTF-8''{quote(filename)}",
        },
        media_type=content_type,
    )
    _set_public_share_headers(response)
    return response


@router.head('/{public_share_id}')
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
