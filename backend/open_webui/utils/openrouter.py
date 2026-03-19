from typing import Optional
from urllib.parse import urlparse


def is_openrouter_url(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname.endswith("openrouter.ai")


def is_openrouter_zdr_model_list_enabled(
    url: str, config: Optional[dict] = None
) -> bool:
    return is_openrouter_url(url) and bool((config or {}).get("openrouter_zdr_only"))


def get_models_list_url(url: str, config: Optional[dict] = None) -> str:
    if is_openrouter_zdr_model_list_enabled(url, config):
        return f"{url}/endpoints/zdr"
    return f"{url}/models"


def normalize_openrouter_zdr_models_response(response) -> dict[str, list]:
    endpoint_data = response.get("data", []) if isinstance(response, dict) else response
    if not isinstance(endpoint_data, list):
        endpoint_data = []

    models_by_id = {}

    for endpoint in endpoint_data:
        if not isinstance(endpoint, dict):
            continue

        model_id = endpoint.get("model_id")
        if not model_id:
            continue

        model = models_by_id.setdefault(
            model_id,
            {
                "id": model_id,
                "name": endpoint.get("model_name") or endpoint.get("name") or model_id,
                "owned_by": "openai",
                "openai": {"id": model_id},
                "providers": [],
                "provider_tags": [],
                "zdr_only": True,
            },
        )

        provider_name = endpoint.get("provider_name")
        if provider_name and provider_name not in model["providers"]:
            model["providers"].append(provider_name)

        provider_tag = endpoint.get("tag")
        if provider_tag and provider_tag not in model["provider_tags"]:
            model["provider_tags"].append(provider_tag)

        if not model.get("context_length") and endpoint.get("context_length"):
            model["context_length"] = endpoint["context_length"]

    return {"object": "list", "data": list(models_by_id.values())}


def normalize_models_response(url: str, config: Optional[dict], response):
    if response is None:
        return None

    if is_openrouter_zdr_model_list_enabled(url, config):
        return normalize_openrouter_zdr_models_response(response)

    return response


def apply_openrouter_zdr_preferences(
    url: str, config: Optional[dict], payload: Optional[dict]
):
    if not isinstance(payload, dict) or not is_openrouter_zdr_model_list_enabled(
        url, config
    ):
        return payload

    provider = payload.get("provider")
    if not isinstance(provider, dict):
        provider = {}

    provider["zdr"] = True
    payload["provider"] = provider

    return payload
