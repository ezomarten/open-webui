import re
import secrets
from typing import Any, Optional
from urllib.parse import urlparse

ATTACHMENT_OMITTED_TEXT = "[Attachment omitted]"
PUBLIC_SHARE_ID_PREFIX = "ps_"
PUBLIC_SHARE_SCHEMA_VERSION = 3

_INTERNAL_FILE_URL_PATTERNS = (
    re.compile(r"^/api/v1/files/(?P<file_id>[^/]+)/content(?:/[^/]+)?/?$"),
    re.compile(r"^/api/v1/files/(?P<file_id>[^/]+)/?$"),
)


def new_public_share_id() -> str:
    return f"{PUBLIC_SHARE_ID_PREFIX}{secrets.token_urlsafe(18)}"


def normalize_public_share_base_url(base_url: Any) -> str:
    return str(base_url or "").strip().rstrip("/")


def validate_public_share_base_url(base_url: Any) -> str:
    normalized = normalize_public_share_base_url(base_url)
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("PUBLIC_SHARE_BASE_URL must be an absolute HTTP(S) URL")

    return normalized


def get_public_share_host(base_url: Any) -> str:
    normalized = normalize_public_share_base_url(base_url)
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        return ""

    return (parsed.hostname or "").lower()


def is_public_share_enabled(enabled: bool, base_url: Any) -> bool:
    return bool(enabled and get_public_share_host(base_url))


def build_public_share_url(base_url: str, public_share_id: str) -> str:
    return f"{normalize_public_share_base_url(base_url)}/p/{public_share_id}"


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

    public_files = _sanitize_public_files(message)
    public_sources = _sanitize_public_sources(message)
    content = _sanitize_content(message, public_files, public_sources)
    if content is None and len(public_files) == 0 and len(public_sources) == 0:
        return None

    message_id = str(message.get("id") or f"psm_{index}")
    model = _normalize_model_name(message.get("model") or message.get("modelName"))
    timestamp = _coerce_timestamp(
        message.get("timestamp")
        or message.get("created_at")
        or message.get("updated_at")
        or message.get("time")
    )

    public_message = {
        "id": message_id,
        "role": role,
        "content": content if content is not None else "",
        "model": model,
        "timestamp": timestamp,
    }

    if public_files:
        public_message["files"] = public_files

    if public_sources:
        public_message["sources"] = public_sources

    return public_message


def build_public_share_snapshot(chat: Any) -> dict:
    chat_body = getattr(chat, "chat", None) or {}
    title = str(
        getattr(chat, "title", None) or chat_body.get("title") or "Untitled Chat"
    )

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


def _sanitize_content(
    message: dict, public_files: list[dict], public_sources: list[dict]
) -> Optional[str]:
    parts, content_has_attachment = _extract_text_parts(message.get("content"))

    if _message_has_omitted_attachment_fields(message, public_files, public_sources):
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

    if public_files or public_sources:
        return ""

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


def _sanitize_public_files(message: dict) -> list[dict]:
    files = message.get("files") or []
    if not isinstance(files, list):
        return []

    public_files = []
    for file in files:
        sanitized_file = _sanitize_public_file(file)
        if sanitized_file is not None:
            public_files.append(sanitized_file)

    return public_files


def _sanitize_public_file(file: Any) -> Optional[dict]:
    if not isinstance(file, dict):
        return None

    if not _is_image_file(file):
        return None

    file_id = _extract_file_id(file.get("url"))
    if file_id is None:
        return None

    public_file = {
        "type": "image",
        "file_id": file_id,
    }

    content_type = _normalize_optional_string(file.get("content_type"))
    if content_type:
        public_file["content_type"] = content_type

    name = _normalize_optional_string(file.get("name"))
    if name:
        public_file["name"] = name

    size = _coerce_int(file.get("size"))
    if size is not None:
        public_file["size"] = size

    return public_file


def _sanitize_public_sources(message: dict) -> list[dict]:
    sources = message.get("sources")
    if sources is None:
        sources = message.get("citations")

    if not isinstance(sources, list):
        return []

    public_sources = []
    for source in sources:
        sanitized_source = _sanitize_public_source(source)
        if sanitized_source is not None:
            public_sources.append(sanitized_source)

    return public_sources


