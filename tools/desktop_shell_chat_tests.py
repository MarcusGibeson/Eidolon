from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from desktop_shell import (  # noqa: E402
    _desktop_chat_response,
    _desktop_restart_command,
    _load_desktop_geometry,
    _save_desktop_geometry,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, str]] = []

    def check(name: str, condition: object) -> None:
        if not condition:
            raise AssertionError(name)
        checks.append({"name": name, "status": "pass"})

    check(
        "eidolon_response_wins_over_receipt",
        _desktop_chat_response({
            "data": {"eidolon_response": "Actual generated reply."},
            "message": "Dashboard chat turn saved: example",
        }) == "Actual generated reply.",
    )
    check(
        "ai_disabled_explanation_is_visible",
        _desktop_chat_response({
            "data": {"eidolon_response": "Local generation is off."},
            "message": "Dashboard chat turn saved: example",
        }) == "Local generation is off.",
    )
    check(
        "legacy_response_fallback_remains_supported",
        _desktop_chat_response({"data": {"response": "Legacy reply."}}) == "Legacy reply.",
    )
    source = (AGENT / "desktop_shell.py").read_text(encoding="utf-8")
    check(
        "desktop_explicitly_requests_enabled_chat_generation",
        '"use_ai": bool(get_setting("ai_chat_enabled", True))' in source,
    )
    check("desktop_allows_local_generation_timeout", "timeout=180" in source)
    restart_command = _desktop_restart_command()
    check("desktop_restart_uses_current_python", restart_command[0] == sys.executable)
    check("desktop_restart_targets_main", Path(restart_command[1]).resolve() == (AGENT / "main.py").resolve())
    check("desktop_restart_selects_desktop_mode", restart_command[2:] == ["--desktop"])
    check("desktop_header_exposes_restart", 'themed_button(header, "Restart"' in source)
    check(
        "desktop_restart_is_left_of_activity",
        source.index("settings_button.pack") < source.index("activity_button.pack") < source.index("restart_button.pack"),
    )
    check("desktop_restart_is_blocked_during_chat", 'restart_button.configure(state="disabled" if busy else "normal")' in source)
    check("desktop_restart_launches_replacement", "_spawn_desktop_replacement()" in source)
    with tempfile.TemporaryDirectory(prefix="eidolon-desktop-geometry-") as temp:
        state_path = Path(temp) / "window_state.json"
        check("desktop_geometry_saves", _save_desktop_geometry("1180x820-240+75", state_path))
        check("desktop_geometry_restores", _load_desktop_geometry(state_path) == "1180x820-240+75")
        check("desktop_geometry_rejects_invalid_state", not _save_desktop_geometry("not geometry", state_path))

    report = {
        "suite": "desktop-shell-chat-repair",
        "ok": True,
        "passed": len(checks),
        "total": len(checks),
        "checks": checks,
        "provider_contacted": False,
        "runtime_mutated": False,
    }
    print(json.dumps(report, indent=2) if args.json else f"pass: {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
