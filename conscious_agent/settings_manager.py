from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any

import requests

from paths import DATA_DIR


SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "settings_version": "15.0",
    "local_model": "qwen2.5:7b",
    "embed_model": "nomic-embed-text:latest",
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
    "desktop_launch_dashboard_on_start": False,
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
    "last_updated_for": "v15.0",
    "release_pipeline_enabled": True,
    "approval_binding_required_for_draft_apply": True,
    "safe_rewrite_preview_required": True,
}

SETTING_DESCRIPTIONS: dict[str, str] = {
    "settings_version": "Settings schema version.",
    "last_updated_for": "Last packaged project version that updated the settings schema/defaults.",
    "release_pipeline_enabled": "Whether the human-approved release pipeline reports and commands are enabled.",
    "approval_binding_required_for_draft_apply": "Whether approved draft apply must validate the exact saved draft artifact snapshot.",
    "safe_rewrite_preview_required": "Whether code patch apply requires a hash-checked safe rewrite preview before writing files.",
    "local_model": "Ollama model used for local chat, reviews, patch suggestions, and summaries.",
    "embed_model": "Ollama embedding model used for semantic memory.",
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

    if isinstance(default, str):
        parsed = str(value).strip()
        if key == "safe_mode" and parsed not in {"strict"}:
            raise SettingsError("safe_mode currently supports only: strict")
        if key == "ollama_base_url":
            parsed = parsed.rstrip("/")
        if not parsed:
            raise SettingsError(f"Setting {key} cannot be empty.")
        return parsed

    return value


def load_settings() -> dict[str, Any]:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_FILE.exists():
        settings = deepcopy(DEFAULT_SETTINGS)
        save_settings(settings)
        return settings

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, json.JSONDecodeError):
        loaded = {}

    settings = deepcopy(DEFAULT_SETTINGS)
    if isinstance(loaded, dict):
        for key, value in loaded.items():
            if key not in DEFAULT_SETTINGS:
                continue
            try:
                settings[key] = _coerce_to_default_type(key, value)
            except SettingsError:
                settings[key] = DEFAULT_SETTINGS[key]

    if loaded != settings:
        save_settings(settings)

    return settings


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean = deepcopy(DEFAULT_SETTINGS)

    for key, value in settings.items():
        if key in DEFAULT_SETTINGS:
            clean[key] = _coerce_to_default_type(key, value)

    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(clean, file, indent=2)


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
    base_url = str(settings.get("ollama_base_url", DEFAULT_SETTINGS["ollama_base_url"])).rstrip("/")
    timeout = int(settings.get("ollama_timeout_seconds", DEFAULT_SETTINGS["ollama_timeout_seconds"]))

    result: dict[str, Any] = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "ollama_base_url": base_url,
        "local_model": settings.get("local_model"),
        "embed_model": settings.get("embed_model"),
        "ollama_ok": False,
        "ollama_version": None,
        "models": [],
        "local_model_installed": False,
        "embed_model_installed": False,
        "errors": [],
    }

    try:
        version_response = requests.get(f"{base_url}/api/version", timeout=timeout)
        version_response.raise_for_status()
        version_data = version_response.json()
        result["ollama_ok"] = True
        result["ollama_version"] = version_data.get("version", version_data)
    except requests.exceptions.RequestException as error:
        result["errors"].append(f"Ollama version check failed: {error}")
        return result

    try:
        tags_response = requests.get(f"{base_url}/api/tags", timeout=timeout)
        tags_response.raise_for_status()
        tags_data = tags_response.json()
        models = [model.get("name", "") for model in tags_data.get("models", []) if isinstance(model, dict)]
        result["models"] = sorted(model for model in models if model)
        result["local_model_installed"] = settings.get("local_model") in result["models"]
        result["embed_model_installed"] = settings.get("embed_model") in result["models"]
    except requests.exceptions.RequestException as error:
        result["errors"].append(f"Ollama model list check failed: {error}")

    return result


def settings_health_text() -> str:
    health = settings_health()
    lines = ["# Settings health", ""]
    lines.append(f"Checked at: {health.get('checked_at')}")
    lines.append(f"Ollama URL: {health.get('ollama_base_url')}")
    lines.append(f"Ollama reachable: {health.get('ollama_ok')}")
    lines.append(f"Ollama version: {health.get('ollama_version')}")
    lines.append(f"Local model: {health.get('local_model')} | installed: {health.get('local_model_installed')}")
    lines.append(f"Embedding model: {health.get('embed_model')} | installed: {health.get('embed_model_installed')}")
    lines.append("")
    lines.append("Installed models:")
    for model in health.get("models", []):
        lines.append(f"- {model}")
    if not health.get("models"):
        lines.append("- [none found]")
    if health.get("errors"):
        lines.append("")
        lines.append("Errors:")
        for error in health.get("errors", []):
            lines.append(f"- {error}")
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
