from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from version_state import VERSION_STATE_VERSION, version_marker_summary

SELF_MAINTENANCE_VERSION_PACKAGE_GATES_VERSION = RUNTIME_VERSION
VERSION_PACKAGE_GATE_BOUNDARIES: dict[str, bool] = {
    "version_package_gates_write_files": False,
    "version_package_gates_mutate_source": False,
    "version_package_gates_build_package": False,
    "version_package_gates_publish_release": False,
    "version_package_gates_create_release_candidate": False,
    "version_package_gates_continue_automatically": False,
    "version_package_gates_review_only": True,
    "source_only_package_policy_required": True,
}

FORBIDDEN_SOURCE_PACKAGE_PATH_FRAGMENTS = [
    "data/autonomy/",
    "data/runtime/",
    "data/logs/",
    "__pycache__/",
    ".pytest_cache/",
    "runtime_outputs/",
]

def summarize_version_package_gates(root: Path | None = None, expected_version: str = SELF_MAINTENANCE_VERSION_PACKAGE_GATES_VERSION) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[1]
    marker_summary = version_marker_summary(root, expected_version)
    return {
        "version": SELF_MAINTENANCE_VERSION_PACKAGE_GATES_VERSION,
        "state": "version_and_package_gate_extraction",
        "expected_version": expected_version,
        "version_state_helper_version": VERSION_STATE_VERSION,
        "marker_summary": marker_summary,
        "forbidden_source_package_path_fragments": list(FORBIDDEN_SOURCE_PACKAGE_PATH_FRAGMENTS),
        "writes_files": False,
        "mutates_source": False,
        "builds_package": False,
        "publishes_release": False,
        "ok": bool(marker_summary.get("ok")),
    }

def version_package_gate_tokens() -> list[str]:
    return [
        "version marker summary checks",
        "current-version expectation helpers",
        "package privacy/source-only expectations",
        "forbidden path scan helpers",
        "release metadata consistency checks",
    ]
