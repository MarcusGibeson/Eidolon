from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

PACKAGE_INTEGRITY_VERSION = "1032.0"
# Static runtime/private/generated source-package denylist. These are matched
# against normalized archive/repository entries after allowlisted source metadata
# files have been exempted.
FORBIDDEN_RUNTIME_PARTS = (
    "/data/approvals/",
    "/data/autonomy/",
    "/data/self_maintenance/",
    "/data/workspaces/",
    "/data/release_package/",
    "/data/releases/",
    "/data/stable_loops/",
    "/data/work_cycles/",
    "/runtime/",
    "/.venv/",
    "/venv/",
    "/__pycache__/",
    "/.pytest_cache/",
    "/.mypy_cache/",
)

SOURCE_DATA_ALLOWLIST = (
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/projects.json",
    "data/workspaces/active_project.json",
    "data/workspaces/command_profiles/default_java.json",
    "data/workspaces/command_profiles/default_node.json",
    "data/workspaces/command_profiles/default_python.json",
    "data/workspaces/command_profiles/eidolon.json",
    "data/signing/trusted_public_keys.json",
)

SOURCE_ONLY_POLICY = {
    "includes_source_modules": True,
    "excludes_runtime_data": True,
    "excludes_private_state": True,
    "excludes_generated_reports": True,
    "rejects_workspace_runtime_timelines": True,
    "checks_final_archive_entries": True,
    "operator_review_required_for_release": True,
    "content_scans_allowlisted_data": True,
    "blocks_private_self_state_content": True,
}

# These are content-aware checks for source-only packages. They intentionally
# inspect data/ JSON and text entries rather than Python source/comments, so the
# scanner can contain its own private-state vocabulary without failing itself.
PRIVATE_USER_IDENTIFIER_TOKENS = ("Marcus", "Gibeson")
PRIVATE_SELF_STATE_KEYS = {"mood", "focus", "energy", "uncertainty", "self_model", "active_goals"}
RUNTIME_GOAL_STATE_KEYS = {"active_goals", "runtime_goals", "current_runtime_goal"}
APPROVAL_OR_ACTION_TRACE_KEYS = {"approvals", "approval_requests", "action_log", "chat_actions", "dashboard_chat"}
MEMORY_LIKE_STATE_KEYS = {"memory", "memories", "memory_items", "thoughts", "thought_log"}
CONTENT_SCAN_SUFFIXES = {".json", ".txt", ".md", ".yaml", ".yml"}
MAX_CONTENT_SCAN_BYTES = 2_000_000