def _sanitize_public_source(source: Any) -> Optional[dict]:
    if not isinstance(source, dict):
        return None

    source_info = _sanitize_public_source_info(source.get("source"))

    documents = source.get("document") or []
    metadata_items = source.get("metadata") or []
    distances = source.get("distances") or []

    if not isinstance(documents, list) or len(documents) == 0:
        return None

    public_documents = []
    public_metadata = []
    public_distances = []
    include_distances = True

    for index, document in enumerate(documents):
        sanitized_document = _sanitize_public_document(document)
        if sanitized_document is None:
            continue

        metadata = (
            metadata_items[index]
            if isinstance(metadata_items, list) and index < len(metadata_items)
            else None
        )
        public_reference = _get_public_source_reference(metadata, source_info)
        if public_reference is None:
            continue

        public_documents.append(sanitized_document)
        public_metadata.append(
            _sanitize_public_source_metadata(metadata, public_reference)
        )

        distance = (
            distances[index]
            if isinstance(distances, list) and index < len(distances)
            else None
        )
        if isinstance(distance, (int, float)):
            public_distances.append(distance)
        else:
            include_distances = False

    if len(public_documents) == 0:
        return None

    public_source = {
        "source": source_info,
        "document": public_documents,
        "metadata": public_metadata,
    }

    if include_distances and len(public_distances) == len(public_documents):
        public_source["distances"] = public_distances

    return public_source


def _sanitize_public_source_info(source: Any) -> dict:
    if not isinstance(source, dict):
        return {}

    public_source = {}

    for key in ("id", "name", "type"):
        value = _normalize_optional_string(source.get(key))
        if value:
            public_source[key] = value

    public_url = _normalize_public_url(source.get("url"))
    if public_url:
        public_source["url"] = public_url

    embed_url = _normalize_public_url(source.get("embed_url"))
    if embed_url:
        public_source["embed_url"] = embed_url

    return public_source


def _sanitize_public_document(document: Any) -> Optional[str]:
    if document is None:
        return None

    normalized_document = str(document).strip()
    return normalized_document if normalized_document else None


def _sanitize_public_source_metadata(metadata: Any, public_reference: str) -> dict:
    public_metadata = {
        "source": public_reference,
        "url": public_reference,
    }

    if isinstance(metadata, dict):
        name = _normalize_optional_string(metadata.get("name"))
        if name:
            public_metadata["name"] = name

        page = _coerce_int(metadata.get("page"))
        if page is not None:
            public_metadata["page"] = page

    return public_metadata


def _get_public_source_reference(metadata: Any, source: dict) -> Optional[str]:
    if isinstance(metadata, dict):
        for key in ("url", "source"):
            public_url = _normalize_public_url(metadata.get(key))
            if public_url:
                return public_url

    for key in ("url", "embed_url", "id", "name"):
        public_url = _normalize_public_url(source.get(key))
        if public_url:
            return public_url

    return None


def _message_has_omitted_attachment_fields(
    message: dict, public_files: list[dict], public_sources: list[dict]
) -> bool:
    attachment_fields = (
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

    raw_sources = message.get("sources")
    if raw_sources is None:
        raw_sources = message.get("citations")

    if raw_sources:
        if not isinstance(raw_sources, list):
            return True

        if len(raw_sources) != len(public_sources):
            return True

        if _count_source_documents(raw_sources) != _count_source_documents(
            public_sources
        ):
            return True

    public_file_ids = {
        str(file.get("file_id"))
        for file in public_files
        if isinstance(file, dict) and file.get("file_id")
    }

    files = message.get("files") or []
    if not isinstance(files, list):
        return True

    for file in files:
        if not isinstance(file, dict):
            return True

        file_id = _extract_file_id(file.get("url"))
        if file_id is None or file_id not in public_file_ids:
            return True

    return False


def _is_image_file(file: dict) -> bool:
    file_type = (_normalize_optional_string(file.get("type")) or "").lower()
    content_type = (_normalize_optional_string(file.get("content_type")) or "").lower()
    return file_type == "image" or content_type.startswith("image/")


def _extract_file_id(value: Any) -> Optional[str]:
    if value is None:
        return None

    candidate = str(value).strip()
    if not candidate:
        return None

    if "/" not in candidate and "?" not in candidate and "#" not in candidate:
        return candidate

    path = urlparse(candidate).path or candidate
    for pattern in _INTERNAL_FILE_URL_PATTERNS:
        match = pattern.match(path)
        if match:
            return match.group("file_id")

    return None


def _normalize_model_name(value: Any) -> Optional[str]:
    if value is None:
        return None

    model_name = str(value).strip()
    return model_name if model_name else None


def _count_source_documents(sources: list[Any]) -> int:
    count = 0

    for source in sources:
        if not isinstance(source, dict):
            continue

        documents = source.get("document") or []
        if isinstance(documents, list):
            count += len(documents)

    return count


def _normalize_public_url(value: Any) -> Optional[str]:
    if value is None:
        return None

    candidate = str(value).strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None

    return candidate


def _normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None

    normalized_value = str(value).strip()
    return normalized_value if normalized_value else None


def _coerce_timestamp(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None
