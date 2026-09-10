from __future__ import annotations

"""Validated operator configuration for local-model services.

This module only validates and saves settings. It never installs, downloads,
deletes, replaces, starts, or stops model services or model files.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from local_model import InvalidConfigurationError, LocalModelConfig, LocalModelError
from settings_manager import (
    LOCAL_MODEL_PROVIDER_PROFILE_KEYS,
    SettingsError,
    load_settings,
    save_settings,
    validate_settings_patch,
)

SCHEMA_VERSION = "1"

EDITABLE_KEYS: tuple[str, ...] = (
    "local_model_provider",
    "local_model_endpoint",
    "local_model_embedding_endpoint",
    "local_model",
    "embed_model",
    "local_model_context_size",
    "local_model_connect_timeout_seconds",
    "local_model_read_timeout_seconds",
    "local_model_ollama_keep_alive_minutes",
    "local_model_max_tokens",
    "local_model_temperature",
    "local_model_top_p",
    "local_model_top_k",
    "local_model_repeat_penalty",
)
EDITABLE_KEY_SET = set(EDITABLE_KEYS)

FIELD_LABELS: dict[str, str] = {
    "local_model_provider": "Provider",
    "local_model_endpoint": "Generation endpoint",
    "local_model_embedding_endpoint": "Embedding endpoint",
    "local_model": "Generation model",
    "embed_model": "Embedding model",
    "local_model_context_size": "Context size",
    "local_model_connect_timeout_seconds": "Connection timeout",
    "local_model_read_timeout_seconds": "Read timeout",
    "local_model_ollama_keep_alive_minutes": "Ollama keep-warm minutes",
    "local_model_max_tokens": "Maximum generated tokens",
    "local_model_temperature": "Temperature",
    "local_model_top_p": "Top-p",
    "local_model_top_k": "Top-k",
    "local_model_repeat_penalty": "Repeat penalty",
}


@dataclass(frozen=True)
class LocalModelConfigurationValidationError(ValueError):
    errors: tuple[dict[str, str], ...]

    def __str__(self) -> str:
        return "; ".join(item.get("message", "Invalid local-model setting.") for item in self.errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": "invalid_local_model_configuration",
            "message": "Local-model settings were not saved.",
            "errors": [dict(item) for item in self.errors],
        }


def _field_for_message(message: str) -> str:
    lowered = message.lower()
    matches = (
        ("embedding_endpoint", "local_model_embedding_endpoint"),
        ("local_model_endpoint", "local_model_endpoint"),
        ("provider", "local_model_provider"),
        ("context", "local_model_context_size"),
        ("connect", "local_model_connect_timeout_seconds"),
        ("read timeout", "local_model_read_timeout_seconds"),
        ("keep_alive", "local_model_ollama_keep_alive_minutes"),
        ("keep-warm", "local_model_ollama_keep_alive_minutes"),
        ("timeout", "local_model_read_timeout_seconds"),
        ("max_tokens", "local_model_max_tokens"),
        ("temperature", "local_model_temperature"),
        ("top_p", "local_model_top_p"),
        ("top_k", "local_model_top_k"),
        ("repeat_penalty", "local_model_repeat_penalty"),
        ("embed_model", "embed_model"),
        ("local_model cannot", "local_model"),
    )
    for token, field in matches:
        if token in lowered:
            return field
    return "configuration"


def _validation_error(error: Exception, field: str | None = None) -> LocalModelConfigurationValidationError:
    message = str(error) or type(error).__name__
    resolved_field = field or _field_for_message(message)
    return LocalModelConfigurationValidationError(({
        "field": resolved_field,
        "label": FIELD_LABELS.get(resolved_field, "Configuration"),
        "message": message,
    },))


def validate_local_model_configuration(
    patch: dict[str, Any],
    *,
    base_settings: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], LocalModelConfig]:
    """Validate an editor patch without writing settings or model state."""
    if not isinstance(patch, dict):
        raise _validation_error(SettingsError("Settings update must be a JSON object."))
    unknown = sorted(set(patch) - EDITABLE_KEY_SET)
    if unknown:
        raise LocalModelConfigurationValidationError(tuple({
            "field": key,
            "label": key,
            "message": f"Setting is not editable from the local-model dashboard: {key}",
        } for key in unknown))
    try:
        merged = validate_settings_patch(
            patch,
            allowed_keys=EDITABLE_KEY_SET,
            base_settings=base_settings,
        )
        config = LocalModelConfig.from_settings(merged).validated()
    except (SettingsError, InvalidConfigurationError, LocalModelError, TypeError, ValueError) as error:
        raise _validation_error(error) from error
    return merged, config


def configuration_payload(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved_settings = dict(settings if settings is not None else load_settings())
    try:
        _, config = validate_local_model_configuration(
            {key: resolved_settings.get(key) for key in EDITABLE_KEYS},
            base_settings=resolved_settings,
        )
        validation = {"status": "valid", "errors": []}
        effective_embedding_endpoint = config.resolved_embedding_endpoint
        fallback = config.uses_legacy_single_endpoint
    except LocalModelConfigurationValidationError as error:
        validation = {"status": "invalid", "errors": [dict(item) for item in error.errors]}
        effective_embedding_endpoint = str(
            resolved_settings.get("local_model_embedding_endpoint")
            or resolved_settings.get("local_model_endpoint")
            or ""
        )
        fallback = not bool(str(resolved_settings.get("local_model_embedding_endpoint") or "").strip())
    return {
        "schema_version": SCHEMA_VERSION,
        "values": {key: resolved_settings.get(key) for key in EDITABLE_KEYS},
        "effective_embedding_endpoint": effective_embedding_endpoint,
        "embedding_endpoint_uses_generation_fallback": fallback,
        "validation": validation,
        "automatic_model_management": False,
        "operator_save_required": True,
        "editable_keys": list(EDITABLE_KEYS),
        "provider_profiles": deepcopy(resolved_settings.get("local_model_provider_profiles") or {}),
        "active_provider_profile": str(resolved_settings.get("local_model_provider") or "ollama"),
        "provider_profile_isolation": True,
    }


def save_local_model_configuration(patch: dict[str, Any]) -> dict[str, Any]:
    """Validate and save only the dashboard-editable settings."""
    current = load_settings()
    current_provider = str(current.get("local_model_provider") or "ollama")
    target_provider = str(patch.get("local_model_provider") or current_provider).strip().lower()
    profiles = deepcopy(current.get("local_model_provider_profiles") or {})
    profiles.setdefault("ollama", {})
    profiles.setdefault("llama_cpp", {})
    profiles[current_provider] = {
        key: current.get(key)
        for key in LOCAL_MODEL_PROVIDER_PROFILE_KEYS
    }

    effective_patch = dict(patch)
    provider_keys = [key for key in LOCAL_MODEL_PROVIDER_PROFILE_KEYS if key in effective_patch]
    submitted_values_match_current = bool(provider_keys) and all(
        effective_patch.get(key) == current.get(key) for key in provider_keys
    )
    target_profile = profiles.get(target_provider) or {}
    internal_profile_patch: dict[str, Any] = {}
    if target_provider != current_provider:
        # A provider selector change commonly submits the old provider's visible
        # fields. Restore the target profile instead of cross-contaminating it.
        # Non-dashboard transport fields are restored internally, but never made
        # user-editable through this endpoint.
        for key, value in target_profile.items():
            if key not in LOCAL_MODEL_PROVIDER_PROFILE_KEYS:
                continue
            if key in EDITABLE_KEY_SET:
                if key not in effective_patch or submitted_values_match_current:
                    effective_patch[key] = value
            else:
                internal_profile_patch[key] = value

    merged, _ = validate_local_model_configuration(effective_patch, base_settings=current)
    if internal_profile_patch:
        try:
            merged = validate_settings_patch(
                internal_profile_patch,
                allowed_keys=set(LOCAL_MODEL_PROVIDER_PROFILE_KEYS) - EDITABLE_KEY_SET,
                base_settings=merged,
            )
            LocalModelConfig.from_settings(merged).validated()
        except (SettingsError, InvalidConfigurationError, LocalModelError, TypeError, ValueError) as error:
            raise _validation_error(error) from error
    profiles[target_provider] = {
        key: merged.get(key)
        for key in LOCAL_MODEL_PROVIDER_PROFILE_KEYS
    }
    merged["local_model_provider_profiles"] = profiles
    save_settings(merged)
    return configuration_payload(merged)
