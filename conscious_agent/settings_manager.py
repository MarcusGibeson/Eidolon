from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any

import requests

from paths import DATA_DIR
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic


SETTINGS_FILE = DATA_DIR / "settings.json"
TRAINING_CAPTURE_SETTING_KEYS: tuple[str, ...] = (
    "training_capture_coding_repair_enabled",
    "training_capture_research_enabled",
    "training_capture_planning_enabled",
    "training_capture_tool_governance_enabled",
    "training_capture_conversation_enabled",
    "training_auto_sanitize_enabled",
)

LOCAL_MODEL_PROVIDER_PROFILE_KEYS: tuple[str, ...] = (
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
    "local_model_retry_limit",
    "local_model_retry_delay_seconds",
    "local_model_seed",
    "local_model_thinking_mode",
    "local_model_stop_sequences",
)

DEFAULT_LOCAL_MODEL_PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    "ollama": {
        "local_model_endpoint": "http://localhost:11434",
        "local_model_embedding_endpoint": "",
        "local_model": "qwen2.5:7b",
        "local_model_thinking_mode": "auto",
        "embed_model": "nomic-embed-text:latest",
        "local_model_context_size": 8192,
        "local_model_connect_timeout_seconds": 5.0,
        "local_model_read_timeout_seconds": 120.0,
        "local_model_ollama_keep_alive_minutes": 30,
        "local_model_max_tokens": 350,
        "local_model_temperature": 0.45,
        "local_model_top_p": 0.9,
        "local_model_top_k": 40,
        "local_model_repeat_penalty": 1.1,
        "local_model_retry_limit": 1,
        "local_model_retry_delay_seconds": 0.25,
        "local_model_seed": 0,
        "local_model_stop_sequences": "",
    },
    "llama_cpp": {
        "local_model_endpoint": "http://127.0.0.1:8080",
        "local_model_embedding_endpoint": "",
        "local_model": "local-model",
        "local_model_thinking_mode": "auto",
        "embed_model": "local-embedding-model",
        "local_model_context_size": 8192,
        "local_model_connect_timeout_seconds": 5.0,
        "local_model_read_timeout_seconds": 120.0,
        "local_model_ollama_keep_alive_minutes": 0,
        "local_model_max_tokens": 350,
        "local_model_temperature": 0.45,
        "local_model_top_p": 0.9,
        "local_model_top_k": 40,
        "local_model_repeat_penalty": 1.1,
        "local_model_retry_limit": 1,
        "local_model_retry_delay_seconds": 0.25,
        "local_model_seed": 0,
        "local_model_stop_sequences": "",
    },
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "settings_version": "2503.4.31",
    "local_model_provider": "ollama",
    "local_model_thinking_mode": "auto",
    "local_model_endpoint": "http://localhost:11434",
    "local_model_embedding_endpoint": "",
    "local_model": "qwen2.5:7b",
    "embed_model": "nomic-embed-text:latest",
    "local_model_context_size": 8192,
    "local_model_connect_timeout_seconds": 5.0,
    "local_model_read_timeout_seconds": 120.0,
    "local_model_ollama_keep_alive_minutes": 30,
    "local_model_max_tokens": 350,
    "local_model_temperature": 0.45,
    "local_model_top_p": 0.9,
    "local_model_top_k": 40,
    "local_model_repeat_penalty": 1.1,
    "local_model_retry_limit": 1,
    "local_model_retry_delay_seconds": 0.25,
    "local_model_seed": 0,
    "local_model_stop_sequences": "",
    "local_model_provider_profiles": deepcopy(DEFAULT_LOCAL_MODEL_PROVIDER_PROFILES),
    "ollama_base_url": "http://localhost:11434",
    "ollama_timeout_seconds": 120,
    "command_timeout_seconds": 45,
    "max_capture_chars": 12000,
    "default_dev_loop_steps": 3,
    "max_dev_loop_steps": 10,
    "memory_keep_recent": 40,
    "memory_min_count": 80,
    "ai_chat_enabled": True,
    "ai_reviews_enabled": True,
    "approval_required_for_file_edits": True,
    "approval_required_for_rollbacks": True,
    "safe_mode": "strict",
    "dashboard_host": "127.0.0.1",
    "dashboard_port": 8765,
    "watch_interval_seconds": 300,
    "watch_default_cycles": 3,
    "watch_max_cycles": 10,
    "notifications_enabled": True,
    "notification_min_priority": "medium",
    "dashboard_chat_use_ai_default": True,
    "api_host": "127.0.0.1",
    "api_port": 8766,
    "dashboard_live_refresh_enabled": True,
    "dashboard_live_refresh_seconds": 5,
    "desktop_refresh_seconds": 8,
    "desktop_prefer_dashboard_api": True,
    "desktop_launch_dashboard_on_start": True,
    "desktop_notifications_enabled": True,
    "desktop_notify_on_unread": True,
    "desktop_notify_on_pending_approvals": True,
    "desktop_notify_on_startup": True,
    "desktop_popup_seconds": 8,
    "desktop_bell_enabled": True,
    "desktop_close_to_watcher": False,
    "desktop_watcher_topmost": True,
    "desktop_api_poll_when_hidden": True,
    "desktop_quick_actions_enabled": True,
    "desktop_confirm_notification_dismiss": True,
    "desktop_confirm_clear_dismissed": True,
    "desktop_tray_enabled": True,
    "desktop_real_tray_enabled": True,
    "desktop_tray_show_on_start": True,
    "desktop_tray_minimize_on_close": True,
    "desktop_tray_fallback_to_watcher": True,
    "desktop_tray_status_in_tooltip": True,
    "desktop_setup_check_on_start": False,
    "desktop_setup_warn_if_attention": True,
    "setup_check_ollama": True,
    "setup_check_ports": True,
    "desktop_onboarding_check_on_start": False,
    "onboarding_refresh_setup_default": True,
    "last_updated_for": "v2503.4.31",
    "release_pipeline_enabled": True,
    "approval_binding_required_for_draft_apply": True,
    "safe_rewrite_preview_required": True,
    "training_capture_coding_repair_enabled": True,
    "training_capture_research_enabled": True,
    "training_capture_planning_enabled": True,
    "training_capture_tool_governance_enabled": True,
    "training_capture_conversation_enabled": False,
    "training_auto_sanitize_enabled": True,
}

