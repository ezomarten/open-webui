from open_webui.utils.openrouter import (
    apply_openrouter_zdr_preferences,
    normalize_openrouter_zdr_models_response,
)


def test_normalize_openrouter_zdr_models_response_groups_endpoints_by_model_id():
    response = {
        "data": [
            {
                "model_id": "openai/gpt-4o-mini",
                "model_name": "GPT-4o mini",
                "provider_name": "OpenAI",
                "tag": "zdr",
                "context_length": 128000,
            },
            {
                "model_id": "openai/gpt-4o-mini",
                "model_name": "GPT-4o mini",
                "provider_name": "Azure",
                "tag": "enterprise",
            },
            {
                "model_id": "anthropic/claude-3.5-sonnet",
                "model_name": "Claude 3.5 Sonnet",
                "provider_name": "Anthropic",
                "tag": "zdr",
                "context_length": 200000,
            },
        ]
    }

    normalized = normalize_openrouter_zdr_models_response(response)

    assert normalized["object"] == "list"
    assert len(normalized["data"]) == 2

    gpt4o_mini = next(
        model for model in normalized["data"] if model["id"] == "openai/gpt-4o-mini"
    )
    assert gpt4o_mini["name"] == "GPT-4o mini"
    assert gpt4o_mini["openai"] == {"id": "openai/gpt-4o-mini"}
    assert gpt4o_mini["providers"] == ["OpenAI", "Azure"]
    assert gpt4o_mini["provider_tags"] == ["zdr", "enterprise"]
    assert gpt4o_mini["context_length"] == 128000
    assert gpt4o_mini["zdr_only"] is True


def test_apply_openrouter_zdr_preferences_preserves_existing_provider_settings():
    payload = {
        "model": "openai/gpt-4o-mini",
        "provider": {"order": ["OpenAI"], "allow_fallbacks": False},
    }

    updated = apply_openrouter_zdr_preferences(
        "https://openrouter.ai/api/v1",
        {"openrouter_zdr_only": True},
        payload,
    )

    assert updated["provider"] == {
        "order": ["OpenAI"],
        "allow_fallbacks": False,
        "zdr": True,
    }