def normalize_entry(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def strip_package_root(normalized: str) -> str:
    stripped = normalized.strip("/")
    if stripped.startswith("Eidolon/"):
        stripped = stripped[len("Eidolon/"):]
    return stripped


def _source_allowlisted(normalized: str) -> bool:
    return strip_package_root(normalized) in SOURCE_DATA_ALLOWLIST


def _content_scan_eligible(normalized: str) -> bool:
    stripped = strip_package_root(normalized)
    suffix = Path(stripped).suffix.lower()
    return stripped.startswith("data/") and suffix in CONTENT_SCAN_SUFFIXES


def source_surface_runtime_parts() -> list[str]:
    """Return runtime directories declared by the source surface manifest.

    Import is intentionally local so package_integrity remains usable in small
    release tooling contexts. The manifest is review-only and grants no package
    creation authority; this helper only lets privacy rules and surface metadata
    agree about what must stay out of source-only archives.
    """
    try:
        from source_surface_manifest import RECENT_SURFACE_ENTRIES
    except Exception:
        return []
    parts: set[str] = set()
    for entry in RECENT_SURFACE_ENTRIES:
        if entry.get("package_privacy_sensitive") is False:
            continue
        runtime = str(entry.get("runtime_directory") or "").replace("\\", "/").strip()
        if runtime:
            parts.add("/" + runtime.strip("/") + "/")
    return sorted(parts)


def forbidden_runtime_parts(include_manifest: bool = True) -> list[str]:
    parts = set(FORBIDDEN_RUNTIME_PARTS)
    if include_manifest:
        parts.update(source_surface_runtime_parts())
    return sorted(parts)


def forbidden_runtime_path_matches(entries: Iterable[str | Path]) -> list[str]:
    matches: list[str] = []
    parts = forbidden_runtime_parts(include_manifest=True)
    for entry in entries:
        raw = normalize_entry(entry)
        stripped = strip_package_root(raw)
        normalized = "/" + raw.strip("/")
        if _source_allowlisted(normalized):
            continue
        if stripped.startswith("data/"):
            matches.append(raw)
            continue
        if any(part in normalized for part in parts):
            matches.append(raw)
    return sorted(dict.fromkeys(matches))


def _finding(entry: str, category: str, detail: str, json_path: str = "") -> dict[str, Any]:
    return {
        "entry": normalize_entry(entry),
        "category": category,
        "detail": detail,
        "json_path": json_path,
    }


def _json_private_content_findings(value: Any, entry: str, path: str = "") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            child_path = f"{path}.{key_text}" if path else key_text
            if key_lower in PRIVATE_SELF_STATE_KEYS:
                findings.append(_finding(entry, "private_self_state_content_detected", f"private/self-state key {key_text!r}", child_path))
            if key_lower in RUNTIME_GOAL_STATE_KEYS:
                findings.append(_finding(entry, "runtime_goal_state_detected", f"runtime goal-state key {key_text!r}", child_path))
            if key_lower in APPROVAL_OR_ACTION_TRACE_KEYS:
                findings.append(_finding(entry, "approval_or_action_trace_detected", f"approval/action/chat trace key {key_text!r}", child_path))
            if key_lower in MEMORY_LIKE_STATE_KEYS:
                findings.append(_finding(entry, "memory_like_state_detected", f"memory-like state key {key_text!r}", child_path))
            if key_lower == "private_key_material_allowed" and child not in (False, "false", "False", 0, None):
                findings.append(_finding(entry, "private_key_material_detected", "private key material allowed flag is not false", child_path))
            findings.extend(_json_private_content_findings(child, entry, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_json_private_content_findings(child, entry, f"{path}[{index}]" if path else f"[{index}]"))
    elif isinstance(value, str):
        for token in PRIVATE_USER_IDENTIFIER_TOKENS:
            if token in value:
                findings.append(_finding(entry, "user_specific_identifier_detected", f"user-specific identifier token {token!r}", path))
    return findings


def private_content_findings_for_items(items: Mapping[str, str | bytes]) -> list[dict[str, Any]]:
    """Return private/runtime-state findings for source package content items.

    Items are archive/root-relative paths mapped to text or bytes. Only data/
    JSON/text-like entries are scanned so source code can contain the scanner
    rules without self-triggering. Historical release note strings are not
    treated as runtime state unless they appear as actual private-state keys.
    """
    findings: list[dict[str, Any]] = []
    for entry, raw in items.items():
        normalized = normalize_entry(entry)
        if not _content_scan_eligible(normalized):
            continue
        data = raw if isinstance(raw, bytes) else str(raw).encode("utf-8", errors="ignore")
        if len(data) > MAX_CONTENT_SCAN_BYTES:
            findings.append(_finding(normalized, "content_scan_skipped_too_large", f"entry exceeded {MAX_CONTENT_SCAN_BYTES} bytes"))
            continue
        text = data.decode("utf-8", errors="ignore")
        stripped = strip_package_root(normalized)
        if Path(stripped).suffix.lower() == ".json":
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                findings.append(_finding(normalized, "json_content_unreadable", "JSON data entry could not be parsed"))
                continue
            findings.extend(_json_private_content_findings(parsed, normalized))
        else:
            for token in PRIVATE_USER_IDENTIFIER_TOKENS:
                if token in text:
                    findings.append(_finding(normalized, "user_specific_identifier_detected", f"user-specific identifier token {token!r}"))
    return sorted(findings, key=lambda row: (row["entry"], row["category"], row.get("json_path", "")))


def privacy_deep_scan_summary(items: Mapping[str, str | bytes] | None = None) -> dict[str, Any]:
    content_items = items or {}
    findings = private_content_findings_for_items(content_items)
    categories = sorted({finding["category"] for finding in findings})
    scanned_entries = [entry for entry in content_items if _content_scan_eligible(entry)]
    return {
        "version": PACKAGE_INTEGRITY_VERSION,
        "content_scan_available": bool(content_items),
        "content_scanned_file_count": len(scanned_entries),
        "private_content_finding_count": len(findings),
        "private_content_findings": findings,
        "blocked_content_categories": categories,
        "private_self_state_content_detected": any(f["category"] == "private_self_state_content_detected" for f in findings),
        "user_specific_identifier_detected": any(f["category"] == "user_specific_identifier_detected" for f in findings),
        "runtime_goal_state_detected": any(f["category"] == "runtime_goal_state_detected" for f in findings),
        "approval_or_action_trace_detected": any(f["category"] == "approval_or_action_trace_detected" for f in findings),
        "memory_like_state_detected": any(f["category"] == "memory_like_state_detected" for f in findings),
        "allowlisted_template_count": 0,
        "ok": not findings,
        "authorizes_packaging": False,
        "review_only": True,
    }


def iter_source_tree_entries(root: str | Path) -> list[str]:
    root_path = Path(root)
    entries: list[str] = []
    if not root_path.exists():
        return entries
    skipped_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    skipped_suffixes = {".pyc", ".pyo", ".log", ".zip"}
    skipped_exact = {"data/workspaces/timeline.json"}
    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root_path)
        rel = rel_path.as_posix()
        if rel in skipped_exact:
            continue
        if rel.startswith("data/") and rel not in SOURCE_DATA_ALLOWLIST:
            # Runtime/private local data stays out of root privacy inventory and final archives.
            # Direct zip-entry scans still flag these paths as forbidden.
            continue
        if any(part in skipped_dirs for part in rel_path.parts):
            continue
        if path.suffix in skipped_suffixes:
            continue
        entries.append(rel)
    return entries


def _source_tree_content_items(root: str | Path, entries: Iterable[str]) -> dict[str, bytes]:
    root_path = Path(root)
    items: dict[str, bytes] = {}
    for rel in entries:
        if not _content_scan_eligible(rel):
            continue
        path = root_path / strip_package_root(rel)
        if path.exists() and path.is_file():
            try:
                items[rel] = path.read_bytes()
            except OSError:
                continue
    return items


def package_privacy_summary_for_root(root: str | Path) -> dict[str, Any]:
    entries = iter_source_tree_entries(root)
    summary = package_privacy_summary(entries)
    deep_scan = privacy_deep_scan_summary(_source_tree_content_items(root, entries))
    summary.update({
        "content_scan_available": deep_scan["content_scan_available"],
        "content_scanned_file_count": deep_scan["content_scanned_file_count"],
        "private_content_finding_count": deep_scan["private_content_finding_count"],
        "private_content_findings": deep_scan["private_content_findings"],
        "blocked_content_categories": deep_scan["blocked_content_categories"],
        "privacy_deep_scan": deep_scan,
    })
    summary["ok"] = summary["ok"] and deep_scan["ok"]
    summary["source_only"] = summary["source_only"] and deep_scan["ok"]
    return summary


def package_privacy_summary_for_zip(zip_path: str | Path) -> dict[str, Any]:
    archive = Path(zip_path)
    if not archive.exists():
        return {
            "version": PACKAGE_INTEGRITY_VERSION,
            "zip_path": normalize_entry(archive),
            "entry_count": 0,
            "forbidden_count": 0,
            "forbidden_entries": [],
            "ok": False,
            "source_only": False,
            "message": "zip archive not found",
            "authorizes_packaging": False,
        }
    try:
        with zipfile.ZipFile(archive) as zf:
            entries = [info.filename for info in zf.infolist() if not info.is_dir()]
            items = {
                info.filename: zf.read(info.filename)
                for info in zf.infolist()
                if not info.is_dir() and _content_scan_eligible(info.filename) and info.file_size <= MAX_CONTENT_SCAN_BYTES
            }
    except (OSError, zipfile.BadZipFile) as error:
        return {
            "version": PACKAGE_INTEGRITY_VERSION,
            "zip_path": normalize_entry(archive),
            "entry_count": 0,
            "forbidden_count": 0,
            "forbidden_entries": [],
            "ok": False,
            "source_only": False,
            "message": f"zip archive unreadable: {error}",
            "authorizes_packaging": False,
        }
    summary = package_privacy_summary(entries)
    deep_scan = privacy_deep_scan_summary(items)
    summary.update({
        "zip_path": normalize_entry(archive),
        "checks_final_archive_entries": True,
        "content_scan_available": deep_scan["content_scan_available"],
        "content_scanned_file_count": deep_scan["content_scanned_file_count"],
        "private_content_finding_count": deep_scan["private_content_finding_count"],
        "private_content_findings": deep_scan["private_content_findings"],
        "blocked_content_categories": deep_scan["blocked_content_categories"],
        "privacy_deep_scan": deep_scan,
    })
    summary["ok"] = summary["ok"] and deep_scan["ok"]
    summary["source_only"] = summary["source_only"] and deep_scan["ok"]
    return summary


def source_only_entry_policy() -> dict[str, Any]:
    return {
        "version": PACKAGE_INTEGRITY_VERSION,
        "policy": dict(SOURCE_ONLY_POLICY),
        "forbidden_runtime_parts": forbidden_runtime_parts(include_manifest=True),
        "source_data_allowlist": list(SOURCE_DATA_ALLOWLIST),
        "private_content_key_categories": {
            "private_self_state": sorted(PRIVATE_SELF_STATE_KEYS),
            "runtime_goal_state": sorted(RUNTIME_GOAL_STATE_KEYS),
            "approval_or_action_trace": sorted(APPROVAL_OR_ACTION_TRACE_KEYS),
            "memory_like_state": sorted(MEMORY_LIKE_STATE_KEYS),
            "user_identifiers": list(PRIVATE_USER_IDENTIFIER_TOKENS),
        },
        "manifest_runtime_parts_imported": bool(source_surface_runtime_parts()),
        "content_scans_allowlisted_data": True,
        "authorizes_package_creation": False,
        "publishes_release": False,
    }


def package_privacy_summary(entries: Iterable[str | Path] | None = None) -> dict[str, Any]:
    entry_list = [normalize_entry(item) for item in (entries or [])]
    forbidden = forbidden_runtime_path_matches(entry_list)
    return {
        "version": PACKAGE_INTEGRITY_VERSION,
        "entry_count": len(entry_list),
        "forbidden_count": len(forbidden),
        "forbidden_entries": forbidden,
        "ok": not forbidden,
        "source_only": not forbidden,
        "content_scan_available": False,
        "content_scanned_file_count": 0,
        "private_content_finding_count": 0,
        "private_content_findings": [],
        "blocked_content_categories": [],
        "rejects_workspace_runtime_timelines": "data/workspaces/timeline.json" in forbidden_runtime_path_matches(["data/workspaces/timeline.json"]),
        "checks_final_archive_entries": True,
        "authorizes_packaging": False,
    }


# v501-v505 source-only package privacy repair tokens: final_archive_entry_privacy_checker=True data/workspaces/timeline.json forbidden source_surface_manifest_runtime_dirs_imported=True source_only_package_privacy_pass_is_authorization=False package_privacy_summary_for_zip authorizes_package_creation=False publishes_release=False

# v711.0-v760.0 package privacy repair tokens: data/tasks.json forbidden data/approvals/README.md forbidden non_allowlisted_data_forbidden=True source_only_zip_excludes_private_runtime_data=True

# v865.0 operator-approved sandbox probe package privacy tokens: sandbox/generated_validation_probes package_privacy_sensitive=False allowed_source_sandbox_artifact=True generated_probe_files_not_private_runtime=True
# v905.0 source metadata privacy tightening tokens: data/self_model.json source_metadata_allowed=False source_only_package_privacy_pass_is_authorization=False
# v909.0 source package privacy deep scan tokens: source-package-privacy-deep-scan-v1 --source-package-privacy-deep-scan build_source_package_privacy_deep_scan_review source_package_privacy_deep_scan_review_text privacy_deep_scan_summary private_content_findings_for_items content_scans_allowlisted_data=True blocks_private_self_state_content=True user_specific_identifier_detected runtime_goal_state_detected approval_or_action_trace_detected memory_like_state_detected data/self_model.json source_metadata_allowed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True