SETTING_DESCRIPTIONS: dict[str, str] = {
    "settings_version": "Settings schema version.",
    "last_updated_for": "Last packaged project version that updated the settings schema/defaults.",
    "release_pipeline_enabled": "Whether the human-approved release pipeline reports and commands are enabled.",
    "approval_binding_required_for_draft_apply": "Whether approved draft apply must validate the exact saved draft artifact snapshot.",
    "safe_rewrite_preview_required": "Whether code patch apply requires a hash-checked safe rewrite preview before writing files.",
    "training_capture_coding_repair_enabled": "Automatically collect verified runtime-only coding and repair evidence.",
    "training_capture_research_enabled": "Automatically collect verified runtime-only bounded research synthesis evidence.",
    "training_capture_planning_enabled": "Collect planning evidence only where completion or revision is deterministically validated.",
    "training_capture_tool_governance_enabled": "Collect tool and governance evidence only where authority validation is deterministic.",
    "training_capture_conversation_enabled": "Collect ordinary conversation evidence. Disabled by default.",
    "training_auto_sanitize_enabled": "Deterministically sanitize successful captures without approving or exporting them.",
    "local_model_provider": "Provider used for local generation: ollama or llama_cpp.",
    "local_model_endpoint": "Generation-service base HTTP URL for the configured local-model provider.",
    "local_model_embedding_endpoint": "Optional embedding-service base HTTP URL; empty uses local_model_endpoint for backward compatibility.",
    "local_model": "Configured generation model used by the shared conversation path.",
    "embed_model": "Configured embedding model used for semantic memory.",
    "local_model_context_size": "Requested model context window size.",
    "local_model_connect_timeout_seconds": "Connection timeout for local-model HTTP requests.",
    "local_model_read_timeout_seconds": "Read timeout for local-model HTTP requests.",
    "local_model_ollama_keep_alive_minutes": "Minutes Ollama keeps the selected generation model resident after use; zero unloads it immediately.",
    "local_model_max_tokens": "Default maximum generated tokens.",
    "local_model_temperature": "Default sampling temperature.",
    "local_model_top_p": "Default nucleus sampling probability.",
    "local_model_top_k": "Default top-k sampling value where supported.",
    "local_model_repeat_penalty": "Default repetition penalty where supported.",
    "local_model_retry_limit": "Maximum safe retries for transient non-stream requests.",
    "local_model_retry_delay_seconds": "Delay between bounded transient retries.",
    "local_model_seed": "Optional deterministic seed; zero means provider default.",
    "local_model_thinking_mode": "Ollama thinking mode: auto (provider default), off, or on.",
    "local_model_stop_sequences": "Stop sequences as JSON list or pipe-separated text.",
    "local_model_provider_profiles": "Saved provider-specific generation and embedding settings used when the operator switches providers.",
    "ollama_base_url": "Base URL for the local Ollama server.",
    "ollama_timeout_seconds": "Timeout for local Ollama requests.",
    "command_timeout_seconds": "Timeout for approved command execution.",
    "max_capture_chars": "Maximum stdout/stderr characters stored from command output.",
    "default_dev_loop_steps": "Default number of steps for the bounded dev loop.",
    "max_dev_loop_steps": "Hard cap for bounded dev-loop steps.",
    "memory_keep_recent": "Default recent memory count kept active during compaction.",
    "memory_min_count": "Default minimum memory count before compaction runs.",
    "ai_chat_enabled": "Whether chat is allowed to use the local AI model.",
    "ai_reviews_enabled": "Whether review/suggestion features should use local AI by default.",
    "approval_required_for_file_edits": "Whether file edits require approval gates.",
    "approval_required_for_rollbacks": "Whether rollbacks require approval gates in automated workflows.",
    "safe_mode": "Safety posture label. Current supported value: strict.",
    "dashboard_host": "Local host/interface used by the web dashboard. Default keeps it on this computer only.",
    "dashboard_port": "Local port used by the web dashboard.",
    "watch_interval_seconds": "Default seconds between background watch-loop cycles.",
    "watch_default_cycles": "Default number of cycles for bounded background watch loops.",
    "watch_max_cycles": "Hard cap for bounded background watch-loop cycles.",
    "notifications_enabled": "Whether watch mode and related systems should create saved notifications.",
    "notification_min_priority": "Minimum watch recommendation priority that becomes a notification: low, medium, high, or critical.",
    "dashboard_chat_use_ai_default": "Whether the Dashboard Chat Console should use local AI by default.",
    "api_host": "Local host/interface used by the standalone API server. Default keeps it on this computer only.",
    "api_port": "Local port used by the standalone API server.",
    "dashboard_live_refresh_enabled": "Whether dashboard pages should poll the local API for fresh status counts.",
    "dashboard_live_refresh_seconds": "Seconds between live dashboard status refreshes.",
    "desktop_refresh_seconds": "Seconds between automatic refreshes in the local desktop companion shell.",
    "desktop_prefer_dashboard_api": "Whether the desktop shell should try the dashboard-integrated API before the standalone API.",
    "desktop_launch_dashboard_on_start": "Whether --desktop should launch the local dashboard automatically when the window opens.",
    "desktop_notifications_enabled": "Whether the desktop shell should show local advisory popups for unread notifications or pending approvals.",
    "desktop_notify_on_unread": "Whether unread Eidolon notifications should trigger desktop advisory popups.",
    "desktop_notify_on_pending_approvals": "Whether pending approval requests should trigger desktop advisory popups.",
    "desktop_notify_on_startup": "Whether the desktop shell may show an advisory popup on startup if attention is already needed.",
    "desktop_popup_seconds": "How long desktop advisory popups stay visible before closing themselves.",
    "desktop_bell_enabled": "Whether the desktop shell may ring the local Tkinter bell when a desktop advisory popup appears.",
    "desktop_close_to_watcher": "Whether closing the main desktop window hides it to the watcher window instead of exiting.",
    "desktop_watcher_topmost": "Whether the watcher fallback window should stay above normal windows.",
    "desktop_api_poll_when_hidden": "Whether the desktop shell keeps polling the local API while hidden to watcher mode.",
    "desktop_quick_actions_enabled": "Whether the desktop shell shows local quick-action buttons for read-only workflows and notification handling.",
    "desktop_confirm_notification_dismiss": "Whether the desktop shell asks before dismissing the latest unread notification.",
    "desktop_confirm_clear_dismissed": "Whether the desktop shell asks before deleting dismissed notification records.",
    "desktop_tray_enabled": "Whether the desktop shell may attempt optional real system tray integration.",
    "desktop_real_tray_enabled": "Whether to use pystray/Pillow for a real OS tray icon when available.",
    "desktop_tray_show_on_start": "Whether the desktop shell starts the real tray icon automatically when support is available.",
    "desktop_tray_minimize_on_close": "Whether closing the desktop window hides it to the real tray when available.",
    "desktop_tray_fallback_to_watcher": "Whether Hide to Tray should fall back to the watcher window if real tray support is unavailable.",
    "desktop_tray_status_in_tooltip": "Whether the real tray tooltip should update with current task, approval, and notification counts.",
    "desktop_setup_check_on_start": "Whether the desktop shell should run a setup check when it opens.",
    "desktop_setup_warn_if_attention": "Whether desktop startup should log and surface setup warnings when setup check finds attention-needed items.",
    "setup_check_ollama": "Whether setup helper should check local Ollama status and configured model availability.",
    "setup_check_ports": "Whether setup helper should check dashboard/API service ports and endpoint availability.",
    "desktop_onboarding_check_on_start": "Whether the desktop shell should run the guided onboarding wizard when it opens.",
    "onboarding_refresh_setup_default": "Whether onboarding runs should create a fresh setup report by default before building guided steps.",
}


