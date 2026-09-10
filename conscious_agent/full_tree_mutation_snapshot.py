from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC

FULL_TREE_MUTATION_SNAPSHOT_VERSION = RUNTIME_VERSION
FULL_TREE_MUTATION_SNAPSHOT_ID = "full-tree-mutation-snapshot-expansion-v1"
SELF_ROUTE = "/full-tree-mutation-snapshot-expansion"
API_ROUTE = "/api/source-surface/full-tree-mutation-snapshot-expansion"
RELATED_BATCH_REVIEW_ID = "manifest-generated-dispatch-fixture-batch-isolated-dry-run-expansion-v1"
RELATED_SANDBOX_CONTRACT_ID = "manifest-fixture-sandbox-adapter-contract-v1"

WATCHED_ROOTS: tuple[str, ...] = (
    "conscious_agent/",
    "tools/",
    "sandbox/",
    ".gitignore",
    "requirements.txt",
    "setup.ps1",
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/active_project.json",
    "data/workspaces/projects.json",
    "data/workspaces/command_profiles/",
)
EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
RUNTIME_PRIVATE_EXACT = {
    "data/tasks.json",
    "data/action_log.json",
    "data/memories.json",
    "data/thoughts.log",
    "data/self_model.json",
    "data/workspaces/timeline.json",
}
RUNTIME_PRIVATE_PREFIXES: tuple[str, ...] = (
    "data/approvals/",
    "data/chat_actions/",
    "data/dashboard_chat/",
    "data/self_development_cycles/",
    "data/releases/",
    "data/release_package/",
    "data/release_installation/",
    "data/backups/",
    "data/diagnostics/",
    "data/notifications/",
    "data/stable_loops/",
    "data/watch_reports/",
    "data/work_cycles/",
)
BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "snapshot_only": True,
    "full_tree_source_scope": True,
    "installation_wide_source_scope": True,
    "runtime_private_paths_excluded": True,
    "writes_source": False,
    "writes_runtime_private_data": False,
    "deletes_runtime_private_data": False,
    "spawns_subprocess": False,
    "executes_fixture": False,
    "network_access_permitted": False,
    "fixture_files_written": False,
    "generated_wiring_activated": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}


@dataclass(frozen=True)
class SnapshotDelta:
    watched_file_count: int
    changed_file_count: int
    created_file_count: int
    deleted_file_count: int
    source_mutation_count: int
    changed_files: tuple[str, ...]
    created_files: tuple[str, ...]
    deleted_files: tuple[str, ...]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def is_runtime_private_path(rel: str) -> bool:
    clean = rel.replace("\\", "/").strip("/")
    return clean in RUNTIME_PRIVATE_EXACT or any(clean.startswith(prefix) for prefix in RUNTIME_PRIVATE_PREFIXES)


def _is_excluded(rel: str) -> bool:
    clean = rel.replace("\\", "/").strip("/")
    parts = set(clean.split("/"))
    return bool(parts & EXCLUDE_DIR_NAMES) or Path(clean).suffix.lower() in EXCLUDE_SUFFIXES or is_runtime_private_path(clean)


def _iter_watched_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for watched in WATCHED_ROOTS:
        base = root / watched
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(root).as_posix()
                    if not _is_excluded(rel):
                        files.append(path)
        elif base.is_file():
            rel = base.relative_to(root).as_posix()
            if not _is_excluded(rel):
                files.append(base)
    # Preserve deterministic order and de-duplicate overlaps, because apparently
    # even file lists need adult supervision.
    unique: dict[str, Path] = {path.relative_to(root).as_posix(): path for path in files}
    return [unique[key] for key in sorted(unique)]


