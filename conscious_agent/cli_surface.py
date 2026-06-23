from __future__ import annotations

from typing import Any

CLI_SURFACE_VERSION = "350.0"

DEFAULT_CLI_SURFACE_HELPERS = [
    {"name": "cli_command_metadata_binder", "purpose": "summarize CLI command metadata", "changes_behavior": False},
    {"name": "cli_json_response_renderer", "purpose": "document JSON response rendering helpers", "changes_behavior": False},
    {"name": "cli_human_summary_renderer", "purpose": "document human-readable CLI summaries", "changes_behavior": False},
    {"name": "dynamic_command_summary", "purpose": "summarize dynamic command coverage", "changes_behavior": False},
    {"name": "cli_surface_parity_checker", "purpose": "flag missing CLI flags for review only", "executes_commands": False},
]


def cli_flag_tokens() -> list[str]:
    return [
        "--operator-governed-dashboard-surface-extraction-map",
        "--operator-governed-dashboard-component-helper-extraction",
        "--operator-governed-api-surface-helper-extraction",
        "--operator-governed-cli-surface-helper-extraction",
        "--operator-governed-dashboard-api-cli-modularization-v1",
    ]


def build_cli_surface_summary(main_text: str = "", cli_flags: list[str] | None = None) -> dict[str, Any]:
    flags = cli_flags or cli_flag_tokens()
    present = [flag for flag in flags if flag in main_text] if main_text else []
    return {
        "version": CLI_SURFACE_VERSION,
        "helper_count": len(DEFAULT_CLI_SURFACE_HELPERS),
        "helpers": DEFAULT_CLI_SURFACE_HELPERS,
        "flag_count": len(flags),
        "flags_present": present,
        "flags_missing": [flag for flag in flags if flag not in present] if main_text else [],
        "uses_dynamic_cli_map": "SUPERVISED_RUNTIME_CLI_MAP" in main_text if main_text else True,
        "changes_behavior": False,
        "executes_commands": False,
        "auto_dispatches_work": False,
    }


def cli_surface_summary_lines(summary: dict[str, Any]) -> list[str]:
    return [
        f"- CLI helper count: {summary.get('helper_count', 0)}.",
        f"- CLI flags present: {len(summary.get('flags_present', []))}/{summary.get('flag_count', 0)}.",
        f"- Dynamic CLI map preserved: {summary.get('uses_dynamic_cli_map', False)}.",
        f"- CLI behavior changed: {summary.get('changes_behavior', False)}.",
        f"- CLI executes commands: {summary.get('executes_commands', False)}.",
    ]