class SettingsError(ValueError):
    pass


def _coerce_to_default_type(key: str, value: Any) -> Any:
    if key not in DEFAULT_SETTINGS:
        raise SettingsError(f"Unknown setting: {key}")

    default = DEFAULT_SETTINGS[key]

    if key == "local_model_provider_profiles":
        profiles = deepcopy(DEFAULT_LOCAL_MODEL_PROVIDER_PROFILES)
        if not isinstance(value, dict):
            raise SettingsError("local_model_provider_profiles expects an object.")
        for provider in ("ollama", "llama_cpp"):
            supplied = value.get(provider)
            if supplied is None:
                continue
            if not isinstance(supplied, dict):
                raise SettingsError(f"Saved profile for {provider} expects an object.")
            for profile_key in LOCAL_MODEL_PROVIDER_PROFILE_KEYS:
                if profile_key in supplied:
                    profiles[provider][profile_key] = _coerce_to_default_type(profile_key, supplied[profile_key])
        return profiles

    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y", "on"}:
                return True
            if lowered in {"false", "0", "no", "n", "off"}:
                return False
        raise SettingsError(f"Setting {key} expects a boolean value.")

    if isinstance(default, int) and not isinstance(default, bool):
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise SettingsError(f"Setting {key} expects an integer value.") from error
        if parsed < 0:
            raise SettingsError(f"Setting {key} cannot be negative.")
        return parsed

    if isinstance(default, float):
        try:
            parsed = float(value)
        except (TypeError, ValueError) as error:
            raise SettingsError(f"Setting {key} expects a number.") from error
        if parsed < 0:
            raise SettingsError(f"Setting {key} cannot be negative.")
        return parsed

    if isinstance(default, str):
        parsed = str(value).strip()
        if key == "safe_mode" and parsed not in {"strict"}:
            raise SettingsError("safe_mode currently supports only: strict")
        if key == "local_model_provider" and parsed.lower() not in {"ollama", "llama_cpp"}:
            raise SettingsError("local_model_provider supports only: ollama, llama_cpp")
        if key == "local_model_thinking_mode" and parsed not in {"auto", "off", "on"}:
            raise SettingsError("local_model_thinking_mode supports only: auto, off, on")
        if key in {"ollama_base_url", "local_model_endpoint", "local_model_embedding_endpoint"}:
            parsed = parsed.rstrip("/")
        if not parsed and key not in {"local_model_stop_sequences", "local_model_embedding_endpoint"}:
            raise SettingsError(f"Setting {key} cannot be empty.")
        return parsed

    return value