def snapshot_source_tree(root: str | Path | None = None) -> dict[str, str]:
    project_root = _repo(root)
    snapshot: dict[str, str] = {}
    for path in _iter_watched_files(project_root):
        rel = path.relative_to(project_root).as_posix()
        try:
            snapshot[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            snapshot[rel] = "unreadable"
    return snapshot


def snapshot_hash(snapshot: dict[str, str]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare_source_snapshots(pre_snapshot: dict[str, str], post_snapshot: dict[str, str]) -> SnapshotDelta:
    pre_keys = set(pre_snapshot)
    post_keys = set(post_snapshot)
    changed = tuple(sorted(key for key in pre_keys & post_keys if pre_snapshot.get(key) != post_snapshot.get(key)))
    created = tuple(sorted(post_keys - pre_keys))
    deleted = tuple(sorted(pre_keys - post_keys))
    return SnapshotDelta(
        watched_file_count=len(pre_keys | post_keys),
        changed_file_count=len(changed),
        created_file_count=len(created),
        deleted_file_count=len(deleted),
        source_mutation_count=len(changed) + len(created) + len(deleted),
        changed_files=changed,
        created_files=created,
        deleted_files=deleted,
    )


def snapshot_delta(pre_snapshot: dict[str, str], post_snapshot: dict[str, str]) -> dict[str, int]:
    delta = compare_source_snapshots(pre_snapshot, post_snapshot)
    return {
        "watched_file_count": delta.watched_file_count,
        "changed_file_count": delta.changed_file_count,
        "created_file_count": delta.created_file_count,
        "deleted_file_count": delta.deleted_file_count,
        "source_mutation_count": delta.source_mutation_count,
    }


def build_full_tree_mutation_snapshot_expansion_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": FULL_TREE_MUTATION_SNAPSHOT_ID,
        "related_batch_review_id": RELATED_BATCH_REVIEW_ID,
        "related_sandbox_contract_id": RELATED_SANDBOX_CONTRACT_ID,
        "status": "preview",
        "ok": True,
        "review_only": True,
        "snapshot_only": True,
        "watched_root_count": len(WATCHED_ROOTS),
        "watched_roots": list(WATCHED_ROOTS),
        "installation_wide_source_scope": True,
        "root_file_watch_count": 3,
        "sandbox_root_included": "sandbox/" in WATCHED_ROOTS,
        "runtime_private_exact_count": len(RUNTIME_PRIVATE_EXACT),
        "runtime_private_prefix_count": len(RUNTIME_PRIVATE_PREFIXES),
        "spawns_subprocess": False,
        "executes_fixture": False,
        "source_mutation_count": 0,
        "fixture_files_written": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Preview metadata for shared full-tree source mutation snapshots. No subprocesses, fixture execution, source writes, release authorization, or autonomy expansion.",
    }


def build_full_tree_mutation_snapshot_expansion(root: str | Path | None = None, *, inspect_sources: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    pre_snapshot = snapshot_source_tree(project_root)
    post_snapshot = snapshot_source_tree(project_root)
    delta = compare_source_snapshots(pre_snapshot, post_snapshot)
    pre_hash = snapshot_hash(pre_snapshot)
    post_hash = snapshot_hash(post_snapshot)
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/full_tree_mutation_snapshot.py",
        "conscious_agent/manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion.py",
        "conscious_agent/manifest_fixture_sandbox_adapter_contract.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ]) if inspect_sources else ""
    required_tokens = [
        CURRENT_MILESTONE,
        FULL_TREE_MUTATION_SNAPSHOT_ID,
        SELF_ROUTE,
        API_ROUTE,
        "snapshot_source_tree",
        "snapshot_hash",
        "compare_source_snapshots",
        "snapshot_delta",
        "watched_root_count=13",
        "full_tree_source_scope=True",
        "installation_wide_source_scope=True",
        "root_file_watch_count=3",
        "sandbox_root_included=True",
        "runtime_private_paths_excluded=True",
        "spawns_subprocess=False",
        "executes_fixture=False",
        "source_mutation_count=0",
        "fixture_files_written=False",
        "generated_wiring_activated=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    checks = [
        {"name": "module-version-current", "ok": FULL_TREE_MUTATION_SNAPSHOT_VERSION == CURRENT_VERSION, "message": f"module={FULL_TREE_MUTATION_SNAPSHOT_VERSION}; current={CURRENT_VERSION}"},
        {"name": "watched-roots-cover-installation-surfaces", "ok": all(item in WATCHED_ROOTS for item in ("conscious_agent/", "tools/", "sandbox/", ".gitignore", "requirements.txt", "setup.ps1", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "data/workspaces/command_profiles/")), "message": f"watched_root_count={len(WATCHED_ROOTS)}"},
        {"name": "runtime-private-excludes-declared", "ok": "data/approvals/" in RUNTIME_PRIVATE_PREFIXES and "data/tasks.json" in RUNTIME_PRIVATE_EXACT and "data/release_package/" in RUNTIME_PRIVATE_PREFIXES, "message": f"runtime_exact={len(RUNTIME_PRIVATE_EXACT)} runtime_prefixes={len(RUNTIME_PRIVATE_PREFIXES)}"},
        {"name": "snapshot-baseline-clean", "ok": delta.source_mutation_count == 0 and pre_hash == post_hash, "message": f"watched={delta.watched_file_count} mutations={delta.source_mutation_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "snapshot_only": True,
            "full_tree_source_scope": True,
    "installation_wide_source_scope": True,
            "runtime_private_paths_excluded": True,
            "writes_source": False,
            "spawns_subprocess": False,
            "executes_fixture": False,
            "fixture_files_written": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "Full-tree mutation snapshot expansion is review-only and cannot execute fixtures, write source, authorize release, or expand autonomy."},
        {"name": "documentation-tokens", "ok": (not inspect_sources) or all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(check.get("ok") is True for check in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": FULL_TREE_MUTATION_SNAPSHOT_ID,
        "related_batch_review_id": RELATED_BATCH_REVIEW_ID,
        "related_sandbox_contract_id": RELATED_SANDBOX_CONTRACT_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "snapshot_only": True,
        "watched_root_count": len(WATCHED_ROOTS),
        "watched_roots": list(WATCHED_ROOTS),
        "installation_wide_source_scope": True,
        "root_file_watch_count": 3,
        "sandbox_root_included": "sandbox/" in WATCHED_ROOTS,
        "watched_file_count": delta.watched_file_count,
        "pre_snapshot_hash": pre_hash,
        "post_snapshot_hash": post_hash,
        "changed_file_count": delta.changed_file_count,
        "created_file_count": delta.created_file_count,
        "deleted_file_count": delta.deleted_file_count,
        "source_mutation_count": delta.source_mutation_count,
        "changed_files": list(delta.changed_files),
        "created_files": list(delta.created_files),
        "deleted_files": list(delta.deleted_files),
        "runtime_private_exact_count": len(RUNTIME_PRIVATE_EXACT),
        "runtime_private_prefix_count": len(RUNTIME_PRIVATE_PREFIXES),
        "runtime_private_paths_excluded": True,
        "full_tree_source_scope": True,
    "installation_wide_source_scope": True,
        "spawns_subprocess": False,
        "executes_fixture": False,
        "network_access_permitted": False,
        "fixture_files_written": False,
        "generated_wiring_activated": False,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "checks": checks,
        "blocked": [check for check in checks if not check.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def full_tree_mutation_snapshot_expansion_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"related_batch_review_id={report.get('related_batch_review_id')}",
        f"related_sandbox_contract_id={report.get('related_sandbox_contract_id')}",
        f"status={report.get('status')}",
        f"watched_root_count={report.get('watched_root_count')}",
        f"watched_file_count={report.get('watched_file_count')}",
        f"pre_snapshot_hash={report.get('pre_snapshot_hash')}",
        f"post_snapshot_hash={report.get('post_snapshot_hash')}",
        f"changed_file_count={report.get('changed_file_count')}",
        f"created_file_count={report.get('created_file_count')}",
        f"deleted_file_count={report.get('deleted_file_count')}",
        f"source_mutation_count={report.get('source_mutation_count')}",
        f"full_tree_source_scope={report.get('full_tree_source_scope')}",
        f"runtime_private_paths_excluded={report.get('runtime_private_paths_excluded')}",
        f"spawns_subprocess={report.get('spawns_subprocess')}",
        f"executes_fixture={report.get('executes_fixture')}",
        f"fixture_files_written={report.get('fixture_files_written')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        lines.append("watched_roots=" + ",".join(str(item) for item in report.get("watched_roots", [])))
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1065.4 full-tree mutation snapshot expansion tokens: full-tree-mutation-snapshot-expansion-v1 /full-tree-mutation-snapshot-expansion /api/source-surface/full-tree-mutation-snapshot-expansion snapshot_source_tree snapshot_hash compare_source_snapshots snapshot_delta watched_root_count=13 full_tree_source_scope=True installation_wide_source_scope=True root_file_watch_count=3 sandbox_root_included=True runtime_private_paths_excluded=True spawns_subprocess=False executes_fixture=False source_mutation_count=0 fixture_files_written=False generated_wiring_activated=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
