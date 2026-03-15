import secrets
from typing import Any, Optional


ATTACHMENT_OMITTED_TEXT = "[Attachment omitted]"
PUBLIC_SHARE_ID_PREFIX = "ps_"
PUBLIC_SHARE_SCHEMA_VERSION = 1


def new_public_share_id() -> str:
    return f"{PUBLIC_SHARE_ID_PREFIX}{secrets.token_urlsafe(18)}"


def build_public_share_url(base_url: str, public_share_id: str) -> str:
    return f"{base_url.rstrip('/')}/p/{public_share_id}"


def extract_public_branch(chat_body: dict) -> list[dict]:
    history = chat_body.get("history") or {}
    history_messages = history.get("messages") or {}
    current_id = history.get("currentId")

    if current_id and isinstance(history_messages, dict):
        branch = []
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            message = history_messages.get(current_id)
            if not message:
                break

            branch.append(message)
            current_id = message.get("parentId")

        if branch:
            branch.reverse()
            return branch

    messages = chat_body.get("messages") or []
    if isinstance(messages, list):
        return messages

    return []


def sanitize_public_message(message: dict, index: int = 0) -> Optional[dict]:
    role = str(message.get("role") or "").lower().strip()
    if role not in {"user", "assistant"}:
        return None

    content = _sanitize_content(message)
    if content is None:
        return None

    message_id = str(message.get("id") or f"psm_{index}")
    model = _normalize_model_name(message.get("model") or message.get("modelName"))
    timestamp = _coerce_timestamp(
        message.get("timestamp")
        or message.get("created_at")
        or message.get("updated_at")
        or message.get("time")
    )

    return {
        "id": message_id,
        "role": role,
        "content": content,
        "model": model,
        "timestamp": timestamp,
    }


def build_public_share_snapshot(chat: Any) -> dict:
    chat_body = getattr(chat, "chat", None) or {}
    title = str(getattr(chat, "title", None) or chat_body.get("title") or "Untitled Chat")

    branch = extract_public_branch(chat_body)
    public_messages = []

    for index, message in enumerate(branch):
        sanitized_message = sanitize_public_message(message, index=index)
        if sanitized_message is not None:
            public_messages.append(sanitized_message)

    if len(public_messages) == 0:
        raise ValueError("No public messages found.")

    models = []
    seen_models = set()

    for message in public_messages:
        model_name = _normalize_model_name(message.get("model"))
        if model_name and model_name not in seen_models:
            seen_models.add(model_name)
            models.append(model_name)

    fallback_models = chat_body.get("models") or []
    if isinstance(fallback_models, str):
        fallback_models = [fallback_models]

    for model_name in fallback_models:
        normalized_name = _normalize_model_name(model_name)
        if normalized_name and normalized_name not in seen_models:
            seen_models.add(normalized_name)
            models.append(normalized_name)

    return {
        "schema_version": PUBLIC_SHARE_SCHEMA_VERSION,
        "title": title,
        "models": models,
        "messages": public_messages,
    }


def _sanitize_content(message: dict) -> Optional[str]:
    parts, content_has_attachment = _extract_text_parts(message.get("content"))

    if _message_has_attachment_fields(message):
        content_has_attachment = True

    normalized_parts = []
    for part in parts:
        if not isinstance(part, str):
            continue

        normalized_part = part.strip()
        if normalized_part:
            normalized_parts.append(normalized_part)

    if normalized_parts:
        return "\n\n".join(normalized_parts)

    if content_has_attachment:
        return ATTACHMENT_OMITTED_TEXT

    return None


def _extract_text_parts(value: Any) -> tuple[list[str], bool]:
    parts: list[str] = []
    has_attachment = False

    if value is None:
        return parts, has_attachment

    if isinstance(value, str):
        return [value], False

    if isinstance(value, list):
        for item in value:
            item_parts, item_has_attachment = _extract_text_parts(item)
            parts.extend(item_parts)
            has_attachment = has_attachment or item_has_attachment
        return parts, has_attachment

    if isinstance(value, dict):
        value_type = str(value.get("type") or "").lower().strip()
        text_payload_keys = ("text", "content", "value")

        if value_type in {"text", "input_text", "output_text"}:
            for key in text_payload_keys:
                if key in value:
                    return _extract_text_parts(value.get(key))

        extracted_any = False
        for key in text_payload_keys:
            if key in value:
                extracted_any = True
                item_parts, item_has_attachment = _extract_text_parts(value.get(key))
                parts.extend(item_parts)
                has_attachment = has_attachment or item_has_attachment

        if value_type and value_type not in {"text", "input_text", "output_text"}:
            has_attachment = True

        if not extracted_any and value:
            has_attachment = True

        return parts, has_attachment

    return parts, True


def _message_has_attachment_fields(message: dict) -> bool:
    attachment_fields = (
        "files",
        "sources",
        "embeds",
        "statusHistory",
        "annotation",
        "usage",
        "error",
        "images",
    )

    for field in attachment_fields:
        value = message.get(field)
        if value:
            return True

    return False


def _normalize_model_name(value: Any) -> Optional[str]:
    if value is None:
        return None

    model_name = str(value).strip()
    return model_name if model_name else None


def _coerce_timestamp(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None