def coerce_setting_value(key: str, value: Any) -> Any:
    """Validate and normalize one setting without writing it."""
    return _coerce_to_default_type(key, value)


def validate_settings_patch(
    patch: dict[str, Any],
    *,
    allowed_keys: set[str] | None = None,
    base_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a validated merged settings mapping without writing runtime state."""
    if not isinstance(patch, dict):
        raise SettingsError("Settings update must be a JSON object.")
    merged = deepcopy(base_settings if base_settings is not None else load_settings())
    for key, value in patch.items():
        if allowed_keys is not None and key not in allowed_keys:
            raise SettingsError(f"Setting is not editable here: {key}")
        merged[key] = _coerce_to_default_type(key, value)
    return merged


def load_settings() -> dict[str, Any]:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_FILE.exists():
        settings = deepcopy(DEFAULT_SETTINGS)
        save_settings(settings)
        return settings

    loaded = load_json_file(SETTINGS_FILE, {}, expected_type=dict)

    settings = deepcopy(DEFAULT_SETTINGS)
    if isinstance(loaded, dict):
        for key, value in loaded.items():
            if key not in DEFAULT_SETTINGS:
                continue
            try:
                settings[key] = _coerce_to_default_type(key, value)
            except SettingsError:
                settings[key] = DEFAULT_SETTINGS[key]

    # v2503.4.31 performs one narrow, documented migration: installations that
    # predate the training-capture policy persist its explicit safe defaults.
    # Other missing or malformed settings remain normalized in memory only.
    if isinstance(loaded, dict) and any(key not in loaded for key in TRAINING_CAPTURE_SETTING_KEYS):
        save_settings(settings)
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean = deepcopy(DEFAULT_SETTINGS)

    for key, value in settings.items():
        if key in DEFAULT_SETTINGS:
            clean[key] = _coerce_to_default_type(key, value)

    write_json_atomic(SETTINGS_FILE, clean, expected_type=dict)


def reset_settings() -> dict[str, Any]:
    settings = deepcopy(DEFAULT_SETTINGS)
    save_settings(settings)
    return settings


def get_setting(key: str, default: Any | None = None) -> Any:
    settings = load_settings()
    if key in settings:
        return settings[key]
    return default


def set_setting(key: str, value: Any) -> dict[str, Any]:
    settings = load_settings()
    settings[key] = _coerce_to_default_type(key, value)
    save_settings(settings)
    return settings


def settings_text() -> str:
    settings = load_settings()
    lines = ["# Eidolon Settings", ""]

    for key in sorted(DEFAULT_SETTINGS.keys()):
        value = settings.get(key)
        description = SETTING_DESCRIPTIONS.get(key, "")
        lines.append(f"{key}: {value}")
        if description:
            lines.append(f"  {description}")
    return "\n".join(lines)


def setting_text(key: str) -> str:
    if key not in DEFAULT_SETTINGS:
        return f"Unknown setting: {key}"
    value = get_setting(key)
    description = SETTING_DESCRIPTIONS.get(key, "")
    return f"{key}: {value}\n{description}".strip()


def settings_health() -> dict[str, Any]:
    settings = load_settings()
    from local_model import provider_health

    health = provider_health(settings)
    health["checked_at"] = datetime.now().isoformat(timespec="seconds")
    # Compatibility fields for older dashboard/setup consumers.
    health["ollama_base_url"] = settings.get("ollama_base_url")
    health["local_model"] = settings.get("local_model")
    health["embed_model"] = settings.get("embed_model")
    health["ollama_ok"] = health.get("service_available", False) if health.get("provider") == "ollama" else False
    health["ollama_version"] = health.get("version") if health.get("provider") == "ollama" else None
    health["local_model_installed"] = health.get("model_available")
    health["embed_model_installed"] = health.get("embed_model_available")
    health["errors"] = [health["error"]["message"]] if health.get("error") else []
    return health

def settings_health_text() -> str:
    health = settings_health()
    lines = ["# Settings health", ""]
    lines.append(f"Checked at: {health.get('checked_at')}")
    lines.append(f"Provider: {health.get('provider')}")
    lines.append(f"Endpoint: {health.get('endpoint')}")
    lines.append(f"Service available: {health.get('service_available')}")
    lines.append(f"Provider version/health: {health.get('version')}")
    lines.append(f"Local model: {health.get('configured_model')} | installed: {health.get('model_available')}")
    lines.append(f"Embedding model: {health.get('configured_embed_model')} | installed: {health.get('embed_model_available')}")
    lines.append("")
    lines.append("Available models:")
    for model in health.get("models", []):
        lines.append(f"- {model}")
    if not health.get("models"):
        lines.append("- [none reported]")
    if health.get("error"):
        lines.extend(["", "Error:", f"- {health['error'].get('code')}: {health['error'].get('message')}"])
    return "\n".join(lines)

def print_settings() -> None:
    print(settings_text())


def print_get_setting(key: str) -> None:
    print(setting_text(key))


def print_set_setting(key: str, value: str) -> None:
    try:
        settings = set_setting(key, value)
    except SettingsError as error:
        print(f"Setting was not changed: {error}")
        return

    print(f"Updated setting: {key} = {settings.get(key)}")


def print_reset_settings() -> None:
    reset_settings()
    print("Settings reset to defaults.")


def print_settings_health() -> None:
    print(settings_health_text())
