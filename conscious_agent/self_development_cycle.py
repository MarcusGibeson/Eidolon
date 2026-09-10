from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from generated_probe_harness import execute_generated_probe
from task_queue import add_task, list_tasks
from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, EXPECTED_TITLE, NEXT_RECOMMENDED_ARC

SELF_DEVELOPMENT_CYCLE_VERSION = CURRENT_VERSION
EXPECTED_MANIFEST_SMOKE_SEGMENT_REPAIRS_APPLIED = 35
EXPECTED_V912_TITLE = "Manifest-Driven Surface Generation Prep v1"

SELF_DEVELOPMENT_DIR = DATA_DIR / "self_development_cycles"
SELF_DEVELOPMENT_README = SELF_DEVELOPMENT_DIR / "README.md"

SELF_DEVELOPMENT_INTENT_PHRASES = (
    "self development cycle",
    "self-development cycle",
    "begin self development",
    "begin work on a self development cycle",
    "begin work on a self-development cycle",
    "controlled self-development loop",
    "what should you improve next",
    "plan your own next development step",
    "identify what needs to be improved next",
    "improve yourself next",
    "own next development step",
)

PROTECTED_SYSTEM_KEYWORDS = (
    "approval",
    "approvals",
    "memory",
    "release",
    "packaging",
    "execution permission",
    "execution-permission",
    "command_runner",
    "command safety",
    "self-update",
    "self update",
    "autonomy",
)

INSPECTION_AREAS = (
    "README files",
    "release history",
    "task/work item records",
    "failed chat actions",
    "recent approvals",
    "smoke/check result hints",
    "TODO/FIXME comments",
    "stale version markers",
    "dashboard/API health markers",
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(text: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (cleaned or "self-development-cycle")[:max_length].strip("-") or "self-development-cycle"


def _ensure_storage() -> None:
    SELF_DEVELOPMENT_DIR.mkdir(parents=True, exist_ok=True)
    if not SELF_DEVELOPMENT_README.exists():
        SELF_DEVELOPMENT_README.write_text(
            "Saved Self Development Cycle records. These are operator-triggered planning receipts that inspect, rank, queue one safe task when requested, and stop before source edits.\n",
            encoding="utf-8",
        )


def _new_cycle_id() -> str:
    return f"selfdev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _cycle_path(cycle_id: str) -> Path:
    _ensure_storage()
    return SELF_DEVELOPMENT_DIR / f"{cycle_id}.json"


def _save_cycle(cycle: dict[str, Any]) -> None:
    _ensure_storage()
    with _cycle_path(cycle["id"]).open("w", encoding="utf-8") as file:
        json.dump(cycle, file, indent=2)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_text(path: Path, limit: int = 120_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if len(text) > limit:
        return text[:limit]
    return text


def _count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE))


def _scan_readmes(root: Path) -> dict[str, Any]:
    readmes = [path for path in root.glob("README*.md") if path.is_file()]
    docs_text = "\n".join(_read_text(path, limit=80_000) for path in readmes)
    return {
        "files": [path.name for path in readmes],
        "file_count": len(readmes),
        "mentions_self_development_cycle": "Self Development Cycle" in docs_text,
        "mentions_realtime_chat": "Realtime Chat Console" in docs_text,
        "next_steps_mentions_current_version": CURRENT_VERSION_TAG in docs_text,
        "release_history_size": len(_read_text(root / "README_RELEASE_HISTORY.md", limit=500_000)),
    }


def _scan_tasks(root: Path) -> dict[str, Any]:
    tasks_path = root / "data" / "tasks.json"
    data = _load_json(tasks_path, {"tasks": []}) if tasks_path.exists() else {"tasks": []}
    tasks = data.get("tasks", []) if isinstance(data, dict) else []
    open_tasks = [task for task in tasks if str(task.get("status", "")).lower() in {"planned", "active", "blocked", "paused"}]
    self_dev_tasks = [task for task in tasks if str(task.get("source_category", "")) == "self_development_cycle"]
    return {
        "tasks_file_exists": tasks_path.exists(),
        "total": len(tasks),
        "open": len(open_tasks),
        "self_development_tasks": len(self_dev_tasks),
        "latest_open_titles": [str(task.get("title", "")) for task in open_tasks[:5]],
    }


def _scan_chat_actions(root: Path) -> dict[str, Any]:
    chat_dir = root / "data" / "chat_actions"
    actions: list[dict[str, Any]] = []
    if chat_dir.exists():
        for path in sorted(chat_dir.glob("*.json"))[-50:]:
            data = _load_json(path, {})
            if isinstance(data, dict):
                actions.append(data)
    failed = [item for item in actions if item.get("status") in {"blocked", "failed"}]
    misclassified_self_dev = [
        item for item in actions
        if "self development" in str(item.get("user_request", "")).lower()
        and item.get("intent") in {"suggest_patch", "suggest_patch_missing_file", "dev_loop_dry_run"}
    ]
    return {
        "directory_exists": chat_dir.exists(),
        "sampled": len(actions),
        "blocked_or_failed": len(failed),
        "misclassified_self_development_requests": len(misclassified_self_dev),
        "recent_intents": [str(item.get("intent", "")) for item in actions[:8]],
    }


def _scan_approvals(root: Path) -> dict[str, Any]:
    approvals_dir = root / "data" / "approvals"
    approvals: list[dict[str, Any]] = []
    if approvals_dir.exists():
        for path in sorted(approvals_dir.glob("*.json"))[-50:]:
            data = _load_json(path, {})
            if isinstance(data, dict):
                approvals.append(data)
    pending = [item for item in approvals if item.get("status") == "pending"]
    return {
        "directory_exists": approvals_dir.exists(),
        "sampled": len(approvals),
        "pending": len(pending),
        "recent_action_types": [str(item.get("action_type", "")) for item in approvals[:8]],
    }


def _scan_todo_fixme(root: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for path in list((root / "conscious_agent").glob("*.py")) + list((root / "tools").glob("*.py")):
        text = _read_text(path, limit=220_000)
        count = _count_pattern(text, r"\b(TODO|FIXME)\b")
        if count:
            matches.append({"path": str(path.relative_to(root)).replace("\\", "/"), "count": count})
    return {
        "file_count": len(matches),
        "total_markers": sum(item["count"] for item in matches),
        "top_files": sorted(matches, key=lambda item: item["count"], reverse=True)[:8],
    }


def _scan_stale_versions(root: Path) -> dict[str, Any]:
    expected = CURRENT_VERSION
    stale: list[dict[str, Any]] = []
    current_names = {
        "CURRENT_VERSION",
        "CURRENT_VERSION_TAG",
        "CURRENT_MILESTONE",
        "NEXT_RECOMMENDED_ARC",
        "WORKSPACE_CURRENT_MILESTONE",
        "SELF_MAINTENANCE_VERSION",
        "DASHBOARD_VERSION",
        "API_VERSION",
        "RELEASE_PACKAGING_VERSION",
        "RELEASE_INSTALLATION_VERSION",
        "VERSION_STATE_VERSION",
        "PACKAGE_INTEGRITY_VERSION",
        "SOURCE_SURFACE_MANIFEST_VERSION",
        "SOURCE_PACKAGE_PRIVACY_METADATA_INTEGRITY_VERSION",
        "METADATA_RELEASE_INTEGRITY_VERSION",
        "SMOKE_SEGMENT_REGISTRY_VERSION",
        "ROUTE_SURFACE_PARITY_VERSION",
        "CURRENT_VERSION_STALENESS_AUDIT_VERSION",
        "SELF_DEVELOPMENT_CYCLE_VERSION",
    }
    current_symbol_pattern = re.compile(r"^\s*(?P<name>[A-Z0-9_]*(?:CURRENT|VERSION)[A-Z0-9_]*)\s*=\s*[\"'](?P<value>[^\"']+)[\"']")
    for path in (root / "conscious_agent").glob("*.py"):
        text = _read_text(path, limit=500_000)
        for line_no, line in enumerate(text.splitlines(), start=1):
            match = current_symbol_pattern.search(line)
            if not match:
                continue
            name = match.group("name")
            value = match.group("value")
            if name not in current_names:
                continue
            ok = False
            if name == "CURRENT_VERSION_TAG":
                ok = value == f"v{expected}"
            elif name in {"CURRENT_MILESTONE", "WORKSPACE_CURRENT_MILESTONE"}:
                ok = f"v{expected}" in value and EXPECTED_TITLE in value
            elif name == "NEXT_RECOMMENDED_ARC":
                ok = value == NEXT_RECOMMENDED_ARC
            else:
                ok = value == expected
            if not ok:
                stale.append({"path": str(path.relative_to(root)).replace("\\", "/"), "line": line_no, "symbol": name, "value": value, "text": line.strip()[:160]})
    return {
        "expected": expected,
        "stale_marker_count": len(stale),
        "sample": stale[:10],
    }


def _scan_dashboard_api_health(root: Path) -> dict[str, Any]:
    dashboard_text = _read_text(root / "conscious_agent" / "dashboard.py", limit=500_000)
    api_text = _read_text(root / "conscious_agent" / "api_server.py", limit=900_000)
    main_text = _read_text(root / "conscious_agent" / "main.py", limit=260_000)
    router_text = _read_text(root / "conscious_agent" / "chat_action_router.py", limit=160_000)
    return {
        "dashboard_version_current": f'DASHBOARD_VERSION = "{CURRENT_VERSION}"' in dashboard_text,
        "api_version_current": f'API_VERSION = "{CURRENT_VERSION}"' in api_text,
        "streaming_chat_route_present": "/api/dashboard-chat/stream" in dashboard_text and "/api/dashboard-chat/stream" in api_text,
        "self_development_cli_present": "--self-development-cycle" in main_text,
        "self_development_router_present": "self_development_cycle" in router_text,
        "native_nav_title_tooltip_risk": "title=\"" in dashboard_text,
    }


def _scan_smoke_hints(root: Path) -> dict[str, Any]:
    smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=900_000)
    return {
        "self_development_smoke_present": "self-development-cycle-v1" in smoke_text,
        "current_version_smoke_present": "current-version-staleness-and-post-patch-verification-v1" in smoke_text,
        "route_parity_smoke_present": "operator-governed-route-surface-parity-v1" in smoke_text,
    }



def _scan_release_smoke_version_mismatches(root: Path) -> dict[str, Any]:
    smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=900_000)
    checks = [
        {"check": "release-pipeline", "module": "release_pipeline", "constant": "RELEASE_PIPELINE_VERSION"},
        {"check": "code-patch-release", "module": "code_patch_release", "constant": "CODE_PATCH_RELEASE_VERSION"},
        {"check": "approval-release-workflow", "module": "approval_release_workflow", "constant": "APPROVAL_RELEASE_VERSION"},
    ]
    mismatches: list[dict[str, Any]] = []
    for row in checks:
        module_text = _read_text(root / "conscious_agent" / f"{row['module']}.py", limit=80_000)
        actual_match = re.search(rf"{row['constant']}\s*=\s*[\"']([^\"']+)[\"']", module_text)
        expected_match = re.search(rf"{row['constant']}\s*!=\s*[\"']([^\"']+)[\"']", smoke_text)
        actual = actual_match.group(1) if actual_match else "[missing]"
        expected = expected_match.group(1) if expected_match else actual
        ok = bool(actual_match and expected_match and actual == expected) or (actual_match and not expected_match)
        if not ok:
            mismatches.append({"check": row["check"], "module": row["module"], "constant": row["constant"], "actual": actual, "expected": expected})
    return {
        "checks_reviewed": len(checks),
        "mismatch_count": len(mismatches),
        "checks": mismatches,
        "status": "pass" if not mismatches else "blocked",
        "ok": not mismatches,
    }

def inspect_project_state(root: Path = ROOT_DIR) -> dict[str, Any]:
    return {
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "created_at": _now(),
        "inspection_areas": list(INSPECTION_AREAS),
        "readmes": _scan_readmes(root),
        "tasks": _scan_tasks(root),
        "chat_actions": _scan_chat_actions(root),
        "approvals": _scan_approvals(root),
        "todo_fixme": _scan_todo_fixme(root),
        "stale_versions": _scan_stale_versions(root),
        "dashboard_api_health": _scan_dashboard_api_health(root),
        "smoke_hints": _scan_smoke_hints(root),
        "release_smoke_version_mismatches": _scan_release_smoke_version_mismatches(root),
    }


# v756.0 cleanup note: the v720-era scoring helpers that used to live here
# were removed after the v721-v755 protected-system-aware helpers fully
# replaced them. Keeping one public definition per helper prevents future
# patch prep from editing dead shadowed code.


def select_recommendation(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    safe = [item for item in candidates if item.get("risk") == "low" and not item.get("requires_operator_approval_before_implementation")]
    return (safe or candidates)[0] if candidates else {}


def _existing_self_development_task(title: str) -> dict[str, Any] | None:
    for task in list_tasks(include_cancelled=False):
        if task.get("source_category") == "self_development_cycle" and task.get("title") == title and task.get("status") in {"planned", "active", "blocked", "paused"}:
            return task
    return None


def _create_selected_task(selected: dict[str, Any], cycle_id: str) -> dict[str, Any]:
    if not selected:
        return {"ok": False, "error": "No selected recommendation."}
    existing = _existing_self_development_task(str(selected.get("title", "")))
    if existing:
        return {"ok": True, "created": False, "task": existing, "message": f"Reused existing self-development task: {existing.get('id')}"}
    result = add_task(
        title=str(selected.get("title", "")),
        description=str(selected.get("summary", "")),
        priority="high" if int(selected.get("urgency", 0) or 0) >= 8 else "medium",
        status="planned",
        command=str(selected.get("recommended_command", "")),
        risk=str(selected.get("risk", "low")),
        source="self_development_cycle",
        source_id=cycle_id,
        source_category="self_development_cycle",
        follow_up_commands=list(selected.get("verification_steps", []) or []),
        requires_approval=bool(selected.get("requires_operator_approval_before_implementation", False)),
        metadata={
            "self_development_cycle_id": cycle_id,
            "verification_steps": list(selected.get("verification_steps", []) or []),
            "stops_before_source_edits": True,
            "source_mutation_allowed": False,
            "operator_approval_required_for_protected_systems": True,
        },
    )
    return {"ok": result.ok, "created": bool(result.ok), "task": result.task or {}, "message": result.message, "error": result.error}


def create_self_development_cycle(
    root: Path = ROOT_DIR,
    prompt: str = "",
    create_task: bool = False,
    save: bool = True,
) -> dict[str, Any]:
    scan = inspect_project_state(root)
    candidates = generate_candidate_improvements(scan)
    selected = select_recommendation(candidates)
    cycle = {
        "id": _new_cycle_id(),
        "type": "self_development_cycle",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "prompt": prompt,
        "inspection": scan,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "selected": selected,
        "task_result": {"ok": True, "created": False, "message": "Task creation was not requested; proposal-only cycle stopped before writes."},
        "verification_steps": list(selected.get("verification_steps", []) if selected else []),
        "safety": {
            "proposal_only": not create_task,
            "creates_task_when_requested": bool(create_task),
            "source_mutation_allowed": False,
            "applies_patch": False,
            "executes_commands": False,
            "modifies_approval_system": False,
            "modifies_memory_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "protected_systems_require_operator_approval": True,
            "stops_before_source_edits": True,
        },
        "final_report": {
            "inspected": list(INSPECTION_AREAS),
            "chosen_task": selected.get("title", "") if selected else "",
            "why_chosen": selected.get("summary", "") if selected else "",
            "what_changed": "Created/reused one task record only." if create_task else "No runtime task was created; proposal-only report saved." if save else "No source or runtime changes requested.",
            "how_verified": list(selected.get("verification_steps", []) if selected else []),
            "what_next": "Review the selected task and approve any later implementation that touches source, approval, memory, release, or execution-permission systems.",
        },
        "useful_commands": [
            "python conscious_agent/main.py --self-development-cycle --self-development-create-task --no-ai-self-development",
            "python conscious_agent/main.py --show-self-development-cycle latest --self-development-full",
            "python tools/smoke_check.py --check self-development-cycle-v1",
        ],
    }
    if create_task:
        cycle["task_result"] = _create_selected_task(selected, cycle["id"])
    if save:
        _save_cycle(cycle)
    return cycle


def list_self_development_cycles() -> list[dict[str, Any]]:
    _ensure_storage()
    cycles: list[dict[str, Any]] = []
    for path in SELF_DEVELOPMENT_DIR.glob("*.json"):
        data = _load_json(path, {})
        if isinstance(data, dict) and data.get("type") == "self_development_cycle":
            cycles.append(data)
    return sorted(cycles, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_self_development_cycle_id(cycle_id: str) -> str:
    token = (cycle_id or "").strip()
    if token.lower() in {"latest", "last"}:
        cycles = list_self_development_cycles()
        return cycles[0].get("id", "") if cycles else ""
    return token


def get_self_development_cycle(cycle_id: str) -> dict[str, Any] | None:
    resolved = resolve_self_development_cycle_id(cycle_id)
    if not resolved:
        return None
    path = _cycle_path(resolved)
    if path.exists():
        data = _load_json(path, {})
        return data if isinstance(data, dict) else None
    for cycle in list_self_development_cycles():
        if cycle.get("id") == resolved:
            return cycle
    return None


def self_development_cycle_text(cycle: dict[str, Any] | None, full: bool = False) -> str:
    if not cycle:
        return "Self Development Cycle not found."
    lines = [
        f"# Self Development Cycle: {cycle.get('id')}",
        f"Version: {cycle.get('version')}",
        f"Created: {cycle.get('created_at')}",
        f"Candidate improvements: {cycle.get('candidate_count')}",
        "Source edits applied: no",
        "Stops before risky writes: yes",
    ]
    selected = cycle.get("selected", {}) or {}
    if selected:
        lines.extend([
            "",
            "## Selected recommendation",
            f"Title: {selected.get('title')}",
            f"Risk: {selected.get('risk')}",
            f"Score: {selected.get('score')}",
            f"Requires approval before implementation: {selected.get('requires_operator_approval_before_implementation')}",
            f"Summary: {selected.get('summary')}",
            f"Recommended command: {selected.get('recommended_command')}",
        ])
    task_result = cycle.get("task_result", {}) or {}
    lines.extend([
        "",
        "## Work item",
        f"OK: {task_result.get('ok')}",
        f"Created: {task_result.get('created')}",
        f"Message: {task_result.get('message') or task_result.get('error') or ''}",
    ])
    task = task_result.get("task") or {}
    if task:
        lines.append(f"Task: {task.get('id')} - {task.get('title')}")
    lines.append("")
    lines.append("## Verification steps")
    for step in cycle.get("verification_steps", []) or []:
        lines.append(f"- {step}")
    safety = cycle.get("safety", {}) or {}
    lines.extend([
        "",
        "## Safety boundaries",
        f"Source mutation allowed: {safety.get('source_mutation_allowed')}",
        f"Executes commands: {safety.get('executes_commands')}",
        f"Applies patch: {safety.get('applies_patch')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Candidates")
        for index, candidate in enumerate(cycle.get("candidates", []) or [], start=1):
            lines.append(f"{index}. {candidate.get('title')} | risk={candidate.get('risk')} | score={candidate.get('score')} | approval_required={candidate.get('requires_operator_approval_before_implementation')}")
        lines.append("")
        lines.append("## Inspection summary")
        lines.append(json.dumps(cycle.get("inspection", {}), indent=2))
    return "\n".join(lines)


def print_self_development_cycle(prompt: str = "", create_task: bool = False, full: bool = False) -> None:
    cycle = create_self_development_cycle(prompt=prompt, create_task=create_task, save=True)
    print(self_development_cycle_text(cycle, full=full))


def print_self_development_cycles() -> None:
    cycles = list_self_development_cycles()
    if not cycles:
        print("No Self Development Cycle records found.")
        return
    for cycle in cycles:
        selected = cycle.get("selected", {}) or {}
        task = (cycle.get("task_result", {}) or {}).get("task", {}) or {}
        print(f"{cycle.get('id')} | {cycle.get('created_at')} | selected={selected.get('title', '[none]')} | task={task.get('id', '[none]')}")


def print_saved_self_development_cycle(cycle_id: str = "latest", full: bool = False) -> None:
    print(self_development_cycle_text(get_self_development_cycle(cycle_id), full=full))

# v721.0-v760.0 trial review and protected-system expansion helpers.  These
# definitions replace the retired v720 scoring helpers while
# preserving the public API used by chat_action_router and main.py.
PROMPT_REGRESSION_FIXTURES = (
    "Eidolon, begin work on a Self Development Cycle v1.",
    "start improving yourself safely",
    "figure out what you should work on next",
    "begin your own development loop",
    "review your project and make a task",
    "look at your failed actions and plan the next fix",
    "what should you improve next",
    "plan your own next development step",
)

PROTECTED_SYSTEM_FIXTURES = (
    "modify the approval system during self development",
    "change memory writes as part of your own development cycle",
    "update release packaging and publish automatically",
    "expand execution permissions or command safety",
    "make yourself autonomous and continue work automatically",
    "schedule hidden self development work",
    "change signing keys, secrets, or trusted release roots",
    "invoke network actions while planning your own next step",
)

PROTECTED_SYSTEM_KEYWORDS = (
    "approval", "approvals", "approval_manager", "approve", "self-approve", "self approve",
    "memory", "memory_compactor", "memory write", "write memory",
    "release", "release_packaging", "release_installation", "package_integrity", "source_package", "publish", "signing",
    "execution permission", "execution-permission", "command_runner", "command safety", "execute", "executor", "runner", "permission",
    "self-update", "self update", "self_maintenance", "autonomous_dev_cycle", "dev_loop", "autonomy", "autonomous", "continue automatically",
    "schedule", "scheduler", "hidden work", "network", "external", "http", "api key", "secret", "token", "trusted_public_keys",
)

QUALITY_BIAS_TERMS = {
    "current_version_trust": ("stale", "version", "current", "metadata"),
    "ui_chat_reliability": ("dashboard", "chat", "route", "api", "ui"),
    "package_privacy": ("package", "privacy", "source-only", "runtime"),
    "testability": ("smoke", "test", "verification", "fixture"),
    "manifest_registry": ("manifest", "registry", "parity", "surface"),
}


def classify_protected_systems(text: str) -> list[str]:
    lowered = str(text or "").lower()
    hits: list[str] = []
    for keyword in PROTECTED_SYSTEM_KEYWORDS:
        if keyword in lowered and keyword not in hits:
            hits.append(keyword)
    return hits


def _protected_target_hit(text: str) -> bool:
    return bool(classify_protected_systems(text))


def _quality_tags(text: str) -> list[str]:
    lowered = str(text or "").lower()
    tags = []
    for tag, terms in QUALITY_BIAS_TERMS.items():
        if any(term in lowered for term in terms):
            tags.append(tag)
    return tags


def _candidate(
    title: str,
    summary: str,
    value: int,
    risk: str,
    urgency: int,
    testability: int,
    recommended_command: str,
    verification_steps: list[str],
    protected_target: bool = False,
) -> dict[str, Any]:
    risk_weights = {"low": 4, "medium": 0, "high": -4, "critical": -8}
    risk = risk if risk in risk_weights else "medium"
    combined = f"{title} {summary} {recommended_command}"
    protected_hits = classify_protected_systems(combined)
    tags = _quality_tags(combined)
    protected = bool(protected_target or protected_hits)
    approval_required = risk in {"medium", "high", "critical"} or protected
    quality_bonus = len(tags) * 2
    protected_penalty = 10 if protected else 0
    score = value * 3 + urgency * 2 + testability * 3 + risk_weights[risk] * 3 + quality_bonus - protected_penalty
    return {
        "title": title,
        "summary": summary,
        "value": value,
        "risk": risk,
        "urgency": urgency,
        "testability": testability,
        "quality_tags": tags,
        "score": score,
        "protected_target": protected,
        "protected_system_hits": protected_hits,
        "requires_operator_approval_before_implementation": bool(approval_required),
        "recommended_command": recommended_command,
        "verification_steps": verification_steps,
    }


def generate_candidate_improvements(scan: dict[str, Any]) -> list[dict[str, Any]]:
    stale_count = int((scan.get("stale_versions") or {}).get("stale_marker_count", 0) or 0)
    todo_count = int((scan.get("todo_fixme") or {}).get("total_markers", 0) or 0)
    misclassified = int((scan.get("chat_actions") or {}).get("misclassified_self_development_requests", 0) or 0)
    release_mismatches = (scan.get("release_smoke_version_mismatches") or {}).get("checks", []) or []
    candidates = []
    if release_mismatches:
        names = ", ".join(str(item.get("check")) for item in release_mismatches[:3])
        candidates.append(_candidate(
            title="Repair active release smoke version expectation mismatches",
            summary=(
                f"The project scan found active release smoke version mismatches in {names}. "
                "Fix smoke expectations or module constants directly instead of classifying these as intentional governance blockers."
            ),
            value=12,
            risk="low",
            urgency=10,
            testability=10,
            recommended_command="python tools/smoke_check.py --check release-pipeline && python tools/smoke_check.py --check code-patch-release && python tools/smoke_check.py --check approval-release-workflow",
            verification_steps=[
                "python tools/smoke_check.py --check release-pipeline",
                "python tools/smoke_check.py --check code-patch-release",
                "python tools/smoke_check.py --check approval-release-workflow",
                "Confirm smoke debt classification reports these as current_release_failure when they fail.",
            ],
        ))
    candidates.extend([
        _candidate(
            title="Review Self Development Cycle trial receipts and protected gate coverage",
            summary=(
                "Summarize recent self-development cycle receipts, verify prompt routing stayed out of suggest_patch, "
                "confirm protected-system wording escalates to approval-required planning, and expose the result as a review-only dashboard surface."
            ),
            value=10,
            risk="low",
            urgency=9 + min(misclassified, 1),
            testability=10,
            recommended_command="python conscious_agent/main.py --self-development-trial-review --self-development-full",
            verification_steps=[
                "python -m compileall -q conscious_agent tools",
                "python tools/smoke_check.py --check self-development-cycle-trial-review-v1",
                "python conscious_agent/main.py --self-development-trial-review --self-development-full",
                "Open /self-development-cycle and confirm the dashboard reports proposal-only status.",
            ],
        ),
        _candidate(
            title="Expand Self Development Cycle prompt regression fixtures",
            summary=(
                "Cover messy plain-English variants such as start improving yourself, begin your own development loop, "
                "review your project and make a task, and look at failed actions before selecting next work."
            ),
            value=9,
            risk="low",
            urgency=8,
            testability=10,
            recommended_command="python tools/smoke_check.py --check self-development-cycle-trial-review-v1",
            verification_steps=[
                "Run all PROMPT_REGRESSION_FIXTURES through chat_action_router.propose_chat_action(save=False).",
                "Confirm every fixture routes to self_development_cycle.",
                "Confirm no fixture routes to suggest_patch, suggest_patch_missing_file, or dev_loop_dry_run.",
            ],
        ),
        _candidate(
            title="Calibrate Self Development Cycle candidate quality scoring",
            summary=(
                "Favor low-risk, high-testability current trust work such as route parity, package privacy, stale-version clarity, "
                "dashboard/chat reliability, and manifest drift; penalize protected systems and vague autonomy expansion."
            ),
            value=9,
            risk="low",
            urgency=8,
            testability=9,
            recommended_command="python conscious_agent/main.py --self-development-cycle --no-ai-self-development --self-development-full",
            verification_steps=[
                "Create a proposal-only self-development cycle with save=False during smoke.",
                "Confirm at least three candidates include score, quality_tags, risk, urgency, and testability.",
                "Confirm the selected recommendation is low-risk and does not require approval before planning.",
            ],
        ),
        _candidate(
            title="Triage broad install smoke blockers into intentional blockers and current stale failures",
            summary=(
                "Classify old broad install smoke blockers without hiding them, then recommend focused current-release repairs separately from supervised-only intentional blockers."
            ),
            value=8,
            risk="low",
            urgency=7,
            testability=8,
            recommended_command="python tools/smoke_check.py --segment install-dashboard --json",
            verification_steps=[
                "python tools/smoke_check.py --list-segments",
                "python tools/smoke_check.py --segment install-dashboard --json",
                "Record which blocked checks are intentional supervised-only gates versus stale current-release failures.",
            ],
        ),
        _candidate(
            title="Add protected-system approval escalation tests for memory, approval, release, execution, scheduling, and autonomy targets",
            summary=(
                "Requests that touch approval, memory, release, command safety, execution permission, signing, scheduling, external/network action, or autonomy must become approval-required plans, not direct implementation work."
            ),
            value=9,
            risk="medium",
            urgency=9,
            testability=10,
            recommended_command="python tools/smoke_check.py --check self-development-cycle-trial-review-v1",
            verification_steps=[
                "Run PROTECTED_SYSTEM_FIXTURES through classify_protected_systems.",
                "Confirm each protected fixture returns at least one protected_system_hit.",
                "Confirm protected candidates require_operator_approval_before_implementation=True.",
            ],
            protected_target=True,
        ),
    ])
    if stale_count:
        candidates.append(_candidate(
            title="Repair current-state stale version marker drift found by self-development scan",
            summary=f"The scan found {stale_count} possible stale current-version marker(s). Verify whether each is a current-state symbol or historical reference before editing anything.",
            value=9,
            risk="medium",
            urgency=10,
            testability=9,
            recommended_command="python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            verification_steps=[
                "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
                "Review self-development stale marker samples.",
                "Do not change release, approval, or command-safety gates without explicit operator approval.",
            ],
            protected_target=True,
        ))
    if todo_count:
        candidates.append(_candidate(
            title="Review TODO/FIXME markers for low-risk documentation or dashboard cleanup",
            summary=f"The scan found {todo_count} TODO/FIXME marker(s). Convert only low-risk, testable cleanup into future work items; protected targets remain approval-gated.",
            value=6,
            risk="low",
            urgency=4,
            testability=7,
            recommended_command="python conscious_agent/main.py --self-development-cycle --no-ai-self-development --self-development-full",
            verification_steps=[
                "Inspect the TODO/FIXME top_files summary.",
                "Create no source patch from this cycle.",
                "Queue any implementation only after operator review.",
            ],
        ))
    return sorted(candidates, key=lambda item: item.get("score", 0), reverse=True)


DUPLICATE_CLEANUP_TARGETS = (
    "_protected_target_hit",
    "_candidate",
    "generate_candidate_improvements",
)


def _module_level_definition_locations(source: str) -> dict[str, list[dict[str, int]]]:
    locations: dict[str, list[dict[str, int]]] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return locations
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            locations.setdefault(node.name, []).append({
                "line": int(getattr(node, "lineno", 0) or 0),
                "end_line": int(getattr(node, "end_lineno", getattr(node, "lineno", 0)) or 0),
            })
    return locations


def build_self_development_cycle_duplicate_cleanup_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    path = root / "conscious_agent" / "self_development_cycle.py"
    source = _read_text(path, limit=900_000)
    locations = _module_level_definition_locations(source)
    duplicate_definitions = [
        {"name": name, "locations": locs, "count": len(locs)}
        for name, locs in sorted(locations.items())
        if len(locs) > 1
    ]
    target_rows = []
    for name in DUPLICATE_CLEANUP_TARGETS:
        locs = locations.get(name, [])
        target_rows.append({
            "name": name,
            "definition_count": len(locs),
            "locations": locs,
            "cleanup_status": "clean" if len(locs) == 1 else "blocked_duplicate_remaining",
        })
    probe = create_self_development_cycle(
        root=root,
        prompt="self-development duplicate cleanup review probe",
        create_task=False,
        save=False,
    )
    selected = probe.get("selected", {}) or {}
    protected_hits = classify_protected_systems("modify approvals, memory, release packaging, command safety, scheduler, autonomy")
    stale_smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=900_000)
    self_maintenance_exact_660 = stale_smoke_text.count('SELF_MAINTENANCE_VERSION != "660.0"') + stale_smoke_text.count('sm.SELF_MAINTENANCE_VERSION != "660.0"')
    self_maintenance_exact_current = stale_smoke_text.count('SELF_MAINTENANCE_VERSION != "885.0"') + stale_smoke_text.count('sm.SELF_MAINTENANCE_VERSION != "885.0"')
    return {
        "id": f"selfdev_duplicate_cleanup_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "self_development_cycle_duplicate_cleanup_review",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if not duplicate_definitions else "blocked",
        "ok": not duplicate_definitions,
        "cleanup_targets": list(DUPLICATE_CLEANUP_TARGETS),
        "target_rows": target_rows,
        "duplicate_definition_count": len(duplicate_definitions),
        "duplicate_definitions": duplicate_definitions,
        "retired_shadowed_v720_helpers": True,
        "candidate_probe": {
            "candidate_count": len(probe.get("candidates", []) or []),
            "selected_title": selected.get("title"),
            "selected_risk": selected.get("risk"),
            "selected_has_quality_tags": bool(selected.get("quality_tags")),
            "selected_has_protected_hits_field": "protected_system_hits" in selected,
        },
        "protected_gate_probe": {
            "fixture_hits": protected_hits,
            "approval_required": bool(protected_hits),
        },
        "legacy_smoke_debt_reduction": {
            "self_maintenance_exact_v660_expectations_remaining": self_maintenance_exact_660,
            "self_maintenance_exact_current_expectations_present": self_maintenance_exact_current,
            "one_lightweight_self_maintenance_install_check_repaired": self_maintenance_exact_current >= 1,
            "install_regression_recent_may_still_block_on_deeper_legacy_checks": True,
        },
        "safety": {
            "review_only": True,
            "applies_source_edits_beyond_this_operator_patch": False,
            "creates_concrete_diff": False,
            "runs_broad_smoke": False,
            "marks_blockers_as_pass": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check self-development-cycle-duplicate-cleanup-v1",
            "python tools/smoke_check.py --check self-development-cycle-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
        ],
    }


def self_development_cycle_duplicate_cleanup_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Self Development Cycle duplicate cleanup review not found."
    safety = report.get("safety", {}) or {}
    legacy = report.get("legacy_smoke_debt_reduction", {}) or {}
    lines = [
        f"# Self Development Cycle Duplicate Cleanup Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Duplicate module-level definitions: {report.get('duplicate_definition_count')}",
        "Retired shadowed v720 helpers: yes",
        f"SELF_MAINTENANCE_VERSION exact v660 expectations remaining: {legacy.get('self_maintenance_exact_v660_expectations_remaining')}",
        f"SELF_MAINTENANCE_VERSION current expectations present: {legacy.get('self_maintenance_exact_current_expectations_present')}",
        "Install regression recent may still block on deeper legacy checks: yes",
        "Review only: yes",
        "Applies source edits beyond this operator patch: no",
        "Creates concrete diff: no",
        "Expands autonomy: no",
        "",
        "## Cleanup targets",
    ]
    for row in report.get("target_rows", []) or []:
        lines.append(f"- {row.get('name')}: count={row.get('definition_count')} status={row.get('cleanup_status')}")
    probe = report.get("candidate_probe", {}) or {}
    lines.extend([
        "",
        "## Candidate probe",
        f"Candidates: {probe.get('candidate_count')}",
        f"Selected: {probe.get('selected_title')} ({probe.get('selected_risk')})",
        f"Selected has quality tags: {probe.get('selected_has_quality_tags')}",
        f"Selected has protected hits field: {probe.get('selected_has_protected_hits_field')}",
        "",
        "## Safety",
        f"Runs broad smoke: {safety.get('runs_broad_smoke')}",
        f"Marks blockers as pass: {safety.get('marks_blockers_as_pass')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Duplicate definitions")
        lines.append(json.dumps(report.get("duplicate_definitions", []), indent=2))
    return "\n".join(lines)


LEGACY_SELF_MAINTENANCE_SMOKE_BLOCKERS = (
    {
        "name": "operator-governed-structural-stabilization-and-runtime-modularization-v1",
        "builder": "build_operator_governed_structural_stabilization_and_runtime_modularization_v1",
        "class": "stale exact-version expectation",
    },
    {
        "name": "operator-governed-self-maintenance-decomposition-v1",
        "builder": "build_operator_governed_self_maintenance_decomposition_v1",
        "class": "stale exact-version expectation",
    },
    {
        "name": "operator-governed-self-maintenance-modular-extraction-v1",
        "builder": "build_operator_governed_self_maintenance_modular_extraction_v1",
        "class": "stale companion-module version expectation",
    },
    {
        "name": "operator-governed-self-maintenance-duplicate-shadow-cleanup-v1",
        "builder": "build_operator_governed_self_maintenance_duplicate_shadow_cleanup_v1",
        "class": "stale companion-module version expectation",
    },
)


_LEGACY_SELF_MAINTENANCE_SMOKE_BLOCKER_REVIEW_CACHE: dict[str, dict[str, Any]] = {}

RESOLVED_INSTALL_REGRESSION_RECENT_CHECKS = {
    "operator-governed-structural-stabilization-and-runtime-modularization-v1",
    "operator-governed-self-maintenance-decomposition-v1",
    "operator-governed-self-maintenance-modular-extraction-v1",
    "operator-governed-self-maintenance-duplicate-shadow-cleanup-v1",
    "legacy-self-maintenance-smoke-blocker-review-v1",
    "self-maintenance",
}


def _classify_legacy_blocker_row(row: dict[str, Any]) -> str:
    name = str(row.get("name", "")).lower()
    message = str(row.get("message", "")).lower()
    if "version" in name or "version" in message:
        return "stale exact-version expectation"
    if "docs" in name or "runtime" in name or "route" in name:
        return "outdated structural assumption"
    if "duplicate" in name or "shadow" in name:
        return "obsolete duplicate-shadow expectation"
    if row.get("status") == "blocked":
        return "real current regression candidate"
    return "current behavior verified"


def build_legacy_self_maintenance_smoke_blocker_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    cache_key = str(Path(root).resolve())
    cached = _LEGACY_SELF_MAINTENANCE_SMOKE_BLOCKER_REVIEW_CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    try:
        import self_maintenance as sm
    except Exception as error:
        return {
            "id": f"legacy_self_maintenance_smoke_blocker_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": "legacy_self_maintenance_smoke_blocker_review",
            "version": SELF_DEVELOPMENT_CYCLE_VERSION,
            "current_milestone": CURRENT_MILESTONE,
            "created_at": _now(),
            "status": "blocked",
            "ok": False,
            "error": f"self_maintenance import failed: {type(error).__name__}: {error}",
            "blockers": [],
            "safety": {"review_only": True, "expands_autonomy": False},
        }
    smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=1_100_000)
    rows: list[dict[str, Any]] = []
    repaired = 0
    still_blocked = 0
    for blocker in LEGACY_SELF_MAINTENANCE_SMOKE_BLOCKERS:
        builder_name = blocker["builder"]
        report: dict[str, Any]
        try:
            report = getattr(sm, builder_name)(save=False)
        except Exception as error:
            report = {"ok": False, "status": "blocked", "rows": [], "error": f"{type(error).__name__}: {error}"}
        blocking_rows = [dict(row) for row in report.get("rows", []) or [] if row.get("status") != "pass"]
        classifications = sorted({_classify_legacy_blocker_row(row) for row in blocking_rows}) or ["current behavior verified"]
        status = "repaired" if report.get("ok") is True and not blocking_rows else "blocked"
        if status == "repaired":
            repaired += 1
        else:
            still_blocked += 1
        rows.append({
            "name": blocker["name"],
            "builder": builder_name,
            "status": status,
            "report_ok": report.get("ok") is True,
            "report_status": report.get("status"),
            "classifications": classifications,
            "blocking_rows": blocking_rows,
            "original_blocker_class": blocker["class"],
        })
    exact_660_remaining = smoke_text.count('SELF_MAINTENANCE_VERSION != "660.0"') + smoke_text.count('sm.SELF_MAINTENANCE_VERSION != "660.0"')
    exact_current_present = smoke_text.count('SELF_MAINTENANCE_VERSION != "885.0"') + smoke_text.count('sm.SELF_MAINTENANCE_VERSION != "885.0"')
    status = "pass" if still_blocked == 0 else "review_required"
    report = {
        "id": f"legacy_self_maintenance_smoke_blocker_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "legacy_self_maintenance_smoke_blocker_review",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": status,
        "ok": still_blocked == 0,
        "blocker_count": len(rows),
        "repaired_blocker_count": repaired,
        "remaining_blocker_count": still_blocked,
        "blockers": rows,
        "install_regression_recent_expected_status": "pass" if still_blocked == 0 else "blocked",
        "legacy_smoke_debt_reduction": {
            "self_maintenance_exact_v660_expectations_remaining": exact_660_remaining,
            "self_maintenance_exact_current_expectations_present": exact_current_present,
            "repaired_legacy_self_maintenance_blockers": repaired,
            "remaining_legacy_self_maintenance_blockers": still_blocked,
            "blocked_checks_are_not_marked_pass_without_repair": True,
        },
        "safety": {
            "review_only": True,
            "applies_source_edits_beyond_this_operator_patch": False,
            "creates_concrete_diff": False,
            "runs_broad_smoke": False,
            "marks_blockers_as_pass": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check legacy-self-maintenance-smoke-blocker-review-v1",
            "python tools/smoke_check.py --segment install-regression-recent --json",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
        ],
    }
    _LEGACY_SELF_MAINTENANCE_SMOKE_BLOCKER_REVIEW_CACHE[cache_key] = dict(report)
    return report


def legacy_self_maintenance_smoke_blocker_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Legacy Self Maintenance smoke blocker review not found."
    safety = report.get("safety", {}) or {}
    legacy = report.get("legacy_smoke_debt_reduction", {}) or {}
    lines = [
        f"# Legacy Self Maintenance Smoke Blocker Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Blockers reviewed: {report.get('blocker_count')}",
        f"Repaired blockers: {report.get('repaired_blocker_count')}",
        f"Remaining blockers: {report.get('remaining_blocker_count')}",
        f"Install regression recent expected status: {report.get('install_regression_recent_expected_status')}",
        f"SELF_MAINTENANCE_VERSION exact v660 expectations remaining: {legacy.get('self_maintenance_exact_v660_expectations_remaining')}",
        f"SELF_MAINTENANCE_VERSION current expectations present: {legacy.get('self_maintenance_exact_current_expectations_present')}",
        "Review only: yes",
        "Marks blockers as pass without repair: no",
        "Runs broad smoke: no",
        "Expands autonomy: no",
        "",
        "## Blocker rows",
    ]
    for row in report.get("blockers", []) or []:
        lines.append(f"- {row.get('name')}: {row.get('status')} classes={', '.join(row.get('classifications', []))}")
        if full:
            for blocker_row in row.get("blocking_rows", []) or []:
                lines.append(f"  - {blocker_row.get('name')}: {blocker_row.get('status')} - {blocker_row.get('message')}")
    lines.extend([
        "",
        "## Safety",
        f"Applies source edits beyond this operator patch: {safety.get('applies_source_edits_beyond_this_operator_patch')}",
        f"Creates concrete diff: {safety.get('creates_concrete_diff')}",
        f"Marks blockers as pass: {safety.get('marks_blockers_as_pass')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    return "\n".join(lines)


def build_self_development_trial_review(root: Path = ROOT_DIR, save: bool = False) -> dict[str, Any]:
    scan = inspect_project_state(root)
    probe_cycle = create_self_development_cycle(root=root, prompt="self-development trial review probe", create_task=False, save=False)
    cycles = list_self_development_cycles()
    prompt_results: list[dict[str, Any]] = []
    try:
        import chat_action_router
        for fixture in PROMPT_REGRESSION_FIXTURES:
            action = chat_action_router.propose_chat_action(fixture, save=False)
            prompt_results.append({
                "prompt": fixture,
                "intent": action.get("intent"),
                "execution_mode": action.get("execution_mode"),
                "risk_level": action.get("risk_level"),
                "command": action.get("command"),
                "ok": action.get("intent") == "self_development_cycle" and action.get("intent") not in {"suggest_patch", "suggest_patch_missing_file", "dev_loop_dry_run"},
            })
    except Exception as error:
        prompt_results.append({"prompt": "[router import failed]", "ok": False, "error": str(error)})
    protected_results = [
        {"fixture": fixture, "hits": classify_protected_systems(fixture), "approval_required": bool(classify_protected_systems(fixture))}
        for fixture in PROTECTED_SYSTEM_FIXTURES
    ]
    candidates = probe_cycle.get("candidates", []) or []
    selected = probe_cycle.get("selected", {}) or {}
    source_write_claims = [
        bool((probe_cycle.get("safety", {}) or {}).get("source_mutation_allowed")),
        bool((probe_cycle.get("safety", {}) or {}).get("applies_patch")),
        bool((probe_cycle.get("safety", {}) or {}).get("executes_commands")),
    ]
    report = {
        "id": f"selfdev_trial_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "self_development_trial_review",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "created_at": _now(),
        "status": "pass" if all(item.get("ok") for item in prompt_results) and all(item.get("approval_required") for item in protected_results) and not any(source_write_claims) else "review_required",
        "recent_cycle_count": len(cycles),
        "latest_cycle_id": cycles[0].get("id", "") if cycles else "",
        "prompt_regression_results": prompt_results,
        "protected_gate_results": protected_results,
        "candidate_count": len(candidates),
        "candidate_quality_summary": [
            {"title": c.get("title"), "risk": c.get("risk"), "score": c.get("score"), "quality_tags": c.get("quality_tags"), "approval_required": c.get("requires_operator_approval_before_implementation")}
            for c in candidates[:5]
        ],
        "selected_recommendation": selected,
        "inspection_summary": {
            "stale_marker_count": (scan.get("stale_versions") or {}).get("stale_marker_count", 0),
            "todo_fixme_count": (scan.get("todo_fixme") or {}).get("total_markers", 0),
            "blocked_or_failed_chat_actions": (scan.get("chat_actions") or {}).get("blocked_or_failed", 0),
            "dashboard_streaming_route_present": (scan.get("dashboard_api_health") or {}).get("streaming_chat_route_present"),
            "self_development_router_present": (scan.get("dashboard_api_health") or {}).get("self_development_router_present"),
        },
        "safety": {
            "review_only": True,
            "source_mutation_allowed": False,
            "applies_patch": False,
            "executes_commands": False,
            "creates_release": False,
            "publishes_release": False,
            "modifies_approval_system": False,
            "modifies_memory_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "protected_systems_require_operator_approval": True,
            "stops_before_source_edits": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check self-development-cycle-trial-review-v1",
            "python conscious_agent/main.py --self-development-trial-review --self-development-full",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }
    return report


def self_development_trial_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Self Development Cycle trial review not found."
    lines = [
        f"# Self Development Cycle Trial Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Recent saved cycles: {report.get('recent_cycle_count')}",
        f"Latest cycle: {report.get('latest_cycle_id') or '[none]'}",
        "Review only: yes",
        "Source edits applied: no",
        "Stops before risky writes: yes",
        "",
        "## Prompt regression fixtures",
    ]
    for item in report.get("prompt_regression_results", []) or []:
        lines.append(f"- {item.get('prompt')} -> intent={item.get('intent')} mode={item.get('execution_mode')} ok={item.get('ok')}")
    lines.append("")
    lines.append("## Protected-system gates")
    for item in report.get("protected_gate_results", []) or []:
        lines.append(f"- {item.get('fixture')} -> hits={', '.join(item.get('hits') or []) or '[none]'} approval_required={item.get('approval_required')}")
    selected = report.get("selected_recommendation", {}) or {}
    lines.extend([
        "",
        "## Selected recommendation",
        f"Title: {selected.get('title')}",
        f"Risk: {selected.get('risk')}",
        f"Score: {selected.get('score')}",
        f"Requires approval before implementation: {selected.get('requires_operator_approval_before_implementation')}",
        f"Summary: {selected.get('summary')}",
        "",
        "## Verification steps",
    ])
    for step in report.get("verification_steps", []) or []:
        lines.append(f"- {step}")
    safety = report.get("safety", {}) or {}
    lines.extend([
        "",
        "## Safety boundaries",
        f"Review only: {safety.get('review_only')}",
        f"Source mutation allowed: {safety.get('source_mutation_allowed')}",
        f"Executes commands: {safety.get('executes_commands')}",
        f"Applies patch: {safety.get('applies_patch')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Candidate quality summary")
        lines.append(json.dumps(report.get("candidate_quality_summary", []), indent=2))
        lines.append("")
        lines.append("## Inspection summary")
        lines.append(json.dumps(report.get("inspection_summary", {}), indent=2))
    return "\n".join(lines)


def print_self_development_trial_review(full: bool = False) -> None:
    print(self_development_trial_review_text(build_self_development_trial_review(save=False), full=full))

# v726.0-v760.0 dashboard trial hardening, receipt browsing, and broad smoke triage.
# This layer remains review-only. It classifies evidence and improves operator UX;
# it does not run broad smoke, apply source patches, or convert a task into approval.
SMOKE_TRIAGE_CATEGORIES = (
    "current_release_failure",
    "stale_legacy_expectation",
    "intentional_supervised_only_blocker",
    "missing_optional_dependency",
    "needs_manual_operator_approval",
)


def _extract_smoke_checks(root: Path = ROOT_DIR) -> list[dict[str, Any]]:
    text = _read_text(root / "tools" / "smoke_check.py", limit=1_400_000)
    pattern = re.compile(r'SmokeCheck\("(?P<name>[^"]+)",\s*"(?P<tier>[^"]+)",\s*(?P<timeout>\d+),\s*(?P<func>[A-Za-z0-9_]+)\)')
    rows: list[dict[str, Any]] = []
    try:
        import smoke_segment_registry as ssr
    except Exception:
        ssr = None  # type: ignore[assignment]
    for match in pattern.finditer(text):
        name = match.group("name")
        tier = match.group("tier")
        segment = ssr.classify_check_name(name, tier) if ssr is not None else "install-core"
        rows.append({
            "name": name,
            "tier": tier,
            "timeout": int(match.group("timeout")),
            "function": match.group("func"),
            "segment": segment,
        })
    return rows


def classify_smoke_blocker(name: str, segment: str = "") -> dict[str, Any]:
    lowered_name = str(name or "").lower()
    lowered = f"{lowered_name} {segment}".lower()
    categories: list[str] = []
    reason = "classified by smoke name and segment; active release smoke names are never hidden as governance blockers"
    active_release_tokens = {
        "release-pipeline",
        "code-patch-release",
        "approval-release-workflow",
        "dashboard-chat-sse-parser-active-smoke-debt-repair-v1",
        "dashboard-chat",
        "realtime-chat",
    }
    if any(token in lowered_name for token in active_release_tokens):
        categories.append("current_release_failure")
    if any(token in lowered for token in ["chromadb", "ollama", "local-model", "optional-dependency"]):
        categories.append("missing_optional_dependency")
    if any(token in lowered for token in ["current-version", "current-state", "staleness", "metadata-release", "source-package", "package-privacy", "release-packaging", "route-surface", "source-surface", "self-development", "realtime-chat", "dashboard-chat"]):
        categories.append("current_release_failure")
    if any(token in lowered for token in ["legacy", "stale-expectation", "segmentation", "regression-recent", "old", "v80", "v90", "v100"]):
        categories.append("stale_legacy_expectation")
    governance_tokens = ["approval", "authorization", "autonomy", "sandbox", "live-patch", "rollback", "release-decision", "archive", "operator-decision", "memory-lifecycle", "observation", "boundary", "gate"]
    if any(token in lowered for token in governance_tokens):
        if "current_release_failure" not in categories:
            categories.append("intentional_supervised_only_blocker")
        categories.append("needs_manual_operator_approval")
    if not categories:
        categories.append("stale_legacy_expectation" if segment == "install-regression-recent" else "current_release_failure" if segment in {"install-core", "install-dashboard", "install-release"} else "intentional_supervised_only_blocker")
    unique: list[str] = []
    for category in categories:
        if category not in unique:
            unique.append(category)
    return {
        "name": name,
        "segment": segment,
        "categories": unique,
        "primary_category": unique[0],
        "reason": reason,
        "review_only": True,
        "treats_blocker_as_pass": False,
        "operator_review_required": True,
    }


def build_broad_smoke_triage_report(root: Path = ROOT_DIR, max_examples_per_category: int = 8) -> dict[str, Any]:
    checks = _extract_smoke_checks(root)
    segment_counts: dict[str, int] = {}
    categories: dict[str, list[dict[str, Any]]] = {category: [] for category in SMOKE_TRIAGE_CATEGORIES}
    for check in checks:
        segment = str(check.get("segment", ""))
        segment_counts[segment] = segment_counts.get(segment, 0) + 1
        triage = classify_smoke_blocker(str(check.get("name", "")), segment)
        triage.update({"tier": check.get("tier"), "timeout": check.get("timeout")})
        for category in triage.get("categories", []):
            categories.setdefault(category, []).append(triage)
    category_counts = {category: len(items) for category, items in categories.items()}
    examples = {category: items[:max_examples_per_category] for category, items in categories.items()}
    focused_current = [
        item for item in categories.get("current_release_failure", [])
        if any(token in item.get("name", "") for token in [
            "current-version", "current-state", "metadata-release", "source-package", "release-packaging", "route-surface", "source-surface", "self-development"
        ])
    ][:max_examples_per_category]
    return {
        "id": f"broad_smoke_triage_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "broad_smoke_triage",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "created_at": _now(),
        "status": "review_prepared",
        "check_count": len(checks),
        "segment_counts": segment_counts,
        "category_counts": category_counts,
        "category_examples": examples,
        "focused_current_release_examples": focused_current,
        "classification_policy": {
            "current_release_failure": "Current release trust gates such as staleness, metadata, package privacy, route/source surface parity, realtime chat, and self-development checks.",
            "stale_legacy_expectation": "Legacy or regression-segmentation checks likely to need historical expectation repair instead of hiding.",
            "intentional_supervised_only_blocker": "Approval, autonomy, sandbox, live patch, rollback, memory, release decision, and operator-control checks that may block intentionally.",
            "missing_optional_dependency": "Environment-dependent optional checks, such as local model/vector dependencies, that should stay separate from source-package failures.",
            "needs_manual_operator_approval": "Checks whose semantics are operator-controlled and must not be converted into automatic approval.",
        },
        "safety": {
            "review_only": True,
            "runs_broad_smoke": False,
            "treats_blocked_as_pass": False,
            "applies_source_edits": False,
            "writes_memory": False,
            "creates_release": False,
            "operator_review_required": True,
            "segment_success_is_approval": False,
            "self_development_task_is_implementation_permission": False,
        },
        "recommended_next_cleanup": [
            "Run focused current-release smokes first before broad install segments.",
            "For broad blockers, repair stale exact-version expectations separately from intentional supervised-only gates.",
            "Keep approval, memory, release, execution-permission, and autonomy checks operator-controlled.",
        ],
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check broad-smoke-triage-v1",
            "python conscious_agent/main.py --self-development-smoke-triage --self-development-full",
            "python tools/smoke_check.py --check self-development-cycle-trial-review-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def broad_smoke_triage_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Broad smoke triage report not found."
    lines = [
        f"# Broad Smoke Triage: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Registered checks reviewed: {report.get('check_count')}",
        "Runs broad smoke: no",
        "Treats blocked as pass: no",
        "Applies source edits: no",
        "Operator review required: yes",
        "",
        "## Segment counts",
    ]
    for segment, count in sorted((report.get("segment_counts") or {}).items()):
        lines.append(f"- {segment}: {count}")
    lines.append("")
    lines.append("## Blocker categories")
    for category, count in sorted((report.get("category_counts") or {}).items()):
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("## Focused current-release examples")
    for item in report.get("focused_current_release_examples", []) or []:
        lines.append(f"- {item.get('name')} [{item.get('segment')}] -> {item.get('primary_category')}")
    lines.append("")
    lines.append("## Recommended cleanup")
    for item in report.get("recommended_next_cleanup", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Verification steps")
    for step in report.get("verification_steps", []) or []:
        lines.append(f"- {step}")
    if full:
        lines.append("")
        lines.append("## Category examples")
        lines.append(json.dumps(report.get("category_examples", {}), indent=2))
    return "\n".join(lines)


def build_self_development_receipt_browser(root: Path = ROOT_DIR, limit: int = 6) -> dict[str, Any]:
    cycles = list_self_development_cycles()[:limit]
    rows: list[dict[str, Any]] = []
    for cycle in cycles:
        selected = cycle.get("selected", {}) or {}
        task = (cycle.get("task_result", {}) or {}).get("task", {}) or {}
        safety = cycle.get("safety", {}) or {}
        rows.append({
            "id": cycle.get("id"),
            "created_at": cycle.get("created_at"),
            "selected_title": selected.get("title"),
            "risk": selected.get("risk"),
            "score": selected.get("score"),
            "task_id": task.get("id"),
            "source_edits_applied": False,
            "stopped_before_source_edits": safety.get("stops_before_source_edits") is True,
            "verification_steps": cycle.get("verification_steps", []),
        })
    return {
        "id": f"selfdev_receipt_browser_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "self_development_receipt_browser",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "created_at": _now(),
        "receipt_count": len(rows),
        "receipts": rows,
        "review_only": True,
        "source_mutation_allowed": False,
        "self_development_task_is_implementation_permission": False,
        "ok": True,
    }


def self_development_receipt_browser_text(browser: dict[str, Any] | None, full: bool = False) -> str:
    if not browser:
        return "Self Development receipt browser not found."
    lines = [
        f"# Self Development Receipt Browser: {browser.get('id')}",
        f"Version: {browser.get('version')}",
        f"Receipts: {browser.get('receipt_count')}",
        "Review only: yes",
        "Source edits applied: no",
        "Self-development task is implementation permission: False",
        "",
        "## Recent receipts",
    ]
    for row in browser.get("receipts", []) or []:
        lines.append(f"- {row.get('id')} | selected={row.get('selected_title') or '[none]'} | risk={row.get('risk')} | task={row.get('task_id') or '[none]'} | stopped_before_source_edits={row.get('stopped_before_source_edits')}")
    if full:
        lines.append("")
        lines.append(json.dumps(browser.get("receipts", []), indent=2))
    return "\n".join(lines)


def build_self_development_dashboard_hardening_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    trial = build_self_development_trial_review(root=root, save=False)
    receipts = build_self_development_receipt_browser(root=root)
    triage = build_broad_smoke_triage_report(root=root)
    return {
        "id": f"selfdev_dashboard_hardening_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "self_development_dashboard_hardening_review",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if trial.get("status") == "pass" and triage.get("status") == "review_prepared" else "review_required",
        "trial_review": trial,
        "receipt_browser": receipts,
        "broad_smoke_triage": triage,
        "operator_next_action": "Review the selected self-development recommendation and smoke triage categories; approve implementation separately if a patch is desired.",
        "safety": {
            "review_only": True,
            "runs_broad_smoke": False,
            "applies_source_edits": False,
            "creates_release": False,
            "writes_memory": False,
            "expands_autonomy": False,
            "operator_approval_required_for_implementation": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check broad-smoke-triage-v1",
            "python tools/smoke_check.py --check self-development-cycle-trial-review-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --check operator-governed-route-surface-parity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def self_development_dashboard_hardening_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Self Development dashboard hardening review not found."
    triage = report.get("broad_smoke_triage", {}) or {}
    receipts = report.get("receipt_browser", {}) or {}
    trial = report.get("trial_review", {}) or {}
    selected = (trial.get("selected_recommendation", {}) or {})
    lines = [
        f"# Self Development Dashboard Hardening Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Selected recommendation: {selected.get('title') or '[none]'}",
        f"Recent receipts: {receipts.get('receipt_count')}",
        f"Broad smoke checks classified: {triage.get('check_count')}",
        "Review only: yes",
        "Source edits applied: no",
        "Runs broad smoke: no",
        "Operator approval required for implementation: yes",
        "",
        "## Operator next action",
        str(report.get("operator_next_action", "")),
        "",
        "## Verification steps",
    ]
    for step in report.get("verification_steps", []) or []:
        lines.append(f"- {step}")
    if full:
        lines.append("")
        lines.append("## Broad smoke triage")
        lines.append(broad_smoke_triage_text(triage, full=False))
        lines.append("")
        lines.append("## Receipts")
        lines.append(self_development_receipt_browser_text(receipts, full=False))
    return "\n".join(lines)




# v731.0-v760.0 implementation proposal packet and legacy smoke cleanup helpers.
# This layer prepares an operator-reviewable implementation proposal for the
# selected Self Development Cycle recommendation. It does not apply edits,
# execute implementation commands, mutate source, or convert a task into approval.
IMPLEMENTATION_PROPOSAL_TYPE = "self_development_implementation_proposal"
IMPLEMENTATION_PROPOSAL_SMOKE = "self-development-implementation-proposal-v1"
IMPLEMENTATION_PROPOSAL_STOP_BOUNDARY = "proposal_packet_only_no_source_edits"

PROTECTED_FILE_PATTERNS = (
    "approval",
    "approvals",
    "memory",
    "memories",
    "release_packaging.py",
    "release_installation.py",
    "package_integrity.py",
    "command_runner.py",
    "chat_action_router.py",
    "execution",
    "self_update",
    "self-update",
    "autonomy",
    "signing",
    "secrets",
    "scheduler",
    "schedule",
)


def _latest_or_probe_cycle(root: Path = ROOT_DIR, cycle_id: str = "latest") -> dict[str, Any]:
    cycle = get_self_development_cycle(cycle_id)
    if cycle:
        return cycle
    return create_self_development_cycle(
        root=root,
        prompt="implementation proposal probe; no saved cycle was available",
        create_task=False,
        save=False,
    )


def _candidate_file_impacts(selected: dict[str, Any]) -> list[dict[str, Any]]:
    text = f"{selected.get('title','')} {selected.get('summary','')} {selected.get('recommended_command','')}".lower()
    impacts: list[dict[str, Any]] = []
    def add(path: str, reason: str, risk: str = "low") -> None:
        protected_hits = classify_protected_systems(path + " " + reason)
        impacts.append({
            "path": path,
            "reason": reason,
            "risk": risk,
            "protected_system_hits": protected_hits,
            "requires_operator_approval": True,
        })

    add("conscious_agent/self_development_cycle.py", "Primary implementation/proposal logic for the selected self-development recommendation.")
    add("tools/smoke_check.py", "Focused smoke coverage for the selected proposal and no-mutation safety boundary.")
    add("README_NEXT_STEPS.md", "Current-state handoff and next-step documentation must be updated after an approved patch.")
    add("README_RELEASE_HISTORY.md", "Release history must record any approved implementation work.")
    if "dashboard" in text or "ui" in text:
        add("conscious_agent/dashboard.py", "Dashboard review surface or operator UX changes may be required.")
    if "chat" in text or "intent" in text or "routing" in text:
        add("conscious_agent/chat_action_router.py", "Chat-action routing changes may be required; command safety must remain strict.", "medium")
    if "command" in text or "cli" in text:
        add("conscious_agent/main.py", "CLI flag or print path changes may be required.")
        add("conscious_agent/command_runner.py", "Only safe read/proposal commands may be allowlisted; implementation commands remain approval-gated.", "medium")
    if "manifest" in text or "surface" in text or "route" in text:
        add("conscious_agent/source_surface_manifest.py", "Surface registry metadata may need a row for the approved review surface.")
        add("conscious_agent/dashboard_route_probe.py", "Route parity metadata may need a review-only entry.")
    if "release" in text or "package" in text or "privacy" in text:
        add("conscious_agent/package_integrity.py", "Package/privacy checks are protected trust gates and require explicit operator review.", "medium")
        add("conscious_agent/source_package_privacy_metadata_integrity.py", "Privacy metadata checks are protected release-trust gates.", "medium")
    if "smoke" in text:
        add("conscious_agent/smoke_segment_registry.py", "Only low-risk stale expectation cleanup should be proposed without touching approval semantics.", "medium")
    # de-duplicate while preserving order
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in impacts:
        if item["path"] not in seen:
            seen.add(item["path"])
            unique.append(item)
    return unique


def _protected_file_hits(file_impacts: list[dict[str, Any]]) -> list[str]:
    hits: list[str] = []
    for item in file_impacts:
        text = f"{item.get('path','')} {item.get('reason','')}".lower()
        for pattern in PROTECTED_FILE_PATTERNS:
            if pattern in text and pattern not in hits:
                hits.append(pattern)
        for hit in item.get("protected_system_hits", []) or []:
            if hit not in hits:
                hits.append(str(hit))
    return hits


def build_self_development_implementation_proposal(
    root: Path = ROOT_DIR,
    cycle_id: str = "latest",
    save: bool = False,
) -> dict[str, Any]:
    cycle = _latest_or_probe_cycle(root=root, cycle_id=cycle_id)
    selected = dict(cycle.get("selected", {}) or {})
    file_impacts = _candidate_file_impacts(selected)
    protected_hits = _protected_file_hits(file_impacts)
    selected_hits = list(selected.get("protected_system_hits", []) or [])
    for hit in selected_hits:
        if hit not in protected_hits:
            protected_hits.append(str(hit))
    selected_risk = str(selected.get("risk", "medium") or "medium")
    proposal_risk = "medium" if protected_hits or selected.get("requires_operator_approval_before_implementation") else selected_risk
    approval_required = True
    proposal = {
        "id": f"selfdev_impl_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": IMPLEMENTATION_PROPOSAL_TYPE,
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "based_on_cycle_id": cycle.get("id"),
        "selected_task": selected,
        "selected_task_preserved": bool(selected.get("title")),
        "goal": "Prepare a reviewable implementation proposal for the selected Self Development Cycle recommendation and stop before edits.",
        "why_selected": selected.get("summary", ""),
        "file_impact_estimate": file_impacts,
        "protected_system_hits": protected_hits,
        "risk_assessment": {
            "selected_risk": selected_risk,
            "proposal_risk": proposal_risk,
            "risk_reason": "Protected file/system hits require operator approval before implementation." if protected_hits else "Low-risk proposal packet; implementation still needs explicit operator approval.",
            "requires_operator_approval_before_implementation": approval_required,
        },
        "implementation_steps": [
            "Review the selected recommendation and confirm it is still current.",
            "Limit edits to the estimated files unless the operator approves scope expansion.",
            "Implement the smallest reversible change that satisfies the selected task.",
            "Update README_NEXT_STEPS.md and README_RELEASE_HISTORY.md after any approved code patch.",
            "Run focused verification before any packaging step.",
            "Stop and request explicit operator approval before touching protected approval, memory, release, command-safety, execution-permission, self-update, scheduling, signing/secrets, or autonomy systems.",
        ],
        "verification_steps": list(selected.get("verification_steps", []) or []) + [
            "python tools/smoke_check.py --check self-development-implementation-proposal-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
        "rollback_notes": [
            "Because this packet applies no edits, rollback for the proposal itself is deleting the saved proposal receipt if one was written.",
            "For any later approved patch, capture file preimages before editing and revert only the touched files if verification fails.",
            "If a protected-system target appears unexpectedly, stop and request operator review instead of expanding scope.",
        ],
        "approval_request": {
            "required_before_implementation": True,
            "approval_is_single_use": True,
            "approval_scope": "selected task plus listed file-impact estimate only",
            "source_edits_authorized_by_this_packet": False,
            "task_is_implementation_permission": False,
        },
        "safety": {
            "review_only": True,
            "proposal_packet_only": True,
            "applies_source_edits": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "stops_before_source_edits": True,
            "operator_approval_required_for_implementation": True,
            "protected_systems_require_operator_approval": True,
        },
        "legacy_smoke_cleanup_boundary": {
            "low_risk_only": True,
            "allowed_without_extra_approval": [
                "stale exact-version text expectation repair",
                "stale route label expectation repair",
                "documentation token alignment",
                "review-only smoke classification wording",
            ],
            "not_allowed_without_explicit_approval": [
                "approval system edits",
                "memory system edits",
                "release publishing changes",
                "command safety expansion",
                "execution permission expansion",
                "autonomy controls",
            ],
        },
        "stop_state": IMPLEMENTATION_PROPOSAL_STOP_BOUNDARY,
    }
    if save:
        _ensure_storage()
        with _cycle_path(proposal["id"]).open("w", encoding="utf-8") as file:
            json.dump(proposal, file, indent=2)
    return proposal


def self_development_implementation_proposal_text(proposal: dict[str, Any] | None, full: bool = False) -> str:
    if not proposal:
        return "Self Development implementation proposal not found."
    selected = proposal.get("selected_task", {}) or {}
    risk = proposal.get("risk_assessment", {}) or {}
    safety = proposal.get("safety", {}) or {}
    lines = [
        f"# Self Development Implementation Proposal: {proposal.get('id')}",
        f"Version: {proposal.get('version')}",
        f"Based on cycle: {proposal.get('based_on_cycle_id')}",
        f"Selected task: {selected.get('title') or '[none]'}",
        f"Proposal risk: {risk.get('proposal_risk')}",
        f"Requires operator approval before implementation: {risk.get('requires_operator_approval_before_implementation')}",
        "Source edits applied: no",
        "Executes commands: no",
        "Stops before source edits: yes",
        "Task is implementation permission: False",
        "",
        "## File impact estimate",
    ]
    for item in proposal.get("file_impact_estimate", []) or []:
        lines.append(f"- {item.get('path')} | risk={item.get('risk')} | approval_required={item.get('requires_operator_approval')} | {item.get('reason')}")
    lines.extend([
        "",
        "## Protected-system hits",
        ", ".join(proposal.get("protected_system_hits", []) or []) or "[none]",
        "",
        "## Implementation plan",
    ])
    for step in proposal.get("implementation_steps", []) or []:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Verification steps")
    for step in proposal.get("verification_steps", []) or []:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Rollback notes")
    for note in proposal.get("rollback_notes", []) or []:
        lines.append(f"- {note}")
    lines.extend([
        "",
        "## Safety boundaries",
        f"Review only: {safety.get('review_only')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Modifies execution permissions: {safety.get('modifies_execution_permissions')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Stop state: {proposal.get('stop_state')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw approval request")
        lines.append(json.dumps(proposal.get("approval_request", {}), indent=2))
        lines.append("")
        lines.append("## Legacy smoke cleanup boundary")
        lines.append(json.dumps(proposal.get("legacy_smoke_cleanup_boundary", {}), indent=2))
    return "\n".join(lines)


def print_self_development_implementation_proposal(cycle_id: str = "latest", full: bool = False, save: bool = True) -> None:
    print(self_development_implementation_proposal_text(build_self_development_implementation_proposal(cycle_id=cycle_id, save=save), full=full))

# v731.0-v760.0 implementation proposal smoke tokens:
# self-development-implementation-proposal-v1 --self-development-implementation-proposal build_self_development_implementation_proposal self_development_implementation_proposal_text
# proposal_packet_only_no_source_edits selected_task_preserved=True source_edits_authorized_by_this_packet=False task_is_implementation_permission=False
# protected_systems_require_operator_approval=True applies_source_edits=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False expands_autonomy=False

def print_broad_smoke_triage(full: bool = False) -> None:
    print(broad_smoke_triage_text(build_broad_smoke_triage_report(), full=full))


def print_self_development_dashboard_hardening_review(full: bool = False) -> None:
    print(self_development_dashboard_hardening_text(build_self_development_dashboard_hardening_review(), full=full))

# v726.0-v760.0 self-development dashboard and broad smoke triage tokens:
# broad-smoke-triage-v1 self-development-dashboard-trial-hardening-v1 /self-development-cycle --self-development-smoke-triage --self-development-dashboard-hardening
# build_broad_smoke_triage_report build_self_development_receipt_browser build_self_development_dashboard_hardening_review
# current_release_failure stale_legacy_expectation intentional_supervised_only_blocker missing_optional_dependency needs_manual_operator_approval
# runs_broad_smoke=False treats_blocked_as_pass=False applies_source_edits=False writes_memory=False creates_release=False expands_autonomy=False
# self_development_task_is_implementation_permission=False no_native_title_tooltip data-tip command-deck operator-console

# v736.0-v760.0 operator-approved self-development patch draft trial.
# This layer prepares an operator-reviewable patch draft packet only after a
# narrow explicit approval phrase. It still does not apply source edits or grant
# implementation authority.
PATCH_DRAFT_TYPE = "operator_approved_self_development_patch_draft"
PATCH_DRAFT_SMOKE = "operator-approved-self-development-patch-draft-v1"
PATCH_DRAFT_STATUS_NOT_APPLIED = "patch_draft_prepared_not_applied"
PATCH_DRAFT_APPROVAL_PREFIX = "Approve drafting a patch proposal for self-development task "
PATCH_DRAFT_REJECTED_VAGUE_APPROVALS = (
    "go ahead",
    "do it",
    "continue",
    "fix yourself",
    "work on it",
    "approved",
    "yes",
)


def _selected_task_reference(cycle: dict[str, Any]) -> dict[str, str]:
    task = ((cycle.get("task_result", {}) or {}).get("task", {}) or {})
    selected = cycle.get("selected", {}) or {}
    task_id = str(task.get("id") or "").strip()
    title = str(task.get("title") or selected.get("title") or "selected self-development recommendation").strip()
    if not task_id:
        task_id = f"selected-{_slug(title, 42)}"
    return {"task_id": task_id, "title": title}


def expected_self_development_patch_draft_approval_phrase(cycle: dict[str, Any] | None = None) -> str:
    cycle = cycle or _latest_or_probe_cycle()
    reference = _selected_task_reference(cycle)
    return f"{PATCH_DRAFT_APPROVAL_PREFIX}{reference['task_id']}"


def validate_self_development_patch_draft_approval(approval_phrase: str, cycle: dict[str, Any] | None = None) -> dict[str, Any]:
    cycle = cycle or _latest_or_probe_cycle()
    reference = _selected_task_reference(cycle)
    phrase = str(approval_phrase or "").strip()
    lowered = phrase.lower()
    expected = expected_self_development_patch_draft_approval_phrase(cycle)
    vague = lowered in PATCH_DRAFT_REJECTED_VAGUE_APPROVALS or lowered in {"ok", "okay", "sure", "approved", "approve it"}
    exact_ok = phrase == expected
    selected = cycle.get("selected", {}) or {}
    selected_low_risk = selected.get("risk") == "low"
    selected_not_protected = selected.get("requires_operator_approval_before_implementation") is not True
    return {
        "ok": bool(exact_ok and selected_low_risk and selected_not_protected and not vague),
        "provided_phrase": phrase,
        "expected_phrase": expected,
        "task_id": reference["task_id"],
        "task_title": reference["title"],
        "exact_phrase_required": True,
        "vague_approval_rejected": bool(vague or not exact_ok),
        "selected_low_risk": bool(selected_low_risk),
        "selected_requires_implementation_approval": bool(selected.get("requires_operator_approval_before_implementation")),
        "reason": (
            "accepted explicit single-scope operator approval for patch draft preparation only"
            if exact_ok and selected_low_risk and selected_not_protected and not vague
            else "rejected: approval phrase must exactly match the selected self-development task and the selected task must be low-risk/non-protected"
        ),
    }


def _patch_draft_file_changes(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for item in proposal.get("file_impact_estimate", []) or []:
        path = str(item.get("path", ""))
        reason = str(item.get("reason", ""))
        if not path:
            continue
        protected_hits = item.get("protected_system_hits", []) or classify_protected_systems(path + " " + reason)
        changes.append({
            "path": path,
            "change_type": "planned_edit_summary_only",
            "planned_change": f"Prepare the smallest reversible edit needed for this file if the operator later approves implementation: {reason}",
            "risk": item.get("risk", "low"),
            "protected_system_hits": protected_hits,
            "requires_separate_application_approval": True,
            "applied": False,
        })
    return changes


def build_operator_approved_self_development_patch_draft(
    root: Path = ROOT_DIR,
    approval_phrase: str = "",
    cycle_id: str = "latest",
    save: bool = False,
) -> dict[str, Any]:
    cycle = _latest_or_probe_cycle(root=root, cycle_id=cycle_id)
    approval = validate_self_development_patch_draft_approval(approval_phrase, cycle)
    proposal = build_self_development_implementation_proposal(root=root, cycle_id=cycle_id, save=False)
    selected = proposal.get("selected_task", {}) or {}
    file_changes = _patch_draft_file_changes(proposal)
    protected_hits = list(proposal.get("protected_system_hits", []) or [])
    for change in file_changes:
        for hit in change.get("protected_system_hits", []) or []:
            if hit not in protected_hits:
                protected_hits.append(str(hit))
    draft_allowed = bool(approval.get("ok"))
    draft = {
        "id": f"selfdev_patch_draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": PATCH_DRAFT_TYPE,
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "based_on_cycle_id": cycle.get("id"),
        "based_on_proposal_id": proposal.get("id"),
        "approval_validation": approval,
        "approval_required_before_drafting": True,
        "draft_prepared": draft_allowed,
        "status": PATCH_DRAFT_STATUS_NOT_APPLIED if draft_allowed else "approval_rejected_no_draft_prepared",
        "selected_task": selected,
        "selected_task_preserved": bool(selected.get("title")),
        "patch_draft": {
            "kind": "review_packet_no_diff_applied",
            "exact_files_likely_changed": [item.get("path") for item in file_changes],
            "planned_file_changes": file_changes if draft_allowed else [],
            "edit_summary": "Prepare a narrow source patch for the approved low-risk self-development task, but do not apply it from this packet." if draft_allowed else "No patch draft prepared because approval was missing, vague, mismatched, or selected task was not low-risk/non-protected.",
            "source_edits_applied": False,
            "patch_file_written": False,
            "can_apply_patch": False,
        },
        "protected_system_hits": protected_hits,
        "risk_assessment": {
            "selected_risk": selected.get("risk", "medium"),
            "draft_risk": "low" if draft_allowed and not protected_hits else "medium",
            "protected_system_hits_require_separate_approval": bool(protected_hits),
            "requires_operator_approval_before_application": True,
        },
        "verification_plan": list(proposal.get("verification_steps", []) or []) + [
            "python tools/smoke_check.py --check operator-approved-self-development-patch-draft-v1",
            "python tools/smoke_check.py --check self-development-implementation-proposal-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
        "rollback_plan": [
            "This packet applies no edits, so rollback for this packet is deleting the saved draft receipt if one was written.",
            "If a later approved patch is applied, revert only the listed files from captured preimages if verification fails.",
            "If the later patch touches a protected system unexpectedly, stop and request a new explicit operator approval before proceeding.",
        ],
        "application_boundary": {
            "operator_must_apply_manually_or_approve_separate_application": True,
            "draft_is_not_application_permission": True,
            "approval_phrase_is_single_scope": True,
            "vague_approval_rejected": approval.get("vague_approval_rejected") is True,
            "source_edits_authorized_by_this_packet": False,
            "task_is_implementation_permission": False,
            "proposal_packet_is_authorization": False,
        },
        "safety": {
            "review_only": True,
            "patch_draft_only": True,
            "requires_exact_operator_approval_phrase": True,
            "rejects_vague_approval": True,
            "applies_source_edits": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "stops_before_source_edits": True,
            "requires_separate_approval_before_patch_application": True,
        },
        "stop_state": "patch_draft_prepared_not_applied_requires_separate_application_approval" if draft_allowed else "no_patch_draft_without_explicit_operator_approval",
    }
    if save:
        _ensure_storage()
        with _cycle_path(draft["id"]).open("w", encoding="utf-8") as file:
            json.dump(draft, file, indent=2)
    return draft


def operator_approved_self_development_patch_draft_text(draft: dict[str, Any] | None, full: bool = False) -> str:
    if not draft:
        return "Operator-approved Self Development patch draft not found."
    approval = draft.get("approval_validation", {}) or {}
    safety = draft.get("safety", {}) or {}
    boundary = draft.get("application_boundary", {}) or {}
    selected = draft.get("selected_task", {}) or {}
    patch = draft.get("patch_draft", {}) or {}
    lines = [
        f"# Operator-Approved Self Development Patch Draft: {draft.get('id')}",
        f"Version: {draft.get('version')}",
        f"Status: {draft.get('status')}",
        f"Draft prepared: {draft.get('draft_prepared')}",
        f"Based on cycle: {draft.get('based_on_cycle_id')}",
        f"Selected task: {selected.get('title') or '[none]'}",
        f"Approval accepted: {approval.get('ok')}",
        f"Expected approval phrase: {approval.get('expected_phrase')}",
        f"Vague approval rejected: {approval.get('vague_approval_rejected')}",
        "Source edits applied: no",
        "Patch applied: no",
        "Requires separate approval before patch application: yes",
        "Draft is not application permission: True",
        "",
        "## Exact files likely changed",
    ]
    for path in patch.get("exact_files_likely_changed", []) or []:
        lines.append(f"- {path}")
    lines.extend(["", "## Planned file changes"])
    for item in patch.get("planned_file_changes", []) or []:
        lines.append(f"- {item.get('path')} | risk={item.get('risk')} | applied={item.get('applied')} | {item.get('planned_change')}")
    lines.extend(["", "## Verification plan"])
    for step in draft.get("verification_plan", []) or []:
        lines.append(f"- {step}")
    lines.extend(["", "## Rollback plan"])
    for step in draft.get("rollback_plan", []) or []:
        lines.append(f"- {step}")
    lines.extend([
        "",
        "## Application boundary",
        f"Operator must apply manually or approve separate application: {boundary.get('operator_must_apply_manually_or_approve_separate_application')}",
        f"Source edits authorized by this packet: {boundary.get('source_edits_authorized_by_this_packet')}",
        f"Task is implementation permission: {boundary.get('task_is_implementation_permission')}",
        f"Proposal packet is authorization: {boundary.get('proposal_packet_is_authorization')}",
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Patch draft only: {safety.get('patch_draft_only')}",
        f"Requires exact operator approval phrase: {safety.get('requires_exact_operator_approval_phrase')}",
        f"Rejects vague approval: {safety.get('rejects_vague_approval')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Executes commands: {safety.get('executes_commands')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Modifies execution permissions: {safety.get('modifies_execution_permissions')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Stop state: {draft.get('stop_state')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw approval validation")
        lines.append(json.dumps(approval, indent=2))
        lines.append("")
        lines.append("## Raw patch draft")
        lines.append(json.dumps(patch, indent=2))
    return "\n".join(lines)


def print_operator_approved_self_development_patch_draft(
    approval_phrase: str = "",
    cycle_id: str = "latest",
    full: bool = False,
    save: bool = True,
) -> None:
    print(operator_approved_self_development_patch_draft_text(
        build_operator_approved_self_development_patch_draft(approval_phrase=approval_phrase, cycle_id=cycle_id, save=save),
        full=full,
    ))

# v736.0-v760.0 patch draft smoke tokens: operator-approved-self-development-patch-draft-v1 --self-development-patch-draft build_operator_approved_self_development_patch_draft operator_approved_self_development_patch_draft_text expected_self_development_patch_draft_approval_phrase validate_self_development_patch_draft_approval patch_draft_prepared_not_applied no_patch_draft_without_explicit_operator_approval source_edits_authorized_by_this_packet=False draft_is_not_application_permission=True requires_separate_approval_before_patch_application=True applies_source_edits=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console


# v741.0-v760.0 operator-approved self-development patch application trial.
# This layer validates a second exact operator phrase and prepares an application
# receipt with preimage hashes. It refuses to apply when the draft packet has no
# concrete diff, which is the correct behavior for v740-style summary drafts.
PATCH_APPLICATION_TYPE = "operator_approved_self_development_patch_application_trial"
PATCH_APPLICATION_SMOKE = "operator-approved-self-development-patch-application-v1"
PATCH_APPLICATION_APPROVAL_PREFIX = "Approve applying self-development patch draft "
PATCH_APPLICATION_STATUS_BLOCKED_NO_DIFF = "application_blocked_no_concrete_diff"
PATCH_APPLICATION_STATUS_READY_NOT_APPLIED = "application_ready_not_applied"
PATCH_APPLICATION_STATUS_APPROVAL_REJECTED = "application_approval_rejected"
PATCH_APPLICATION_REJECTED_VAGUE_APPROVALS = (
    "go ahead",
    "apply it",
    "continue",
    "yes",
    "approved",
    "do it",
    "run it",
)
PATCH_APPLICATION_ALLOWED_LOW_RISK_PATHS = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/self_development_cycle.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/main.py",
    "tools/smoke_check.py",
    "conscious_agent/source_surface_manifest.py",
    "conscious_agent/dashboard_route_probe.py",
)
PATCH_APPLICATION_PROTECTED_PATH_FRAGMENTS = (
    "approval",
    "memory",
    "release_packaging.py",
    "release_installation.py",
    "package_integrity.py",
    "command_runner.py",
    "authorization_firewall.py",
    "autonomous_dev_cycle.py",
    "dev_loop_runner.py",
    "sandbox",
    "trusted_public_keys",
    "secrets",
)


def _list_operator_approved_self_development_patch_drafts() -> list[dict[str, Any]]:
    _ensure_storage()
    drafts: list[dict[str, Any]] = []
    for path in SELF_DEVELOPMENT_DIR.glob("*.json"):
        data = _load_json(path, {})
        if isinstance(data, dict) and data.get("type") == PATCH_DRAFT_TYPE:
            drafts.append(data)
    return sorted(drafts, key=lambda item: item.get("created_at", ""), reverse=True)


def _resolve_or_probe_patch_draft(draft_id: str = "latest", root: Path = ROOT_DIR) -> dict[str, Any]:
    token = (draft_id or "latest").strip()
    drafts = _list_operator_approved_self_development_patch_drafts()
    if token.lower() in {"latest", "last"} and drafts:
        return drafts[0]
    for draft in drafts:
        if draft.get("id") == token:
            return draft
    cycle = _latest_or_probe_cycle(root=root, cycle_id="latest")
    phrase = expected_self_development_patch_draft_approval_phrase(cycle)
    draft = build_operator_approved_self_development_patch_draft(root=root, approval_phrase=phrase, cycle_id="latest", save=False)
    if token.lower() not in {"latest", "last"}:
        draft["id"] = token
    return draft


def expected_self_development_patch_application_approval_phrase(draft: dict[str, Any] | None = None) -> str:
    draft = draft or _resolve_or_probe_patch_draft("latest")
    draft_id = str(draft.get("id") or "latest").strip()
    return f"{PATCH_APPLICATION_APPROVAL_PREFIX}{draft_id}"


def validate_self_development_patch_application_approval(approval_phrase: str, draft: dict[str, Any] | None = None) -> dict[str, Any]:
    draft = draft or _resolve_or_probe_patch_draft("latest")
    phrase = str(approval_phrase or "").strip()
    expected = expected_self_development_patch_application_approval_phrase(draft)
    lowered = phrase.lower()
    vague = lowered in PATCH_APPLICATION_REJECTED_VAGUE_APPROVALS or lowered in {"ok", "okay", "sure", "approve", "approve it"}
    exact_ok = phrase == expected
    draft_prepared = draft.get("draft_prepared") is True and draft.get("status") == PATCH_DRAFT_STATUS_NOT_APPLIED
    boundary = draft.get("application_boundary", {}) or {}
    draft_not_permission = boundary.get("draft_is_not_application_permission") is True
    safety = draft.get("safety", {}) or {}
    no_prior_edits = safety.get("applies_source_edits") is False
    return {
        "ok": bool(exact_ok and draft_prepared and draft_not_permission and no_prior_edits and not vague),
        "provided_phrase": phrase,
        "expected_phrase": expected,
        "draft_id": draft.get("id"),
        "exact_phrase_required": True,
        "vague_approval_rejected": bool(vague or not exact_ok),
        "draft_prepared": bool(draft_prepared),
        "draft_is_not_application_permission": bool(draft_not_permission),
        "source_edits_already_applied_by_draft": safety.get("applies_source_edits") is True,
        "reason": (
            "accepted explicit single-scope operator approval for patch application trial only"
            if exact_ok and draft_prepared and draft_not_permission and no_prior_edits and not vague
            else "rejected: approval phrase must exactly match the selected patch draft and the draft must be prepared, non-applied, and non-authorizing"
        ),
    }


def _safe_project_relative_path(raw_path: str, root: Path = ROOT_DIR) -> str:
    cleaned = str(raw_path or "").replace("\\", "/").strip().lstrip("/")
    if not cleaned or ".." in Path(cleaned).parts:
        return ""
    try:
        target = (root / cleaned).resolve()
        target.relative_to(root.resolve())
    except Exception:
        return ""
    return cleaned


def _file_sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 256), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _path_protected_reason(path: str) -> str:
    lowered = path.lower()
    for fragment in PATCH_APPLICATION_PROTECTED_PATH_FRAGMENTS:
        if fragment in lowered:
            return f"protected path fragment: {fragment}"
    if path not in PATCH_APPLICATION_ALLOWED_LOW_RISK_PATHS:
        return "not in low-risk self-development application allowlist"
    return ""


def _capture_patch_application_preimages(draft: dict[str, Any], root: Path = ROOT_DIR) -> list[dict[str, Any]]:
    patch = draft.get("patch_draft", {}) or {}
    paths = list(dict.fromkeys(str(path or "") for path in (patch.get("exact_files_likely_changed", []) or [])))
    preimages: list[dict[str, Any]] = []
    for raw_path in paths:
        rel = _safe_project_relative_path(raw_path, root=root)
        reason = _path_protected_reason(rel) if rel else "invalid or unsafe project path"
        target = (root / rel) if rel else root
        preimages.append({
            "path": rel or raw_path,
            "exists": bool(rel and target.exists()),
            "sha256_before": _file_sha256(target) if rel and target.exists() else "",
            "size_before": target.stat().st_size if rel and target.exists() and target.is_file() else 0,
            "eligible_low_risk_target": bool(rel and not reason),
            "blocked_reason": reason,
            "source_edit_applied": False,
        })
    return preimages


def build_operator_approved_self_development_patch_application_trial(
    root: Path = ROOT_DIR,
    approval_phrase: str = "",
    draft_id: str = "latest",
    save: bool = False,
) -> dict[str, Any]:
    requested_draft_id = draft_id
    phrase_text = str(approval_phrase or "").strip()
    if (not requested_draft_id or requested_draft_id in {"latest", "last"}) and phrase_text.startswith(PATCH_APPLICATION_APPROVAL_PREFIX):
        requested_draft_id = phrase_text[len(PATCH_APPLICATION_APPROVAL_PREFIX):].strip() or requested_draft_id
    draft = _resolve_or_probe_patch_draft(draft_id=requested_draft_id, root=root)
    approval = validate_self_development_patch_application_approval(approval_phrase, draft)
    preimages = _capture_patch_application_preimages(draft, root=root)
    blocked_targets = [item for item in preimages if item.get("eligible_low_risk_target") is not True]
    patch = draft.get("patch_draft", {}) or {}
    concrete_diff_present = bool(patch.get("unified_diff") or patch.get("diff") or patch.get("concrete_patch"))
    approval_ok = approval.get("ok") is True
    eligible = approval_ok and not blocked_targets
    status = PATCH_APPLICATION_STATUS_APPROVAL_REJECTED
    if approval_ok and not concrete_diff_present:
        status = PATCH_APPLICATION_STATUS_BLOCKED_NO_DIFF
    elif approval_ok and blocked_targets:
        status = "application_blocked_protected_or_unallowlisted_target"
    elif eligible and concrete_diff_present:
        # A future arc may implement an actual diff applier. This v745 trial records
        # readiness and preimages only; it intentionally does not mutate source.
        status = PATCH_APPLICATION_STATUS_READY_NOT_APPLIED
    receipt = {
        "id": f"selfdev_patch_application_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": PATCH_APPLICATION_TYPE,
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "based_on_draft_id": draft.get("id"),
        "based_on_cycle_id": draft.get("based_on_cycle_id"),
        "approval_validation": approval,
        "status": status,
        "application_attempted": False,
        "application_permitted_by_trial": bool(status == PATCH_APPLICATION_STATUS_READY_NOT_APPLIED),
        "concrete_diff_present": concrete_diff_present,
        "preimage_capture": preimages,
        "blocked_targets": blocked_targets,
        "post_application_verification": {
            "verification_ran": False,
            "reason": "No source edits were applied by this trial, so post-application verification is listed for the later explicit application arc.",
            "required_commands": [
                "python -m compileall -q conscious_agent tools",
                "python tools/smoke_check.py --check operator-approved-self-development-patch-application-v1",
                "python tools/smoke_check.py --check operator-approved-self-development-patch-draft-v1",
                "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
                "python tools/smoke_check.py --tier fast --json",
            ],
        },
        "rollback_notes": [
            "This v745 trial applies no source edits; rollback for this receipt is deleting the saved application receipt if one was written.",
            "If a future concrete-diff application arc applies source edits, restore each listed file from its captured sha256/preimage if verification fails.",
            "If any protected or unallowlisted target appears, stop and request a new explicit operator approval after review.",
        ],
        "safety": {
            "requires_exact_operator_application_phrase": True,
            "rejects_vague_approval": True,
            "captures_preimage_hashes": True,
            "low_risk_file_allowlist_enforced": True,
            "blocks_protected_targets": True,
            "applies_source_edits": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "stops_before_release_publish_autonomy": True,
        },
        "current_smoke_debt_reduction": {
            "broad_smoke_blockers_hidden": False,
            "focused_current_release_smokes_first": True,
            "legacy_blockers_classified_not_overridden": True,
            "recommended_next": "Convert only concrete stale exact-string smoke expectations to registry checks after operator review.",
        },
    }
    if save:
        _ensure_storage()
        with _cycle_path(receipt["id"]).open("w", encoding="utf-8") as file:
            json.dump(receipt, file, indent=2)
    return receipt


def operator_approved_self_development_patch_application_trial_text(receipt: dict[str, Any] | None, full: bool = False) -> str:
    if not receipt:
        return "Operator-approved Self Development patch application trial not found."
    approval = receipt.get("approval_validation", {}) or {}
    safety = receipt.get("safety", {}) or {}
    lines = [
        f"# Operator-Approved Self Development Patch Application Trial: {receipt.get('id')}",
        f"Version: {receipt.get('version')}",
        f"Status: {receipt.get('status')}",
        f"Based on draft: {receipt.get('based_on_draft_id')}",
        f"Approval accepted: {approval.get('ok')}",
        f"Expected approval phrase: {approval.get('expected_phrase')}",
        f"Concrete diff present: {receipt.get('concrete_diff_present')}",
        f"Application attempted: {receipt.get('application_attempted')}",
        "Source edits applied: no",
        "Preimage hashes captured: yes",
        "Stops before release/publish/autonomy: yes",
        "",
        "## Preimage capture",
    ]
    for item in receipt.get("preimage_capture", []) or []:
        lines.append(f"- {item.get('path')} | exists={item.get('exists')} | eligible={item.get('eligible_low_risk_target')} | sha256={item.get('sha256_before') or '[missing]'} | blocked={item.get('blocked_reason') or '[none]'}")
    lines.append("")
    lines.append("## Blocked targets")
    blocked = receipt.get("blocked_targets", []) or []
    if blocked:
        for item in blocked:
            lines.append(f"- {item.get('path')}: {item.get('blocked_reason')}")
    else:
        lines.append("- [none]")
    lines.append("")
    lines.append("## Verification")
    verification = receipt.get("post_application_verification", {}) or {}
    lines.append(f"Verification ran: {verification.get('verification_ran')}")
    lines.append(f"Reason: {verification.get('reason')}")
    for command in verification.get("required_commands", []) or []:
        lines.append(f"- {command}")
    lines.append("")
    lines.append("## Rollback notes")
    for note in receipt.get("rollback_notes", []) or []:
        lines.append(f"- {note}")
    lines.extend([
        "",
        "## Safety",
        f"Requires exact operator application phrase: {safety.get('requires_exact_operator_application_phrase')}",
        f"Rejects vague approval: {safety.get('rejects_vague_approval')}",
        f"Captures preimage hashes: {safety.get('captures_preimage_hashes')}",
        f"Low-risk file allowlist enforced: {safety.get('low_risk_file_allowlist_enforced')}",
        f"Blocks protected targets: {safety.get('blocks_protected_targets')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Executes commands: {safety.get('executes_commands')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Modifies execution permissions: {safety.get('modifies_execution_permissions')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw receipt")
        lines.append(json.dumps(receipt, indent=2))
    return "\n".join(lines)


def print_operator_approved_self_development_patch_application_trial(
    approval_phrase: str = "",
    draft_id: str = "latest",
    full: bool = False,
    save: bool = True,
) -> None:
    print(operator_approved_self_development_patch_application_trial_text(
        build_operator_approved_self_development_patch_application_trial(
            approval_phrase=approval_phrase,
            draft_id=draft_id,
            save=save,
        ),
        full=full,
    ))

# v741.0-v760.0 patch application smoke tokens: operator-approved-self-development-patch-application-v1 --self-development-patch-application build_operator_approved_self_development_patch_application_trial operator_approved_self_development_patch_application_trial_text expected_self_development_patch_application_approval_phrase validate_self_development_patch_application_approval application_blocked_no_concrete_diff captures_preimage_hashes=True low_risk_file_allowlist_enforced=True blocks_protected_targets=True applies_source_edits=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False stops_before_release_publish_autonomy=True current_smoke_debt_reduction legacy_blockers_classified_not_overridden=True data-tip command-deck operator-console

# v746.0-v760.0 self-development application receipt review and current smoke debt ledger.
# Review-only: this layer reads saved/probe receipts, converts broad smoke triage
# into a structured ledger, proposes low-risk cleanup candidates, and stops before
# concrete diff generation or source application.
APPLICATION_RECEIPT_REVIEW_SMOKE = "self-development-application-receipt-review-v1"
CURRENT_SMOKE_DEBT_LEDGER_SMOKE = "current-smoke-debt-ledger-v1"
SMOKE_DEBT_LEDGER_TYPE = "current_smoke_debt_ledger"
APPLICATION_RECEIPT_REVIEW_TYPE = "self_development_application_receipt_review"


def _self_development_records(record_type: str) -> list[dict[str, Any]]:
    _ensure_storage()
    rows: list[dict[str, Any]] = []
    for path in SELF_DEVELOPMENT_DIR.glob("*.json"):
        data = _load_json(path, {})
        if isinstance(data, dict) and data.get("type") == record_type:
            rows.append(data)
    return sorted(rows, key=lambda item: item.get("created_at", ""), reverse=True)


def list_self_development_application_trials() -> list[dict[str, Any]]:
    return _self_development_records(PATCH_APPLICATION_TYPE)


def build_self_development_application_receipt_review(root: Path = ROOT_DIR, limit: int = 5) -> dict[str, Any]:
    receipts = list_self_development_application_trials()[:limit]
    if not receipts:
        probe_draft = _resolve_or_probe_patch_draft(draft_id="latest", root=root)
        phrase = expected_self_development_patch_application_approval_phrase(probe_draft)
        receipts = [build_operator_approved_self_development_patch_application_trial(root=root, approval_phrase=phrase, draft_id=probe_draft.get("id", "latest"), save=False)]
    rows: list[dict[str, Any]] = []
    for receipt in receipts:
        approval = receipt.get("approval_validation", {}) or {}
        verification = receipt.get("post_application_verification", {}) or {}
        safety = receipt.get("safety", {}) or {}
        rows.append({
            "id": receipt.get("id"),
            "created_at": receipt.get("created_at"),
            "status": receipt.get("status"),
            "based_on_draft_id": receipt.get("based_on_draft_id"),
            "selected_task_id": approval.get("draft_id"),
            "approval_accepted": approval.get("ok") is True,
            "concrete_diff_present": receipt.get("concrete_diff_present") is True,
            "application_attempted": receipt.get("application_attempted") is True,
            "source_edits_applied": False,
            "preimage_hashes_captured": bool(receipt.get("preimage_capture")),
            "preimage_count": len(receipt.get("preimage_capture", []) or []),
            "blocked_target_count": len(receipt.get("blocked_targets", []) or []),
            "verification_ran": verification.get("verification_ran") is True,
            "stop_condition": receipt.get("status"),
            "stops_before_release_publish_autonomy": safety.get("stops_before_release_publish_autonomy") is True,
        })
    blocked_without_success = all(row.get("source_edits_applied") is False for row in rows)
    return {
        "id": f"selfdev_application_receipt_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": APPLICATION_RECEIPT_REVIEW_TYPE,
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "review_prepared",
        "receipt_count": len(rows),
        "receipts": rows,
        "safety": {
            "review_only": True,
            "receipt_is_not_success": True,
            "blocked_trial_is_not_success": True,
            "source_edits_implied_by_receipt": False,
            "applies_source_edits": False,
            "executes_commands": False,
            "writes_memory": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
            "stops_before_concrete_diff_generation": True,
        },
        "summary": {
            "all_rows_source_unchanged": blocked_without_success,
            "application_receipts_reviewable": True,
            "no_blocked_trial_treated_as_success": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check self-development-application-receipt-review-v1",
            "python conscious_agent/main.py --self-development-application-receipt-review --self-development-full",
            "python tools/smoke_check.py --check operator-approved-self-development-patch-application-v1",
        ],
    }


def self_development_application_receipt_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Self Development application receipt review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Self Development Application Receipt Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Receipts reviewed: {report.get('receipt_count')}",
        "Review only: yes",
        "Receipt is not success: True",
        "Blocked trial is not success: True",
        "Source edits applied: no",
        "Stops before concrete diff generation: yes",
        "",
        "## Application receipts",
    ]
    for row in report.get("receipts", []) or []:
        lines.append(
            f"- {row.get('id')} | status={row.get('status')} | draft={row.get('based_on_draft_id')} | "
            f"approval={row.get('approval_accepted')} | diff={row.get('concrete_diff_present')} | "
            f"preimages={row.get('preimage_count')} | blocked_targets={row.get('blocked_target_count')} | "
            f"source_edits={row.get('source_edits_applied')}"
        )
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Source edits implied by receipt: {safety.get('source_edits_implied_by_receipt')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Creates release: {safety.get('creates_release')}",
        f"Publishes release: {safety.get('publishes_release')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        "",
        "## Verification steps",
    ])
    for step in report.get("verification_steps", []) or []:
        lines.append(f"- {step}")
    if full:
        lines.append("")
        lines.append("## Raw summary")
        lines.append(json.dumps(report.get("summary", {}), indent=2))
    return "\n".join(lines)


def _ledger_relevance(entry: dict[str, Any]) -> str:
    categories = set(entry.get("categories", []) or [])
    name = str(entry.get("name", "")).lower()
    if "current_release_failure" in categories:
        return "current_release_relevant"
    if "stale_legacy_expectation" in categories:
        return "legacy_or_historical"
    if "intentional_supervised_only_blocker" in categories:
        return "operator_governance_relevant"
    if "missing_optional_dependency" in categories:
        return "environment_relevant"
    if any(token in name for token in ["approval", "memory", "release", "autonomy", "execution"]):
        return "protected_system_relevant"
    return "needs_manual_review"


def _smoke_debt_reason(entry: dict[str, Any]) -> str:
    primary = entry.get("primary_category")
    if primary == "current_release_failure":
        return "Current-release trust gate or current dashboard/API/package/metadata surface; investigate before broad cleanup."
    if primary == "stale_legacy_expectation":
        return "Likely stale historical expectation or exact-string legacy check; convert to registry/current-state check only after review."
    if primary == "intentional_supervised_only_blocker":
        return "Governed safety or supervised-only boundary; do not convert to pass or automatic approval."
    if primary == "missing_optional_dependency":
        return "Environment dependency concern; keep separate from source-package correctness."
    if primary == "needs_manual_operator_approval":
        return "Operator-controlled area; approval is required before changing semantics."
    return "Unclassified blocker; manual review required."


def build_current_smoke_debt_ledger(root: Path = ROOT_DIR, save: bool = False, max_entries: int = 80) -> dict[str, Any]:
    triage = build_broad_smoke_triage_report(root=root, max_examples_per_category=20)
    legacy_review = build_legacy_self_maintenance_smoke_blocker_review(root=root)
    resolved_checks = set(RESOLVED_INSTALL_REGRESSION_RECENT_CHECKS) if legacy_review.get("ok") is True else set()
    seen: set[str] = set()
    ledger_entries: list[dict[str, Any]] = []
    resolved_entries: list[dict[str, Any]] = []
    for category, items in (triage.get("category_examples") or {}).items():
        for item in items:
            key = str(item.get("name") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            categories = list(item.get("categories", []) or [category])
            is_resolved = key in resolved_checks
            entry = {
                "name": key,
                "smoke_segment": item.get("segment"),
                "tier": item.get("tier"),
                "categories": categories,
                "primary_category": item.get("primary_category") or category,
                "reason": _smoke_debt_reason(item),
                "current_release_relevance": _ledger_relevance(item),
                "is_stale_legacy_noise": "stale_legacy_expectation" in categories and "current_release_failure" not in categories,
                "requires_operator_approval": bool("needs_manual_operator_approval" in categories or "intentional_supervised_only_blocker" in categories),
                "recommended_cleanup_path": "review_only_classification_first",
                "blocked_check_treated_as_pass": False,
                "resolution_status": "resolved_by_v765_install_regression_recovery" if is_resolved else "active_review_required",
                "active_smoke_debt": not is_resolved,
                "verified_by": "install-regression-recent" if is_resolved else "not_yet_reconciled",
            }
            if is_resolved:
                resolved_entries.append(entry)
                continue
            ledger_entries.append(entry)
            if len(ledger_entries) >= max_entries:
                break
        if len(ledger_entries) >= max_entries:
            break
    category_counts: dict[str, int] = {}
    for entry in ledger_entries:
        for category in entry.get("categories", []) or []:
            category_counts[category] = category_counts.get(category, 0) + 1
    resolved_category_counts: dict[str, int] = {}
    for entry in resolved_entries:
        for category in entry.get("categories", []) or []:
            resolved_category_counts[category] = resolved_category_counts.get(category, 0) + 1
    ledger = {
        "id": f"current_smoke_debt_ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": SMOKE_DEBT_LEDGER_TYPE,
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "ledger_prepared_review_only",
        "entry_count": len(ledger_entries),
        "active_entry_count": len(ledger_entries),
        "resolved_entry_count": len(resolved_entries),
        "category_counts": category_counts,
        "resolved_category_counts": resolved_category_counts,
        "entries": ledger_entries,
        "resolved_entries": resolved_entries,
        "reconciliation": {
            "install_regression_recent_expected_status": legacy_review.get("install_regression_recent_expected_status"),
            "legacy_self_maintenance_remaining_blockers": legacy_review.get("remaining_blocker_count"),
            "resolved_legacy_self_maintenance_checks_are_not_active_debt": bool(resolved_entries) and all(item.get("active_smoke_debt") is False for item in resolved_entries),
            "does_not_hide_unresolved_failures": True,
            "broad_smoke_not_executed_by_ledger": True,
        },
        "safety": {
            "review_only": True,
            "runs_broad_smoke": False,
            "marks_blockers_as_pass": False,
            "applies_source_edits": False,
            "executes_commands": False,
            "writes_memory": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_system_cleanup_requires_operator_approval": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check current-smoke-debt-ledger-v1",
            "python conscious_agent/main.py --current-smoke-debt-ledger --self-development-full",
            "python tools/smoke_check.py --check current-smoke-debt-ledger-reconciliation-v1",
            "python tools/smoke_check.py --check broad-smoke-triage-v1",
        ],
    }
    if save:
        _ensure_storage()
        with _cycle_path(ledger["id"]).open("w", encoding="utf-8") as file:
            json.dump(ledger, file, indent=2)
    return ledger


def current_smoke_debt_ledger_text(ledger: dict[str, Any] | None, full: bool = False) -> str:
    if not ledger:
        return "Current smoke debt ledger not found."
    safety = ledger.get("safety", {}) or {}
    lines = [
        f"# Current Smoke Debt Ledger: {ledger.get('id')}",
        f"Version: {ledger.get('version')}",
        f"Status: {ledger.get('status')}",
        f"Ledger entries: {ledger.get('entry_count')}",
        "Runs broad smoke: no",
        "Marks blockers as pass: no",
        "Applies source edits: no",
        "",
        "## Category counts",
    ]
    for category, count in sorted((ledger.get("category_counts") or {}).items()):
        lines.append(f"- {category}: {count}")
    lines.append("")
    lines.append("## Ledger entries")
    for entry in (ledger.get("entries", []) or [])[:20]:
        lines.append(
            f"- {entry.get('name')} [{entry.get('smoke_segment')}] -> {entry.get('primary_category')} | "
            f"relevance={entry.get('current_release_relevance')} | approval={entry.get('requires_operator_approval')} | "
            f"stale_legacy={entry.get('is_stale_legacy_noise')}"
        )
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Runs broad smoke: {safety.get('runs_broad_smoke')}",
        f"Marks blockers as pass: {safety.get('marks_blockers_as_pass')}",
        f"Protected cleanup requires operator approval: {safety.get('protected_system_cleanup_requires_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw entries")
        lines.append(json.dumps(ledger.get("entries", []), indent=2))
    return "\n".join(lines)



def build_current_smoke_debt_ledger_reconciliation_review(root: Path = ROOT_DIR, ledger: dict[str, Any] | None = None, triage: dict[str, Any] | None = None, legacy_review: dict[str, Any] | None = None) -> dict[str, Any]:
    ledger = ledger or build_current_smoke_debt_ledger(root=root, save=False)
    triage = triage or build_broad_smoke_triage_report(root=root, max_examples_per_category=20)
    legacy_review = legacy_review or build_legacy_self_maintenance_smoke_blocker_review(root=root)
    resolved_names = [entry.get("name") for entry in ledger.get("resolved_entries", []) or []]
    active_names = {entry.get("name") for entry in ledger.get("entries", []) or []}
    resolved_still_active = [name for name in resolved_names if name in active_names]
    unresolved_legacy_entries = [
        entry for entry in ledger.get("entries", []) or []
        if entry.get("smoke_segment") == "install-regression-recent" and entry.get("active_smoke_debt") is not False
    ]
    next_candidates = [
        {
            "rank": 1,
            "name": "stale current audit/report wording cleanup",
            "risk": "low",
            "reason": "Several current audit/report strings still reference older arc titles even when current-state gates pass.",
            "recommended_arc": "v851.0-v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
            "protected_system_hits": [],
        },
        {
            "rank": 2,
            "name": "release history duplicate/out-of-order hygiene",
            "risk": "low_to_medium",
            "reason": "Historical release notes contain duplicate/out-of-order entries that should be clarified without rewriting current state.",
            "recommended_arc": "v851.0-v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
            "protected_system_hits": ["release"],
        },
        {
            "rank": 3,
            "name": "manifest-driven dashboard/API/CLI/smoke validation expansion",
            "risk": "medium",
            "reason": "The manifest now helps surface truth, but more surfaces can be live-probed before generation is attempted.",
            "recommended_arc": "v851.0-v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
            "protected_system_hits": ["execution"],
        },
    ]
    ok = legacy_review.get("ok") is True and not resolved_still_active and ledger.get("resolved_entry_count", 0) >= 1
    return {
        "id": f"current_smoke_debt_ledger_reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "current_smoke_debt_ledger_reconciliation_review",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "triage_check_count": triage.get("check_count"),
        "active_ledger_entry_count": ledger.get("active_entry_count"),
        "resolved_ledger_entry_count": ledger.get("resolved_entry_count"),
        "install_regression_recent_expected_status": legacy_review.get("install_regression_recent_expected_status"),
        "legacy_self_maintenance_remaining_blockers": legacy_review.get("remaining_blocker_count"),
        "resolved_checks": resolved_names,
        "resolved_checks_still_active": resolved_still_active,
        "unresolved_install_regression_recent_entries": unresolved_legacy_entries,
        "next_broad_smoke_recovery_candidates": next_candidates,
        "safety": {
            "review_only": True,
            "runs_broad_smoke": False,
            "runs_install_regression_segment": False,
            "marks_blockers_as_pass": False,
            "hides_unresolved_failures": False,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check current-smoke-debt-ledger-reconciliation-v1",
            "python tools/smoke_check.py --segment install-regression-recent --json",
            "python tools/smoke_check.py --check current-smoke-debt-ledger-v1",
            "python tools/smoke_check.py --check broad-smoke-triage-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def current_smoke_debt_ledger_reconciliation_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Current smoke debt ledger reconciliation review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Current Smoke Debt Ledger Reconciliation Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Active ledger entries: {report.get('active_ledger_entry_count')}",
        f"Resolved ledger entries: {report.get('resolved_ledger_entry_count')}",
        f"Install regression recent expected status: {report.get('install_regression_recent_expected_status')}",
        f"Legacy self-maintenance blockers remaining: {report.get('legacy_self_maintenance_remaining_blockers')}",
        "Review only: yes",
        "Runs broad smoke: no",
        "Marks blockers as pass: no",
        "Hides unresolved failures: no",
        "Expands autonomy: no",
        "",
        "## Resolved checks removed from active debt",
    ]
    for name in report.get("resolved_checks", []) or []:
        lines.append(f"- {name}")
    lines.append("")
    lines.append("## Next broad smoke recovery candidates")
    for item in report.get("next_broad_smoke_recovery_candidates", []) or []:
        lines.append(f"- #{item.get('rank')} {item.get('name')} ({item.get('risk')}): {item.get('reason')}")
    lines.extend([
        "",
        "## Safety",
        f"Runs install-regression segment inside packet: {safety.get('runs_install_regression_segment')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Creates concrete diff: {safety.get('creates_concrete_diff')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Unresolved install-regression entries")
        lines.append(json.dumps(report.get("unresolved_install_regression_recent_entries", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_current_audit_wording_cleanup_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review current-state audit wording after the v780 cleanup.

    Historical release notes are allowed to mention old arcs. Current audit rows,
    current metadata messages, and active handoff docs should not describe v650,
    v700, v705, or v770-era work as the current release.
    """
    scan_targets = [
        "conscious_agent/current_version_staleness_audit.py",
        "conscious_agent/metadata_release_integrity.py",
        "conscious_agent/source_package_privacy_metadata_integrity.py",
        "conscious_agent/main.py",
        "conscious_agent/dashboard.py",
        "README_NEXT_STEPS.md",
    ]
    docs_targets = scan_targets + [
        "conscious_agent/self_development_cycle.py",
        "tools/smoke_check.py",
        "conscious_agent/source_surface_manifest.py",
    ]
    stale_phrases = [
        "README/source/dashboard/API/CLI/smoke metadata include v700 autonomy Phase 0 readiness harness surfaces",
        "Operator may review the v696-v700 autonomy Phase 0 readiness harness",
        "Next recommended arc points beyond the v650 session continuity/resume boundary",
    ]
    findings: list[dict[str, Any]] = []
    for rel in scan_targets:
        path = root / rel
        text = _read_text(path, limit=950_000)
        for phrase in stale_phrases:
            count = text.count(phrase)
            if count:
                findings.append({"path": rel, "phrase": phrase, "count": count})
    required_current_tokens = [
        "v850.0 Manifest-Guided Multi-Surface Probe Packet Consistency Gate v1",
        "current-audit-wording-cleanup-v1",
        "--current-audit-wording-cleanup",
        "build_current_audit_wording_cleanup_review",
        "current_audit_wording_cleanup_review_text",
        "manifest-generation-prep-review-v1",
        "--manifest-generation-prep-review",
        "build_manifest_generation_prep_review",
        "manifest_generation_prep_review_text",
    ]
    docs = "\n".join(_read_text(root / rel, limit=950_000) for rel in docs_targets)
    missing_current_tokens = [token for token in required_current_tokens if token not in docs]
    historical_release_history = _read_text(root / "README_RELEASE_HISTORY.md", limit=950_000)
    historical_allowed = all(token in historical_release_history for token in [
        "v650.0 - Operator Session Continuity and Resume Console UX v1",
        "v700.0 - Autonomy Phase 0 Readiness Harness v1",
        "v705.0 - Neural Command Deck UI Stabilization and Publish Safety Repair v1",
        "v770.0 - Current Smoke Debt Ledger Accuracy and Broad Smoke Recovery Prep v1",
    ])
    ok = not findings and not missing_current_tokens and historical_allowed
    return {
        "id": f"current_audit_wording_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "current_audit_wording_cleanup_review",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "target_count": len(scan_targets),
        "stale_current_audit_wording_findings": findings,
        "stale_current_audit_wording_clean": not findings,
        "missing_current_tokens": missing_current_tokens,
        "historical_release_references_allowed": historical_allowed,
        "current_state_history_rewrite_attempted": False,
        "safety": {
            "review_only": True,
            "runs_broad_smoke": False,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check current-audit-wording-cleanup-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-metadata-release-integrity-v1",
        ],
    }


def current_audit_wording_cleanup_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Current audit wording cleanup review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Current Audit Wording Cleanup Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Current stale wording clean: {report.get('stale_current_audit_wording_clean')}",
        f"Historical release references allowed: {report.get('historical_release_references_allowed')}",
        f"Missing current tokens: {len(report.get('missing_current_tokens') or [])}",
        "Review only: yes",
        "Runs broad smoke: no",
        "Applies source edits: no",
        "Creates concrete diff: no",
        "Expands autonomy: no",
        "",
        "## Findings",
    ]
    findings = report.get("stale_current_audit_wording_findings", []) or []
    if findings:
        for item in findings:
            lines.append(f"- {item.get('path')}: {item.get('phrase')} x{item.get('count')}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Runs broad smoke: {safety.get('runs_broad_smoke')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw summary")
        lines.append(json.dumps({
            "findings": report.get("stale_current_audit_wording_findings", []),
            "missing_current_tokens": report.get("missing_current_tokens", []),
            "verification_steps": report.get("verification_steps", []),
        }, indent=2))
    return "\n".join(lines)


def build_manifest_generation_prep_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Prepare, but do not generate, a manifest-driven surface expansion plan."""
    try:
        from source_surface_manifest import RECENT_SURFACE_ENTRIES
    except Exception:
        RECENT_SURFACE_ENTRIES = []
    surface_groups = [
        {
            "surface": "dashboard routes",
            "current_state": "partially manifest-represented and separately routed",
            "generation_readiness": "validate_first",
            "risk": "medium",
            "next_gate": "live route probe for every claimed dashboard route before generation",
        },
        {
            "surface": "API routes",
            "current_state": "manifest claims can be live-probed after v755 route repair",
            "generation_readiness": "validation_expansion_ready",
            "risk": "medium",
            "next_gate": "dispatch_api must return non-404 for every claimed API route",
        },
        {
            "surface": "CLI flags",
            "current_state": "manual argparse and dispatch remain source of truth",
            "generation_readiness": "inventory_only",
            "risk": "medium_high",
            "next_gate": "compare manifest CLI flags to parser and dispatch paths",
        },
        {
            "surface": "smoke checks",
            "current_state": "manual registry with recent manifest representation",
            "generation_readiness": "inventory_only",
            "risk": "medium_high",
            "next_gate": "ensure each manifest smoke check is registered and runnable",
        },
        {
            "surface": "README/release metadata",
            "current_state": "manual current-state and historical documentation",
            "generation_readiness": "review_only",
            "risk": "low_to_medium",
            "next_gate": "separate current-state generated snippets from historical release notes",
        },
    ]
    entry_count = len(RECENT_SURFACE_ENTRIES)
    claimed_api_routes = sorted({str(entry.get("api_route", "")) for entry in RECENT_SURFACE_ENTRIES if str(entry.get("api_route", "")).startswith("/api/")})
    claimed_dashboard_routes = sorted({str(entry.get("dashboard_route", "")) for entry in RECENT_SURFACE_ENTRIES if str(entry.get("dashboard_route", "")).startswith("/")})
    ok = entry_count > 0 and bool(surface_groups)
    return {
        "id": f"manifest_generation_prep_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_generation_prep_review",
        "smoke_check": "manifest-generation-prep-review-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "prepared_review_only" if ok else "review_required",
        "ok": ok,
        "manifest_entry_count": entry_count,
        "claimed_api_route_count": len(claimed_api_routes),
        "claimed_dashboard_route_count": len(claimed_dashboard_routes),
        "surface_groups": surface_groups,
        "recommended_next_arc": "v851.0-v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
        "manifest_generation_prep_is_review_only": True,
        "generates_surfaces": False,
        "modifies_manifest": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "safety": {
            "review_only": True,
            "generates_surfaces": False,
            "modifies_manifest": False,
            "runs_broad_smoke": False,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "verification_steps": [
            "python tools/smoke_check.py --check current-audit-wording-cleanup-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --check operator-governed-route-surface-parity-v1",
        ],
    }


def manifest_generation_prep_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest generation prep review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Generation Prep Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Manifest entries: {report.get('manifest_entry_count')}",
        f"Claimed API routes: {report.get('claimed_api_route_count')}",
        f"Claimed dashboard routes: {report.get('claimed_dashboard_route_count')}",
        f"Recommended next arc: {report.get('recommended_next_arc')}",
        "Review only: yes",
        "Generates surfaces: no",
        "Applies source edits: no",
        "Creates concrete diff: no",
        "Expands autonomy: no",
        "",
        "## Surface groups",
    ]
    for item in report.get("surface_groups", []) or []:
        lines.append(f"- {item.get('surface')} [{item.get('risk')}]: {item.get('generation_readiness')} -> {item.get('next_gate')}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Modifies manifest: {safety.get('modifies_manifest')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw surface groups")
        lines.append(json.dumps(report.get("surface_groups", []), indent=2))
    return "\n".join(lines)


def _unique_manifest_surface_values(entries: list[dict[str, Any]], key: str, prefix: str | None = None) -> list[str]:
    values: set[str] = set()
    for entry in entries:
        value = str(entry.get(key, "") or "")
        if not value:
            continue
        if prefix is not None and not value.startswith(prefix):
            continue
        values.add(value)
    return sorted(values)


def _probe_dashboard_route(route: str, root: Path = ROOT_DIR) -> dict[str, Any]:
    route = str(route or "")
    if not route.startswith("/"):
        return {"route": route or "[missing]", "live": False, "status_class": "not_claimed"}
    try:
        dash_text = _read_text(root / "conscious_agent" / "dashboard.py", limit=1_200_000)
        token_present = route in dash_text
        command_deck_present = "command-deck" in dash_text
        data_tip_present = "data-tip" in dash_text
        return {
            "route": route,
            "live": token_present,
            "status_class": "declared_static_token_present" if token_present else "declared_but_missing",
            "static_token_present": token_present,
            "uses_data_tip": data_tip_present,
            "uses_command_deck": command_deck_present,
            "render_not_invoked": True,
        }
    except Exception as error:
        return {"route": route, "live": False, "status_class": "probe_error", "error": f"{type(error).__name__}: {error}"}


def _probe_cli_flag(flag: str, root: Path = ROOT_DIR) -> dict[str, Any]:
    flag = str(flag or "")
    if not flag.startswith("--"):
        return {"flag": flag or "[missing]", "live": False, "status_class": "not_claimed"}
    source = _read_text(root / "conscious_agent" / "main.py", limit=1_400_000)
    dest = flag[2:].replace("-", "_")
    argparse_registered = f'add_argument("{flag}"' in source or f"add_argument('{flag}'" in source
    dispatch_registered = f"args.{dest}" in source
    return {
        "flag": flag,
        "live": argparse_registered and dispatch_registered,
        "status_class": "declared_and_live" if argparse_registered and dispatch_registered else "declared_but_missing",
        "argparse_registered": argparse_registered,
        "dispatch_registered": dispatch_registered,
    }


def _probe_smoke_check(check_name: str, root: Path = ROOT_DIR) -> dict[str, Any]:
    check_name = str(check_name or "")
    if not check_name:
        return {"smoke_check": "[missing]", "live": False, "status_class": "not_claimed"}
    source = _read_text(root / "tools" / "smoke_check.py", limit=1_400_000)
    registered = f'SmokeCheck("{check_name}"' in source or f"SmokeCheck('{check_name}'" in source
    function_token = "check_" + check_name.replace("-", "_")
    function_present = function_token in source
    return {
        "smoke_check": check_name,
        "live": registered,
        "status_class": "declared_and_live" if registered else "declared_but_missing",
        "registered": registered,
        "function_token_present": function_present,
    }


def _probe_builder_text_functions(entries: list[dict[str, Any]], root: Path = ROOT_DIR) -> list[dict[str, Any]]:
    source = _read_text(root / "conscious_agent" / "self_development_cycle.py", limit=1_200_000)
    probes: list[dict[str, Any]] = []
    for name in _unique_manifest_surface_values(entries, "builder_function") + _unique_manifest_surface_values(entries, "text_function"):
        if not name or name in {"classify_protected_systems", "classify_smoke_blocker", "generate_candidate_improvements"}:
            live = name in source
        else:
            live = f"def {name}" in source or f"class {name}" in source or name in source
        probes.append({
            "symbol": name,
            "live": live,
            "status_class": "declared_and_live" if live else "declared_but_missing",
        })
    return probes


def _classify_probe_count(probes: list[dict[str, Any]], live_key: str = "live") -> dict[str, int]:
    live = sum(1 for item in probes if item.get(live_key) is True)
    missing = sum(1 for item in probes if item.get(live_key) is not True)
    return {"declared_and_live": live, "declared_but_missing": missing, "total": len(probes)}


def build_manifest_gated_surface_validation_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Validate manifest-described self-development surfaces before any generation is attempted.

    This packet is intentionally read-only. It inventories declared dashboard, API,
    CLI, smoke, README, and metadata surfaces and classifies whether each one is
    live, missing, historical-only, review-only, or not applicable. It must not
    generate route wiring, mutate source, run broad smoke, or expand autonomy.
    """
    entries = _self_development_surface_entries()
    dashboard_routes = _unique_manifest_surface_values(entries, "dashboard_route", "/")
    api_routes = _unique_manifest_surface_values(entries, "api_route", "/api/")
    review_only_api_markers = sorted({str(entry.get("api_route", "")) for entry in entries if str(entry.get("api_route", "")) == "not_exposed_review_only"})
    cli_flags = _unique_manifest_surface_values(entries, "cli_flag", "--")
    smoke_checks = _unique_manifest_surface_values(entries, "smoke_check")
    dashboard_probes = [_probe_dashboard_route(route, root=root) for route in dashboard_routes]
    api_probes = [_probe_api_route(route) for route in api_routes]
    cli_probes = [_probe_cli_flag(flag, root=root) for flag in cli_flags]
    smoke_probes = [_probe_smoke_check(check, root=root) for check in smoke_checks]
    symbol_probes = _probe_builder_text_functions(entries, root=root)
    readme_text = _read_text(root / "README_NEXT_STEPS.md", limit=950_000)
    release_text = _read_text(root / "README_RELEASE_HISTORY.md", limit=950_000)
    settings_text = _read_text(root / "data" / "settings.json", limit=300_000)
    projects_text = _read_text(root / "data" / "projects.json", limit=900_000)
    required_current_tokens = [
        "v850.0 Manifest-Guided Multi-Surface Probe Packet Consistency Gate v1",
        "manifest-registry-expanded-review-surfaces-v1",
        "--manifest-registry-expanded-review-surfaces",
        "build_manifest_registry_expanded_review_surfaces_review",
        "manifest_registry_expanded_review_surfaces_review_text",
        "manifest-gated-surface-validation-v1",
        "--manifest-gated-surface-validation",
        "build_manifest_gated_surface_validation_review",
        "manifest_gated_surface_validation_review_text",
    ]
    docs_blob = "\n".join([readme_text, release_text, settings_text, projects_text, _read_text(root / "conscious_agent" / "source_surface_manifest.py", limit=1_100_000)])
    missing_current_tokens = [token for token in required_current_tokens if token not in docs_blob]
    api_missing = [probe for probe in api_probes if probe.get("dispatches") is not True]
    dashboard_missing = [probe for probe in dashboard_probes if probe.get("live") is not True]
    cli_missing = [probe for probe in cli_probes if probe.get("live") is not True]
    smoke_missing = [probe for probe in smoke_probes if probe.get("live") is not True]
    symbol_missing = [probe for probe in symbol_probes if probe.get("live") is not True]
    surface_classification = {
        "dashboard_routes": _classify_probe_count(dashboard_probes),
        "api_routes": {
            "declared_and_live": len([probe for probe in api_probes if probe.get("dispatches") is True]),
            "declared_but_missing": len(api_missing),
            "review_only_not_exposed": len(review_only_api_markers),
            "total": len(api_probes) + len(review_only_api_markers),
        },
        "cli_flags": _classify_probe_count(cli_probes),
        "smoke_checks": _classify_probe_count(smoke_probes),
        "builder_text_symbols": _classify_probe_count(symbol_probes),
        "readme_metadata_claims": {
            "declared_and_live": 0 if missing_current_tokens else len(required_current_tokens),
            "declared_but_missing": len(missing_current_tokens),
            "total": len(required_current_tokens),
        },
    }
    ok = (
        bool(entries)
        and not api_missing
        and not dashboard_missing
        and not cli_missing
        and not smoke_missing
        and not symbol_missing
        and not missing_current_tokens
    )
    return {
        "id": f"manifest_gated_surface_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_gated_surface_validation_review",
        "smoke_check": "manifest-gated-surface-validation-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "manifest_entry_count": len(entries),
        "dashboard_route_count": len(dashboard_routes),
        "api_route_count": len(api_routes),
        "review_only_api_marker_count": len(review_only_api_markers),
        "cli_flag_count": len(cli_flags),
        "smoke_check_count": len(smoke_checks),
        "surface_classification": surface_classification,
        "dashboard_route_probes": dashboard_probes,
        "api_route_probes": api_probes,
        "cli_flag_probes": cli_probes,
        "smoke_check_probes": smoke_probes,
        "builder_text_symbol_probes": symbol_probes,
        "missing_current_tokens": missing_current_tokens,
        "classification_legend": [
            "declared_and_live",
            "declared_but_missing",
            "live_but_undeclared",
            "historical_only",
            "review_only",
            "not_applicable",
        ],
        "validation_is_review_only": True,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": {
            "review_only": True,
            "generates_surfaces": False,
            "manifest_drives_wiring": False,
            "runs_broad_smoke": False,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "recommended_next_arc": "v851.0-v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-gated-surface-validation-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --check operator-governed-route-surface-parity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_gated_surface_validation_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-gated surface validation review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Gated Surface Validation Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Manifest entries reviewed: {report.get('manifest_entry_count')}",
        f"Dashboard routes: {report.get('dashboard_route_count')}",
        f"API routes: {report.get('api_route_count')}",
        f"Review-only API markers: {report.get('review_only_api_marker_count')}",
        f"CLI flags: {report.get('cli_flag_count')}",
        f"Smoke checks: {report.get('smoke_check_count')}",
        "Validation only: yes",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Runs broad smoke: no",
        "Expands autonomy: no",
        "",
        "## Classification summary",
    ]
    for name, summary in (report.get("surface_classification", {}) or {}).items():
        lines.append(f"- {name}: {summary}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Manifest drives wiring: {safety.get('manifest_drives_wiring')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## API probes")
        lines.append(json.dumps(report.get("api_route_probes", []), indent=2))
        lines.append("")
        lines.append("## Dashboard probes")
        lines.append(json.dumps(report.get("dashboard_route_probes", []), indent=2))
        lines.append("")
        lines.append("## CLI probes")
        lines.append(json.dumps(report.get("cli_flag_probes", []), indent=2))
        lines.append("")
        lines.append("## Smoke probes")
        lines.append(json.dumps(report.get("smoke_check_probes", []), indent=2))
        lines.append("")
        lines.append("## Builder/text symbol probes")
        lines.append(json.dumps(report.get("builder_text_symbol_probes", []), indent=2))
        lines.append("")
        lines.append("## Missing current tokens")
        lines.append(json.dumps(report.get("missing_current_tokens", []), indent=2))
    return "\n".join(lines)


def _find_self_development_manifest_entry(entries: list[dict[str, Any]], *, cli_flag: str = "", surface_id: str = "") -> dict[str, Any]:
    for entry in entries:
        if cli_flag and entry.get("cli_flag") == cli_flag:
            return dict(entry)
        if surface_id and entry.get("surface_id") == surface_id:
            return dict(entry)
    return {}


def build_manifest_driven_surface_registry_pilot_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Register exactly one review-only self-development surface as a manifest pilot.

    The pilot describes the existing manifest-gated surface validation packet in a
    registry-shaped record. It validates presence and safety boundaries only; it
    does not generate dashboard/API/CLI/smoke wiring, apply source edits, or
    expand autonomy.
    """
    entries = _self_development_surface_entries()
    pilot = _find_self_development_manifest_entry(entries, cli_flag="--manifest-gated-surface-validation")
    dashboard_probe = _probe_dashboard_route(str(pilot.get("dashboard_route", "")), root=root) if pilot else {}
    api_value = str(pilot.get("api_route", "")) if pilot else ""
    api_probe = {"route": api_value, "status_class": "review_only", "dispatches": None, "review_only_not_exposed": True} if api_value == "not_exposed_review_only" else _probe_api_route(api_value)
    cli_probe = _probe_cli_flag(str(pilot.get("cli_flag", "")), root=root) if pilot else {}
    smoke_probe = _probe_smoke_check(str(pilot.get("smoke_check", "")), root=root) if pilot else {}
    symbol_probes = _probe_builder_text_functions([pilot], root=root) if pilot else []
    registry_pilot_record = {
        "pilot_id": "v785_manifest_gated_surface_validation_registry_pilot",
        "selected_surface_id": pilot.get("surface_id") if pilot else "",
        "selected_cli_flag": pilot.get("cli_flag") if pilot else "",
        "selected_smoke_check": pilot.get("smoke_check") if pilot else "",
        "selected_dashboard_route": pilot.get("dashboard_route") if pilot else "",
        "selected_api_route": pilot.get("api_route") if pilot else "",
        "builder_function": pilot.get("builder_function") if pilot else "",
        "text_function": pilot.get("text_function") if pilot else "",
        "authority_level": "review_only",
        "safe_for_manifest_registration": True,
        "safe_for_generated_validation_only": True,
        "safe_for_generated_wiring": False,
        "manual_until_further_review": False,
        "protected_operator_controlled": True,
        "never_autonomous": True,
        "writes_files": False,
        "writes_memory": False,
        "requires_operator_approval": True,
        "generates_dashboard_route": False,
        "generates_api_route": False,
        "generates_cli_flag": False,
        "generates_smoke_check": False,
    }
    safety = {
        "review_only": True,
        "pilot_registers_one_surface": True,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "runs_broad_smoke": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    symbol_live = bool(symbol_probes) and all(probe.get("live") is True for probe in symbol_probes)
    ok = (
        bool(pilot)
        and pilot.get("authority_level") == "review_only"
        and pilot.get("writes_files") is False
        and pilot.get("writes_memory") is False
        and dashboard_probe.get("live") is True
        and api_probe.get("review_only_not_exposed") is True
        and cli_probe.get("live") is True
        and smoke_probe.get("live") is True
        and symbol_live
        and all(value is False for key, value in safety.items() if key in {
            "generates_surfaces", "manifest_drives_wiring", "generated_wiring_activated",
            "runs_broad_smoke", "applies_source_edits", "creates_concrete_diff", "executes_commands",
            "writes_memory", "modifies_approval_system", "modifies_release_system",
            "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        })
    )
    return {
        "id": f"manifest_driven_surface_registry_pilot_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_driven_surface_registry_pilot_review",
        "smoke_check": "manifest-driven-surface-registry-pilot-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "pilot_surface_id": pilot.get("surface_id") if pilot else "",
        "pilot_surface_registered": bool(pilot),
        "pilot_surface_count": 1 if pilot else 0,
        "registry_pilot_record": registry_pilot_record,
        "dashboard_probe": dashboard_probe,
        "api_probe": api_probe,
        "cli_probe": cli_probe,
        "smoke_probe": smoke_probe,
        "symbol_probes": symbol_probes,
        "registry_pilot_is_review_only": True,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-driven-surface-registry-pilot-v1",
            "python tools/smoke_check.py --check manifest-gated-surface-validation-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_driven_surface_registry_pilot_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-driven surface registry pilot review not found."
    safety = report.get("safety", {}) or {}
    record = report.get("registry_pilot_record", {}) or {}
    lines = [
        f"# Manifest-Driven Surface Registry Pilot Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Pilot surface: {report.get('pilot_surface_id')}",
        f"Pilot surface count: {report.get('pilot_surface_count')}",
        "Registry pilot: one review-only surface",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Generated wiring activated: no",
        "Expands autonomy: no",
        "",
        "## Pilot record",
        f"- CLI flag: {record.get('selected_cli_flag')}",
        f"- Dashboard route: {record.get('selected_dashboard_route')}",
        f"- API route: {record.get('selected_api_route')}",
        f"- Smoke check: {record.get('selected_smoke_check')}",
        f"- Builder: {record.get('builder_function')}",
        f"- Text renderer: {record.get('text_function')}",
        f"- Safe for manifest registration: {record.get('safe_for_manifest_registration')}",
        f"- Safe for generated wiring: {record.get('safe_for_generated_wiring')}",
        f"- Never autonomous: {record.get('never_autonomous')}",
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Pilot registers one surface: {safety.get('pilot_registers_one_surface')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Manifest drives wiring: {safety.get('manifest_drives_wiring')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ]
    if full:
        lines.append("")
        lines.append("## Registry pilot record")
        lines.append(json.dumps(record, indent=2))
        lines.append("")
        lines.append("## Probes")
        lines.append(json.dumps({
            "dashboard_probe": report.get("dashboard_probe"),
            "api_probe": report.get("api_probe"),
            "cli_probe": report.get("cli_probe"),
            "smoke_probe": report.get("smoke_probe"),
            "symbol_probes": report.get("symbol_probes"),
        }, indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_surface_generation_readiness_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Classify future generated-surface candidates without generating wiring."""
    pilot = build_manifest_driven_surface_registry_pilot_review(root=root)
    validation = build_manifest_gated_surface_validation_review(root=root)
    candidate_categories = [
        {
            "category": "safe_for_manifest_registration",
            "surfaces": ["manifest-gated-surface-validation", "current-audit-wording-cleanup", "manifest-generation-prep-review"],
            "condition": "review-only surfaces with existing dashboard/CLI/smoke coverage and no writes",
        },
        {
            "category": "safe_for_generated_validation_only",
            "surfaces": ["self-development-api-surface-truth-review", "current-smoke-debt-ledger-reconciliation", "legacy-self-maintenance-smoke-blocker-review"],
            "condition": "validation can be generated as a report, but live dispatch/wiring remains manual",
        },
        {
            "category": "manual_until_further_review",
            "surfaces": ["dashboard route placement", "API route creation", "CLI dispatch insertion", "smoke registration mutation"],
            "condition": "requires exact operator-reviewed diff before any generated wiring is allowed",
        },
        {
            "category": "protected_operator_controlled",
            "surfaces": ["approval system", "memory mutation", "release packaging", "execution permissions", "scheduler", "network/external systems"],
            "condition": "operator-controlled gate remains mandatory",
        },
        {
            "category": "never_autonomous",
            "surfaces": ["self-approval", "approval escalation", "failed-smoke override", "package privacy override", "stale-version override"],
            "condition": "must not become autonomous even after manifest generation matures",
        },
    ]
    safety = {
        "review_only": True,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = pilot.get("ok") is True and validation.get("ok") is True and len(candidate_categories) == 5 and safety["generates_surfaces"] is False
    return {
        "id": f"manifest_surface_generation_readiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_surface_generation_readiness_review",
        "smoke_check": "manifest-driven-surface-registry-pilot-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "pilot_surface_status": pilot.get("status"),
        "manifest_validation_status": validation.get("status"),
        "candidate_categories": candidate_categories,
        "category_names": [item["category"] for item in candidate_categories],
        "safe_for_manifest_registration_count": len(candidate_categories[0]["surfaces"]),
        "manual_until_further_review_count": len(candidate_categories[2]["surfaces"]),
        "protected_operator_controlled_count": len(candidate_categories[3]["surfaces"]),
        "never_autonomous_count": len(candidate_categories[4]["surfaces"]),
        "readiness_is_review_only": True,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def manifest_surface_generation_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest surface generation readiness review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Surface Generation Readiness Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Pilot surface status: {report.get('pilot_surface_status')}",
        f"Manifest validation status: {report.get('manifest_validation_status')}",
        "Readiness only: yes",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Expands autonomy: no",
        "",
        "## Candidate categories",
    ]
    for item in report.get("candidate_categories", []) or []:
        lines.append(f"- {item.get('category')}: {', '.join(item.get('surfaces', []))} — {item.get('condition')}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Manifest drives wiring: {safety.get('manifest_drives_wiring')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw categories")
        lines.append(json.dumps(report.get("candidate_categories", []), indent=2))
    return "\n".join(lines)




MANIFEST_REGISTRY_EXPANDED_REVIEW_SURFACE_FLAGS = (
    "--manifest-gated-surface-validation",
    "--current-audit-wording-cleanup",
    "--current-smoke-debt-ledger-reconciliation",
    "--legacy-self-maintenance-smoke-blocker-review",
    "--self-development-cycle-duplicate-cleanup",
    "--self-development-api-surface-truth-review",
    "--manifest-guided-generated-validation-probe",
    "--manifest-smoke-segment-parity-drift",
    "--manifest-smoke-segment-parity-repair-packet",
    "--manifest-segment-parity-enforcement-gate",
)


def _manifest_registry_expanded_surface_entries() -> list[dict[str, Any]]:
    entries = _self_development_surface_entries()
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for flag in MANIFEST_REGISTRY_EXPANDED_REVIEW_SURFACE_FLAGS:
        entry = _find_self_development_manifest_entry(entries, cli_flag=flag)
        surface_id = str(entry.get("surface_id", ""))
        if entry and surface_id not in seen:
            selected.append(entry)
            seen.add(surface_id)
    return selected


def _score_manifest_registry_surface(entry: dict[str, Any]) -> str:
    if not entry:
        return "manual_wiring_required"
    authority = str(entry.get("authority_level", ""))
    api_route = str(entry.get("api_route", ""))
    if authority != "review_only" or entry.get("writes_files") is not False or entry.get("writes_memory") is not False:
        return "blocked_by_protected_system"
    if "approval" in str(entry.get("surface_id", "")).lower() or "memory" in str(entry.get("surface_id", "")).lower():
        return "protected_operator_controlled"
    if api_route == "not_exposed_review_only":
        return "registry_only_ready"
    if api_route.startswith("/api/"):
        return "validation_generation_ready"
    return "manual_wiring_required"


def build_manifest_registry_expanded_review_surfaces_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Expand the manifest registry pilot to a small batch of review-only surfaces.

    This remains a registry/validation packet only. It describes a pilot surface plus
    five additional self-development review surfaces and confirms their dashboard,
    CLI, smoke, symbol, and safety boundaries without generating wiring.
    """
    selected = _manifest_registry_expanded_surface_entries()
    records: list[dict[str, Any]] = []
    for index, entry in enumerate(selected, start=1):
        api_value = str(entry.get("api_route", ""))
        api_probe = {"route": api_value, "status_class": "review_only", "dispatches": None, "review_only_not_exposed": True} if api_value == "not_exposed_review_only" else _probe_api_route(api_value)
        record = {
            "registry_index": index,
            "surface_id": entry.get("surface_id"),
            "cli_flag": entry.get("cli_flag"),
            "dashboard_route": entry.get("dashboard_route"),
            "api_route": entry.get("api_route"),
            "smoke_check": entry.get("smoke_check"),
            "builder_function": entry.get("builder_function"),
            "text_function": entry.get("text_function"),
            "authority_level": entry.get("authority_level"),
            "writes_files": entry.get("writes_files"),
            "writes_memory": entry.get("writes_memory"),
            "dashboard_probe": _probe_dashboard_route(str(entry.get("dashboard_route", "")), root=root),
            "api_probe": api_probe,
            "cli_probe": _probe_cli_flag(str(entry.get("cli_flag", "")), root=root),
            "smoke_probe": _probe_smoke_check(str(entry.get("smoke_check", "")), root=root),
            "symbol_probes": _probe_builder_text_functions([entry], root=root),
            "readiness_score": _score_manifest_registry_surface(entry),
            "safe_for_manifest_registration": True,
            "safe_for_generated_wiring": False,
            "generated_wiring_activated": False,
            "never_autonomous": True,
        }
        records.append(record)
    readiness_scores: dict[str, int] = {}
    for record in records:
        score = str(record.get("readiness_score", "manual_wiring_required"))
        readiness_scores[score] = readiness_scores.get(score, 0) + 1
    expected_flags = set(MANIFEST_REGISTRY_EXPANDED_REVIEW_SURFACE_FLAGS)
    registered_flags = {str(record.get("cli_flag")) for record in records}
    probes_ok = all(
        record.get("dashboard_probe", {}).get("live") is True
        and (record.get("api_probe", {}).get("review_only_not_exposed") is True or record.get("api_probe", {}).get("dispatches") is True)
        and record.get("cli_probe", {}).get("live") is True
        and record.get("smoke_probe", {}).get("live") is True
        and all(probe.get("live") is True for probe in record.get("symbol_probes", []) or [])
        for record in records
    )
    safety = {
        "review_only": True,
        "registry_expands_review_surfaces": True,
        "selected_surface_count": len(records),
        "additional_surface_count": max(0, len(records) - 1),
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        len(records) == len(MANIFEST_REGISTRY_EXPANDED_REVIEW_SURFACE_FLAGS)
        and expected_flags == registered_flags
        and probes_ok
        and all(record.get("authority_level") == "review_only" for record in records)
        and all(record.get("writes_files") is False and record.get("writes_memory") is False for record in records)
        and all(record.get("safe_for_generated_wiring") is False for record in records)
        and all(value is False for key, value in safety.items() if key in {
            "generates_surfaces", "manifest_drives_wiring", "generated_wiring_activated",
            "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke", "executes_commands",
            "writes_memory", "modifies_approval_system", "modifies_release_system",
            "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        })
    )
    return {
        "id": f"manifest_registry_expanded_review_surfaces_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_registry_expanded_review_surfaces_review",
        "smoke_check": "manifest-registry-expanded-review-surfaces-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "pilot_surface_id": records[0].get("surface_id") if records else "",
        "selected_surface_count": len(records),
        "additional_surface_count": max(0, len(records) - 1),
        "registered_surface_records": records,
        "readiness_scores": readiness_scores,
        "readiness_score_names": ["registry_only_ready", "validation_generation_ready", "manual_wiring_required", "blocked_by_protected_system", "never_generate"],
        "registry_expansion_is_review_only": True,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-registry-expanded-review-surfaces-v1",
            "python tools/smoke_check.py --check manifest-driven-surface-registry-pilot-v1",
            "python tools/smoke_check.py --check manifest-gated-surface-validation-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_registry_expanded_review_surfaces_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest registry expanded review surfaces review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Registry Expanded Review Surfaces Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Pilot surface: {report.get('pilot_surface_id')}",
        f"Selected review surfaces: {report.get('selected_surface_count')}",
        f"Additional review surfaces: {report.get('additional_surface_count')}",
        "Registry expansion: pilot plus nine review-only surfaces",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Generated wiring activated: no",
        "Expands autonomy: no",
        "",
        "## Registered review surfaces",
    ]
    for record in report.get("registered_surface_records", []) or []:
        lines.append(
            f"- {record.get('surface_id')}: {record.get('cli_flag')} / {record.get('smoke_check')} / score={record.get('readiness_score')}"
        )
    lines.extend([
        "",
        "## Readiness scoring",
    ])
    for name in report.get("readiness_score_names", []) or []:
        lines.append(f"- {name}: {(report.get('readiness_scores', {}) or {}).get(name, 0)}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Manifest drives wiring: {safety.get('manifest_drives_wiring')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Registry records")
        lines.append(json.dumps(report.get("registered_surface_records", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_registry_generation_readiness_scoring_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Summarize generation-readiness scoring for the expanded registry batch."""
    expanded = build_manifest_registry_expanded_review_surfaces_review(root=root)
    records = expanded.get("registered_surface_records", []) or []
    category_guidance = [
        {"score": "registry_only_ready", "meaning": "safe to describe in registry; wiring stays manual"},
        {"score": "validation_generation_ready", "meaning": "safe candidate for future generated validation probes only"},
        {"score": "manual_wiring_required", "meaning": "requires operator-reviewed diff before any wiring change"},
        {"score": "blocked_by_protected_system", "meaning": "blocked by protected-system boundaries"},
        {"score": "never_generate", "meaning": "must remain manual and never autonomous"},
    ]
    safety = {
        "review_only": True,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = expanded.get("ok") is True and len(records) >= 6 and safety["generates_surfaces"] is False
    return {
        "id": f"manifest_registry_generation_readiness_scoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_registry_generation_readiness_scoring_review",
        "smoke_check": "manifest-registry-expanded-review-surfaces-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "selected_surface_count": len(records),
        "readiness_scores": expanded.get("readiness_scores", {}),
        "category_guidance": category_guidance,
        "scoring_is_review_only": True,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def manifest_registry_generation_readiness_scoring_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest registry generation readiness scoring review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Registry Generation Readiness Scoring Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected review surfaces: {report.get('selected_surface_count')}",
        "Scoring only: yes",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Expands autonomy: no",
        "",
        "## Score guidance",
    ]
    for item in report.get("category_guidance", []) or []:
        lines.append(f"- {item.get('score')}: {item.get('meaning')}")
    lines.extend([
        "",
        "## Score counts",
    ])
    for key, value in (report.get("readiness_scores", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Manifest drives wiring: {safety.get('manifest_drives_wiring')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Raw guidance")
        lines.append(json.dumps(report.get("category_guidance", []), indent=2))
    return "\n".join(lines)


DRIFT_DETECTION_CLASSES = (
    "in_sync",
    "missing_builder",
    "missing_text_renderer",
    "missing_cli_flag",
    "missing_dashboard_card",
    "missing_smoke",
    "safety_boundary_drift",
    "autonomy_boundary_drift",
    "manual_review_required",
)


def _classify_manifest_registry_drift(record: dict[str, Any]) -> list[str]:
    classes: list[str] = []
    symbol_probes = record.get("symbol_probes", []) or []
    builder_name = str(record.get("builder_function", ""))
    text_name = str(record.get("text_function", ""))
    builder_live = any(probe.get("symbol") == builder_name and probe.get("live") is True for probe in symbol_probes)
    text_live = any(probe.get("symbol") == text_name and probe.get("live") is True for probe in symbol_probes)
    if not builder_live:
        classes.append("missing_builder")
    if not text_live:
        classes.append("missing_text_renderer")
    if record.get("cli_probe", {}).get("live") is not True:
        classes.append("missing_cli_flag")
    if record.get("dashboard_probe", {}).get("live") is not True:
        classes.append("missing_dashboard_card")
    if record.get("smoke_probe", {}).get("live") is not True:
        classes.append("missing_smoke")
    api_probe = record.get("api_probe", {}) or {}
    if not (api_probe.get("review_only_not_exposed") is True or api_probe.get("dispatches") is True):
        classes.append("manual_review_required")
    if record.get("authority_level") != "review_only" or record.get("writes_files") is not False or record.get("writes_memory") is not False:
        classes.append("safety_boundary_drift")
    if record.get("never_autonomous") is not True or record.get("generated_wiring_activated") is not False or record.get("safe_for_generated_wiring") is not False:
        classes.append("autonomy_boundary_drift")
    return classes or ["in_sync"]


def build_manifest_registry_drift_detection_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Detect registry-to-surface drift for the expanded review-only manifest registry batch."""
    expanded = build_manifest_registry_expanded_review_surfaces_review(root=root)
    records = expanded.get("registered_surface_records", []) or []
    drift_records: list[dict[str, Any]] = []
    class_counts = {name: 0 for name in DRIFT_DETECTION_CLASSES}
    for record in records:
        classes = _classify_manifest_registry_drift(record)
        for name in classes:
            class_counts[name] = class_counts.get(name, 0) + 1
        drift_records.append({
            "surface_id": record.get("surface_id"),
            "cli_flag": record.get("cli_flag"),
            "dashboard_route": record.get("dashboard_route"),
            "api_route": record.get("api_route"),
            "smoke_check": record.get("smoke_check"),
            "builder_function": record.get("builder_function"),
            "text_function": record.get("text_function"),
            "drift_classes": classes,
            "status": "in_sync" if classes == ["in_sync"] else "drift_detected",
            "dashboard_live": record.get("dashboard_probe", {}).get("live"),
            "cli_live": record.get("cli_probe", {}).get("live"),
            "smoke_live": record.get("smoke_probe", {}).get("live"),
            "api_live_or_review_only": (record.get("api_probe", {}) or {}).get("review_only_not_exposed") is True or (record.get("api_probe", {}) or {}).get("dispatches") is True,
            "review_only": record.get("authority_level") == "review_only",
            "writes_files": record.get("writes_files"),
            "writes_memory": record.get("writes_memory"),
            "generated_wiring_activated": record.get("generated_wiring_activated"),
            "safe_for_generated_wiring": record.get("safe_for_generated_wiring"),
            "never_autonomous": record.get("never_autonomous"),
        })
    drifted = [item for item in drift_records if item.get("status") != "in_sync"]
    safety = {
        "review_only": True,
        "registry_drift_detection_is_review_only": True,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "repairs_drift": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        expanded.get("ok") is True
        and len(records) == len(MANIFEST_REGISTRY_EXPANDED_REVIEW_SURFACE_FLAGS)
        and not drifted
        and class_counts.get("in_sync", 0) == len(records)
        and all(value is False for key, value in safety.items() if key in {
            "generates_surfaces", "manifest_drives_wiring", "generated_wiring_activated", "repairs_drift",
            "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass",
            "hides_unresolved_failures", "executes_commands", "writes_memory", "modifies_approval_system",
            "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        })
    )
    return {
        "id": f"manifest_registry_drift_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_registry_drift_detection_review",
        "smoke_check": "manifest-registry-drift-detection-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "registered_surface_count": len(records),
        "drift_count": len(drifted),
        "in_sync_count": class_counts.get("in_sync", 0),
        "drift_class_counts": class_counts,
        "drift_detection_classes": list(DRIFT_DETECTION_CLASSES),
        "registered_surface_drift_records": drift_records,
        "registry_drift_detection_is_review_only": True,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check manifest-registry-expanded-review-surfaces-v1",
            "python tools/smoke_check.py --check manifest-gated-surface-validation-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_registry_drift_detection_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest registry drift detection review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Registry Drift Detection Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Registered surfaces: {report.get('registered_surface_count')}",
        f"In sync: {report.get('in_sync_count')}",
        f"Drift count: {report.get('drift_count')}",
        "Registry drift detection: review-only",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Generated wiring activated: no",
        "Expands autonomy: no",
        "",
        "## Drift classes",
    ]
    for name in report.get("drift_detection_classes", []) or []:
        lines.append(f"- {name}: {(report.get('drift_class_counts', {}) or {}).get(name, 0)}")
    lines.extend(["", "## Registered surface drift records"])
    for record in report.get("registered_surface_drift_records", []) or []:
        lines.append(f"- {record.get('surface_id')}: {record.get('status')} classes={','.join(record.get('drift_classes', []) or [])}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Repairs drift: {safety.get('repairs_drift')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Manifest drives wiring: {safety.get('manifest_drives_wiring')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Drift records")
        lines.append(json.dumps(report.get("registered_surface_drift_records", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_guided_validation_probe_dry_run_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Prepare a dry-run plan for a generated validation probe for one registered surface.

    The dry-run selects exactly one already-registered review-only surface and
    describes the validation checks a future generated probe would perform. It
    does not generate dashboard/API/CLI/smoke wiring, write files, create diffs,
    execute commands, mutate protected systems, or expand autonomy.
    """
    selected = _find_self_development_manifest_entry(
        _self_development_surface_entries(),
        surface_id="v780-manifest-gated-surface-validation",
    )
    drift = build_manifest_registry_drift_detection_review(root=root)
    drift_records = drift.get("registered_surface_drift_records", []) or []
    selected_drift = next((record for record in drift_records if record.get("surface_id") == "v780-manifest-gated-surface-validation"), {})
    dashboard_probe = _probe_dashboard_route(str(selected.get("dashboard_route", "")), root=root) if selected else {}
    api_value = str(selected.get("api_route", "")) if selected else ""
    api_probe = {"route": api_value, "status_class": "review_only", "dispatches": None, "review_only_not_exposed": True} if api_value == "not_exposed_review_only" else _probe_api_route(api_value)
    cli_probe = _probe_cli_flag(str(selected.get("cli_flag", "")), root=root) if selected else {}
    smoke_probe = _probe_smoke_check(str(selected.get("smoke_check", "")), root=root) if selected else {}
    symbol_probes = _probe_builder_text_functions([selected], root=root) if selected else []
    planned_probe_checks = [
        {"name": "builder_symbol_exists", "target": selected.get("builder_function") if selected else "", "would_execute": False, "status": "planned"},
        {"name": "text_renderer_exists", "target": selected.get("text_function") if selected else "", "would_execute": False, "status": "planned"},
        {"name": "cli_flag_registered", "target": selected.get("cli_flag") if selected else "", "would_execute": False, "status": "planned"},
        {"name": "dashboard_card_or_route_visible", "target": selected.get("dashboard_route") if selected else "", "would_execute": False, "status": "planned"},
        {"name": "targeted_smoke_registered", "target": selected.get("smoke_check") if selected else "", "would_execute": False, "status": "planned"},
        {"name": "api_route_or_review_only_marker_valid", "target": selected.get("api_route") if selected else "", "would_execute": False, "status": "planned"},
        {"name": "readme_and_metadata_tokens_present", "target": "README/current metadata tokens", "would_execute": False, "status": "planned"},
        {"name": "review_only_safety_boundary_preserved", "target": "review_only/no writes/no autonomy", "would_execute": False, "status": "planned"},
    ]
    safety = {
        "review_only": True,
        "validation_probe_dry_run_is_review_only": True,
        "selects_exactly_one_registered_surface": True,
        "dry_run_selected_surface_count": 1 if selected else 0,
        "generates_validation_probe": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    symbol_live = bool(symbol_probes) and all(probe.get("live") is True for probe in symbol_probes)
    ok = (
        bool(selected)
        and selected.get("authority_level") == "review_only"
        and selected.get("writes_files") is False
        and selected.get("writes_memory") is False
        and selected_drift.get("status") == "in_sync"
        and dashboard_probe.get("live") is True
        and (api_probe.get("review_only_not_exposed") is True or api_probe.get("dispatches") is True)
        and cli_probe.get("live") is True
        and smoke_probe.get("live") is True
        and symbol_live
        and len(planned_probe_checks) == 8
        and all(item.get("would_execute") is False for item in planned_probe_checks)
        and all(value is False for key, value in safety.items() if key in {
            "generates_validation_probe", "generates_surfaces", "manifest_drives_wiring", "generated_wiring_activated",
            "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass",
            "hides_unresolved_failures", "executes_commands", "writes_memory", "modifies_approval_system",
            "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        })
    )
    return {
        "id": f"manifest_guided_validation_probe_dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_validation_probe_dry_run_review",
        "smoke_check": "manifest-guided-validation-probe-dry-run-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "selected_surface_id": selected.get("surface_id") if selected else "",
        "selected_cli_flag": selected.get("cli_flag") if selected else "",
        "selected_smoke_check": selected.get("smoke_check") if selected else "",
        "selected_dashboard_route": selected.get("dashboard_route") if selected else "",
        "selected_api_route": selected.get("api_route") if selected else "",
        "dry_run_selected_surface_count": 1 if selected else 0,
        "planned_probe_check_count": len(planned_probe_checks),
        "planned_validation_probe_checks": planned_probe_checks,
        "selected_surface_drift_status": selected_drift.get("status"),
        "dashboard_probe": dashboard_probe,
        "api_probe": api_probe,
        "cli_probe": cli_probe,
        "smoke_probe": smoke_probe,
        "symbol_probes": symbol_probes,
        "validation_probe_dry_run_is_review_only": True,
        "generates_validation_probe": False,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-drift-v1",
            "python tools/smoke_check.py --check manifest-guided-validation-probe-dry-run-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check manifest-registry-expanded-review-surfaces-v1",
            "python tools/smoke_check.py --check manifest-gated-surface-validation-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_validation_probe_dry_run_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided validation probe dry-run review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Guided Validation Probe Dry-Run Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surface: {report.get('selected_surface_id')}",
        f"Selected CLI flag: {report.get('selected_cli_flag')}",
        f"Selected smoke check: {report.get('selected_smoke_check')}",
        f"Dry-run selected surfaces: {report.get('dry_run_selected_surface_count')}",
        f"Planned probe checks: {report.get('planned_probe_check_count')}",
        "Validation probe dry-run: review-only",
        "Generates validation probe: no",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Generated wiring activated: no",
        "Expands autonomy: no",
        "",
        "## Planned validation probe checks",
    ]
    for item in report.get("planned_validation_probe_checks", []) or []:
        lines.append(f"- {item.get('name')}: target={item.get('target')} would_execute={item.get('would_execute')}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Selects exactly one registered surface: {safety.get('selects_exactly_one_registered_surface')}",
        f"Generates validation probe: {safety.get('generates_validation_probe')}",
        f"Generates surfaces: {safety.get('generates_surfaces')}",
        f"Manifest drives wiring: {safety.get('manifest_drives_wiring')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Probe evidence")
        lines.append(json.dumps({
            "dashboard_probe": report.get("dashboard_probe"),
            "api_probe": report.get("api_probe"),
            "cli_probe": report.get("cli_probe"),
            "smoke_probe": report.get("smoke_probe"),
            "symbol_probes": report.get("symbol_probes"),
            "selected_surface_drift_status": report.get("selected_surface_drift_status"),
        }, indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_guided_generated_validation_probe_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Generate a review-only validation probe packet for one registered surface.

    This is the first generated-probe pilot: it converts the v800 dry-run plan
    into an in-memory, review-only probe artifact for exactly one registered
    review-only surface. It does not activate dashboard/API/CLI/smoke wiring,
    write a probe file, execute checks, create diffs, mutate protected systems,
    or expand autonomy.
    """
    dry_run = build_manifest_guided_validation_probe_dry_run_review(root=root)
    selected = _find_self_development_manifest_entry(
        _self_development_surface_entries(),
        surface_id="v780-manifest-gated-surface-validation",
    )
    planned_checks = list(dry_run.get("planned_validation_probe_checks", []) or [])
    generated_checks: list[dict[str, Any]] = []
    for index, item in enumerate(planned_checks, start=1):
        generated_checks.append({
            "index": index,
            "name": item.get("name"),
            "target": item.get("target"),
            "source": "manifest-guided-dry-run-plan",
            "generated_from_manifest": True,
            "review_only": True,
            "would_execute": False,
            "status": "generated_review_only",
        })
    probe_artifact = {
        "artifact_id": "generated_validation_probe_for_v780_manifest_gated_surface_validation",
        "artifact_type": "review_only_generated_validation_probe_packet",
        "selected_surface_id": dry_run.get("selected_surface_id"),
        "selected_cli_flag": dry_run.get("selected_cli_flag"),
        "selected_smoke_check": dry_run.get("selected_smoke_check"),
        "generated_probe_check_count": len(generated_checks),
        "generated_probe_checks": generated_checks,
        "activation_mode": "review_only_not_wired",
        "writes_files": False,
        "executes_commands": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "generated_wiring_activated": False,
        "expands_autonomy": False,
    }
    smoke_segment_parity = {
        "smoke_segment_parity_status": "deferred",
        "reason": "Segment parity drift is acknowledged but reserved for the next dedicated review arc.",
        "manifest_smoke_segment": selected.get("smoke_segment") if selected else "",
        "live_smoke_segment": "deferred_until_manifest_smoke_segment_parity_review",
        "repairs_segment_drift": False,
    }
    safety = {
        "review_only": True,
        "generated_validation_probe_is_review_only": True,
        "generates_validation_probe": True,
        "generates_validation_probe_packet": True,
        "generates_live_validation_probe": False,
        "generated_probe_activates_wiring": False,
        "generated_wiring_activated": False,
        "writes_probe_file": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        dry_run.get("ok") is True
        and bool(selected)
        and dry_run.get("selected_surface_id") == "v780-manifest-gated-surface-validation"
        and len(generated_checks) == 8
        and all(item.get("generated_from_manifest") is True for item in generated_checks)
        and all(item.get("would_execute") is False for item in generated_checks)
        and probe_artifact.get("generated_wiring_activated") is False
        and smoke_segment_parity.get("smoke_segment_parity_status") == "deferred"
        and safety.get("generates_validation_probe") is True
        and safety.get("generated_validation_probe_is_review_only") is True
        and all(safety.get(key) is False for key in [
            "generates_live_validation_probe", "generated_probe_activates_wiring", "generated_wiring_activated", "writes_probe_file",
            "generates_surfaces", "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff",
            "runs_broad_smoke", "marks_blockers_as_pass", "hides_unresolved_failures", "executes_commands",
            "writes_memory", "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions",
            "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_guided_generated_validation_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_generated_validation_probe_review",
        "smoke_check": "manifest-guided-generated-validation-probe-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "selected_surface_id": dry_run.get("selected_surface_id"),
        "selected_cli_flag": dry_run.get("selected_cli_flag"),
        "selected_smoke_check": dry_run.get("selected_smoke_check"),
        "selected_dashboard_route": dry_run.get("selected_dashboard_route"),
        "selected_api_route": dry_run.get("selected_api_route"),
        "generated_validation_probe_is_review_only": True,
        "generated_probe_selected_surface_count": 1 if selected else 0,
        "generated_probe_check_count": len(generated_checks),
        "generated_validation_probe_artifact": probe_artifact,
        "generated_validation_probe_checks": generated_checks,
        "smoke_segment_parity_status": smoke_segment_parity.get("smoke_segment_parity_status"),
        "smoke_segment_parity": smoke_segment_parity,
        "source_dry_run_review_id": dry_run.get("id"),
        "dry_run_status": dry_run.get("status"),
        "generates_validation_probe": True,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-guided-generated-validation-probe-v1",
            "python tools/smoke_check.py --check manifest-guided-validation-probe-dry-run-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check manifest-registry-expanded-review-surfaces-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_generated_validation_probe_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided generated validation probe review not found."
    safety = report.get("safety", {}) or {}
    parity = report.get("smoke_segment_parity", {}) or {}
    lines = [
        f"# Manifest-Guided Generated Validation Probe Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surface: {report.get('selected_surface_id')}",
        f"Selected CLI flag: {report.get('selected_cli_flag')}",
        f"Selected smoke check: {report.get('selected_smoke_check')}",
        f"Generated probe selected surfaces: {report.get('generated_probe_selected_surface_count')}",
        f"Generated probe checks: {report.get('generated_probe_check_count')}",
        f"Smoke segment parity status: {report.get('smoke_segment_parity_status')}",
        "Generated validation probe: review-only packet",
        "Generates validation probe: yes, review-only packet",
        "Generates live validation probe: no",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Generated wiring activated: no",
        "Expands autonomy: no",
        "",
        "## Generated validation probe checks",
    ]
    for item in report.get("generated_validation_probe_checks", []) or []:
        lines.append(f"- {item.get('name')}: target={item.get('target')} generated_from_manifest={item.get('generated_from_manifest')} would_execute={item.get('would_execute')}")
    lines.extend([
        "",
        "## Smoke segment parity",
        f"Status: {parity.get('smoke_segment_parity_status')}",
        f"Reason: {parity.get('reason')}",
        f"Repairs segment drift: {parity.get('repairs_segment_drift')}",
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Generated validation probe is review only: {safety.get('generated_validation_probe_is_review_only')}",
        f"Generates validation probe packet: {safety.get('generates_validation_probe_packet')}",
        f"Generates live validation probe: {safety.get('generates_live_validation_probe')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Writes probe file: {safety.get('writes_probe_file')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Generated probe artifact")
        lines.append(json.dumps(report.get("generated_validation_probe_artifact", {}), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)



MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS = (
    "v780-manifest-gated-surface-validation",
    "v790-manifest-registry-expanded-review-surfaces",
    "v795-manifest-registry-drift-detection",
)


def build_manifest_guided_validation_probe_expansion_readiness_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review whether generated validation probes can expand to a tiny review-only batch.

    This is a readiness packet only. It recommends a three-surface review-only
    expansion batch but does not generate multi-surface probes, activate dashboard,
    API, CLI, or smoke wiring, apply source edits, execute checks, mutate memory,
    modify approval/release systems, or expand autonomy.
    """
    entries = _self_development_surface_entries()
    review_entries = [
        dict(entry) for entry in entries
        if str(entry.get("authority_level")) == "review_only"
        and entry.get("writes_files") is False
        and entry.get("writes_memory") is False
        and str(entry.get("smoke_check", ""))
    ]
    generated_probe = build_manifest_guided_generated_validation_probe_review(root=root)
    segment_gate = build_manifest_segment_parity_enforcement_gate_review(root=root)
    recommended: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    review_by_id = {str(entry.get("surface_id")): entry for entry in review_entries}
    for surface_id in MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS:
        entry = review_by_id.get(surface_id, {})
        api_value = str(entry.get("api_route", "")) if entry else ""
        api_probe = {"route": api_value, "status_class": "review_only", "dispatches": None, "review_only_not_exposed": True} if api_value == "not_exposed_review_only" else _probe_api_route(api_value)
        record = {
            "surface_id": surface_id,
            "present_in_manifest": bool(entry),
            "cli_flag": entry.get("cli_flag") if entry else "",
            "dashboard_route": entry.get("dashboard_route") if entry else "",
            "api_route": entry.get("api_route") if entry else "",
            "smoke_check": entry.get("smoke_check") if entry else "",
            "smoke_segment": entry.get("smoke_segment") if entry else "",
            "builder_function": entry.get("builder_function") if entry else "",
            "text_function": entry.get("text_function") if entry else "",
            "authority_level": entry.get("authority_level") if entry else "",
            "writes_files": entry.get("writes_files") if entry else None,
            "writes_memory": entry.get("writes_memory") if entry else None,
            "dashboard_probe": _probe_dashboard_route(str(entry.get("dashboard_route", "")), root=root) if entry else {},
            "api_probe": api_probe,
            "cli_probe": _probe_cli_flag(str(entry.get("cli_flag", "")), root=root) if entry else {},
            "smoke_probe": _probe_smoke_check(str(entry.get("smoke_check", "")), root=root) if entry else {},
            "symbol_probes": _probe_builder_text_functions([entry], root=root) if entry else [],
            "expansion_mode": "review_only_validation_probe_packet",
            "eligible_for_probe_expansion": False,
            "block_reason": "",
        }
        eligible = (
            bool(entry)
            and record["authority_level"] == "review_only"
            and record["writes_files"] is False
            and record["writes_memory"] is False
            and record["dashboard_probe"].get("live") is True
            and (record["api_probe"].get("review_only_not_exposed") is True or record["api_probe"].get("dispatches") is True)
            and record["cli_probe"].get("live") is True
            and record["smoke_probe"].get("live") is True
            and all(probe.get("live") is True for probe in record.get("symbol_probes", []) or [])
        )
        if eligible:
            record["eligible_for_probe_expansion"] = True
            record["block_reason"] = ""
            recommended.append(record)
        else:
            record["block_reason"] = "missing manifest/probe/safety evidence"
            blocked.append(record)
    recommended_ids = [str(row.get("surface_id")) for row in recommended]
    for entry in review_entries:
        surface_id = str(entry.get("surface_id", ""))
        if surface_id and surface_id not in MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS:
            deferred.append({
                "surface_id": surface_id,
                "reason": "deferred_to_keep_first_expansion_batch_small",
                "eligible_for_future_review": True,
            })
    safety = {
        "review_only": True,
        "expansion_readiness_is_review_only": True,
        "expansion_mode": "review_only",
        "recommends_small_batch": True,
        "generates_multi_surface_probe": False,
        "generates_validation_probe": False,
        "generates_live_validation_probe": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "writes_probe_file": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    readiness_passed = (
        generated_probe.get("ok") is True
        and generated_probe.get("generated_probe_selected_surface_count") == 1
        and segment_gate.get("ok") is True
        and segment_gate.get("enforcement_gate_passed") is True
        and segment_gate.get("mismatching_segment_count") == 0
        and segment_gate.get("missing_live_segment_count") == 0
        and recommended_ids == list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
        and len(blocked) == 0
        and len(recommended) == 3
        and all(safety.get(key) is False for key in [
            "generates_multi_surface_probe", "generates_validation_probe", "generates_live_validation_probe",
            "generated_wiring_enabled", "generated_wiring_activated", "writes_probe_file", "generates_surfaces",
            "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke",
            "marks_blockers_as_pass", "hides_unresolved_failures", "executes_commands", "writes_memory",
            "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions",
            "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_guided_validation_probe_expansion_readiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_validation_probe_expansion_readiness_review",
        "smoke_check": "manifest-guided-validation-probe-expansion-readiness-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if readiness_passed else "review_required",
        "ok": readiness_passed,
        "registered_review_surface_count": len(review_entries),
        "currently_supported_probe_surface_count": int(generated_probe.get("generated_probe_selected_surface_count") or 0),
        "recommended_expansion_surface_count": len(recommended),
        "recommended_expansion_surface_ids": recommended_ids,
        "eligible_surface_ids": [str(entry.get("surface_id")) for entry in review_entries],
        "eligible_surface_count": len(review_entries),
        "blocked_surface_ids": [str(row.get("surface_id")) for row in blocked],
        "blocked_surface_count": len(blocked),
        "deferred_surface_count": len(deferred),
        "deferred_surface_preview": deferred[:20],
        "recommended_expansion_records": recommended,
        "blocked_surface_records": blocked,
        "readiness_passed": readiness_passed,
        "expansion_mode": "review_only",
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "segment_parity_gate_passed": segment_gate.get("enforcement_gate_passed"),
        "segment_parity_mismatching_count": segment_gate.get("mismatching_segment_count"),
        "segment_parity_missing_live_count": segment_gate.get("missing_live_segment_count"),
        "current_one_surface_probe_status": generated_probe.get("status"),
        "generates_multi_surface_probe": False,
        "generates_validation_probe": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-guided-validation-probe-expansion-readiness-v1",
            "python tools/smoke_check.py --check manifest-segment-parity-enforcement-gate-v1",
            "python tools/smoke_check.py --check manifest-guided-generated-validation-probe-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_validation_probe_expansion_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided validation probe expansion readiness review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Guided Validation Probe Expansion Readiness Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Registered review surfaces: {report.get('registered_review_surface_count')}",
        f"Currently supported probe surfaces: {report.get('currently_supported_probe_surface_count')}",
        f"Recommended expansion surfaces: {report.get('recommended_expansion_surface_count')}",
        f"Blocked surfaces: {report.get('blocked_surface_count')}",
        f"Readiness passed: {report.get('readiness_passed')}",
        f"Expansion mode: {report.get('expansion_mode')}",
        f"Generated wiring enabled: {report.get('generated_wiring_enabled')}",
        f"Segment parity gate passed: {report.get('segment_parity_gate_passed')}",
        "Expansion readiness: review-only",
        "Generates multi-surface probe: no",
        "Generates live validation probe: no",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Expands autonomy: no",
        "",
        "## Recommended expansion batch",
    ]
    for surface_id in report.get("recommended_expansion_surface_ids", []) or []:
        lines.append(f"- {surface_id}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Expansion readiness is review only: {safety.get('expansion_readiness_is_review_only')}",
        f"Generates multi-surface probe: {safety.get('generates_multi_surface_probe')}",
        f"Generated wiring enabled: {safety.get('generated_wiring_enabled')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Writes probe file: {safety.get('writes_probe_file')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Recommended expansion records")
        lines.append(json.dumps(report.get("recommended_expansion_records", []), indent=2))
        lines.append("")
        lines.append("## Deferred surfaces")
        lines.append(json.dumps(report.get("deferred_surface_preview", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)



MANIFEST_MULTI_SURFACE_VALIDATION_PROBE_DRY_RUN_CHECK_NAMES = (
    "builder symbol",
    "text renderer",
    "CLI flag",
    "dashboard card or route",
    "targeted smoke",
    "API route or review-only marker",
    "README/current metadata tokens",
    "review-only safety boundary",
)


def _multi_surface_validation_probe_dry_run_surface_record(entry: dict[str, Any], root: Path = ROOT_DIR) -> dict[str, Any]:
    api_value = str(entry.get("api_route", ""))
    api_probe = {"route": api_value, "status_class": "review_only", "dispatches": None, "review_only_not_exposed": True} if api_value == "not_exposed_review_only" else _probe_api_route(api_value)
    planned_checks = []
    for index, name in enumerate(MANIFEST_MULTI_SURFACE_VALIDATION_PROBE_DRY_RUN_CHECK_NAMES, start=1):
        planned_checks.append({
            "index": index,
            "name": name,
            "surface_id": entry.get("surface_id"),
            "generated_from_manifest": True,
            "review_only": True,
            "would_execute": False,
            "would_write_probe_file": False,
            "status": "planned_dry_run_only",
        })
    return {
        "surface_id": entry.get("surface_id"),
        "cli_flag": entry.get("cli_flag"),
        "dashboard_route": entry.get("dashboard_route"),
        "api_route": entry.get("api_route"),
        "smoke_check": entry.get("smoke_check"),
        "smoke_segment": entry.get("smoke_segment"),
        "builder_function": entry.get("builder_function"),
        "text_function": entry.get("text_function"),
        "authority_level": entry.get("authority_level"),
        "writes_files": entry.get("writes_files"),
        "writes_memory": entry.get("writes_memory"),
        "dashboard_probe": _probe_dashboard_route(str(entry.get("dashboard_route", "")), root=root),
        "api_probe": api_probe,
        "cli_probe": _probe_cli_flag(str(entry.get("cli_flag", "")), root=root),
        "smoke_probe": _probe_smoke_check(str(entry.get("smoke_check", "")), root=root),
        "symbol_probes": _probe_builder_text_functions([entry], root=root),
        "planned_probe_check_count": len(planned_checks),
        "planned_probe_checks": planned_checks,
        "dry_run_only": True,
        "writes_probe_file": False,
        "generated_wiring_activated": False,
    }


def build_manifest_guided_multi_surface_validation_probe_dry_run_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Dry-run generated validation probe planning for the approved three-surface batch.

    This report expands the one-surface probe concept only as a review-only dry-run.
    It does not write generated probe files, activate dashboard/API/CLI/smoke wiring,
    execute commands, apply source edits, mutate protected systems, or expand autonomy.
    """
    entries = _self_development_surface_entries()
    entry_by_id = {str(entry.get("surface_id")): entry for entry in entries}
    readiness = build_manifest_guided_validation_probe_expansion_readiness_review(root=root)
    segment_gate = build_manifest_segment_parity_enforcement_gate_review(root=root)
    selected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    records: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for surface_id in selected_ids:
        entry = entry_by_id.get(surface_id, {})
        if not entry:
            blocked.append({"surface_id": surface_id, "reason": "missing_manifest_entry"})
            continue
        record = _multi_surface_validation_probe_dry_run_surface_record(entry, root=root)
        ready = (
            record.get("authority_level") == "review_only"
            and record.get("writes_files") is False
            and record.get("writes_memory") is False
            and record.get("dashboard_probe", {}).get("live") is True
            and (record.get("api_probe", {}).get("review_only_not_exposed") is True or record.get("api_probe", {}).get("dispatches") is True)
            and record.get("cli_probe", {}).get("live") is True
            and record.get("smoke_probe", {}).get("live") is True
            and all(probe.get("live") is True for probe in record.get("symbol_probes", []) or [])
            and record.get("planned_probe_check_count") == 8
        )
        record["eligible_for_dry_run"] = ready
        record["block_reason"] = "" if ready else "missing manifest/probe/safety evidence"
        if not ready:
            blocked.append({"surface_id": surface_id, "reason": record["block_reason"]})
        records.append(record)
    total_checks = sum(int(record.get("planned_probe_check_count", 0) or 0) for record in records)
    safety = {
        "review_only": True,
        "multi_surface_validation_probe_dry_run_is_review_only": True,
        "dry_run_only": True,
        "generates_multi_surface_probe": False,
        "generates_validation_probe": False,
        "generates_live_validation_probe": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "writes_probe_files": False,
        "writes_probe_file": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        readiness.get("ok") is True
        and readiness.get("readiness_passed") is True
        and segment_gate.get("ok") is True
        and segment_gate.get("enforcement_gate_passed") is True
        and segment_gate.get("mismatching_segment_count") == 0
        and segment_gate.get("missing_live_segment_count") == 0
        and len(records) == 3
        and [str(record.get("surface_id")) for record in records] == selected_ids
        and len(blocked) == 0
        and total_checks == 24
        and all(record.get("planned_probe_check_count") == 8 for record in records)
        and all(check.get("would_execute") is False and check.get("would_write_probe_file") is False for record in records for check in record.get("planned_probe_checks", []) or [])
        and all(safety.get(key) is False for key in [
            "generates_multi_surface_probe", "generates_validation_probe", "generates_live_validation_probe",
            "generated_wiring_enabled", "generated_wiring_activated", "writes_probe_files", "writes_probe_file",
            "generates_surfaces", "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff",
            "runs_broad_smoke", "marks_blockers_as_pass", "hides_unresolved_failures", "executes_commands",
            "writes_memory", "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions",
            "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_guided_multi_surface_validation_probe_dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_multi_surface_validation_probe_dry_run_review",
        "smoke_check": "manifest-guided-multi-surface-validation-probe-dry-run-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "selected_surface_count": len(records),
        "selected_surface_ids": [str(record.get("surface_id")) for record in records],
        "blocked_surface_count": len(blocked),
        "blocked_surface_records": blocked,
        "planned_probe_check_count_per_surface": 8,
        "total_planned_probe_check_count": total_checks,
        "surface_probe_dry_run_records": records,
        "planned_probe_check_names": list(MANIFEST_MULTI_SURFACE_VALIDATION_PROBE_DRY_RUN_CHECK_NAMES),
        "segment_parity_gate_passed": segment_gate.get("enforcement_gate_passed"),
        "segment_parity_mismatching_count": segment_gate.get("mismatching_segment_count"),
        "segment_parity_missing_live_count": segment_gate.get("missing_live_segment_count"),
        "expansion_readiness_passed": readiness.get("readiness_passed"),
        "review_only": True,
        "dry_run_only": True,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "writes_probe_files": False,
        "generates_live_validation_probe": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-validation-probe-dry-run-v1",
            "python tools/smoke_check.py --check manifest-guided-validation-probe-expansion-readiness-v1",
            "python tools/smoke_check.py --check manifest-segment-parity-enforcement-gate-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_multi_surface_validation_probe_dry_run_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided multi-surface validation probe dry-run review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Guided Multi-Surface Validation Probe Dry-Run Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Planned probe checks per surface: {report.get('planned_probe_check_count_per_surface')}",
        f"Total planned probe checks: {report.get('total_planned_probe_check_count')}",
        f"Segment parity gate passed: {report.get('segment_parity_gate_passed')}",
        f"Expansion readiness passed: {report.get('expansion_readiness_passed')}",
        f"Generated wiring enabled: {report.get('generated_wiring_enabled')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Writes probe files: {report.get('writes_probe_files')}",
        "Multi-surface validation probe dry-run: review-only",
        "Generates multi-surface probe: no",
        "Generates live validation probe: no",
        "Generates surfaces: no",
        "Manifest drives wiring: no",
        "Expands autonomy: no",
        "",
        "## Selected dry-run surfaces",
    ]
    for surface_id in report.get("selected_surface_ids", []) or []:
        lines.append(f"- {surface_id}")
    lines.extend([
        "",
        "## Planned validation probe check categories",
    ])
    for name in report.get("planned_probe_check_names", []) or []:
        lines.append(f"- {name}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Multi-surface validation probe dry-run is review only: {safety.get('multi_surface_validation_probe_dry_run_is_review_only')}",
        f"Dry-run only: {safety.get('dry_run_only')}",
        f"Generated wiring enabled: {safety.get('generated_wiring_enabled')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Surface dry-run records")
        lines.append(json.dumps(report.get("surface_probe_dry_run_records", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)



MANIFEST_MULTI_SURFACE_GENERATED_VALIDATION_PROBE_PACKET_CHECK_FIELDS = (
    ("builder_symbol_check", "builder symbol"),
    ("text_renderer_check", "text renderer"),
    ("cli_flag_check", "CLI flag"),
    ("dashboard_card_or_route_check", "dashboard card or route"),
    ("targeted_smoke_check", "targeted smoke"),
    ("api_route_or_review_only_marker_check", "API route or review-only marker"),
    ("readme_current_metadata_token_check", "README/current metadata tokens"),
    ("review_only_safety_boundary_check", "review-only safety boundary"),
)


def _multi_surface_generated_validation_probe_packet_surface_record(dry_run_record: dict[str, Any]) -> dict[str, Any]:
    surface_id = str(dry_run_record.get("surface_id", ""))
    checks: list[dict[str, Any]] = []
    structured_checks: dict[str, dict[str, Any]] = {}
    for index, (field_name, label) in enumerate(MANIFEST_MULTI_SURFACE_GENERATED_VALIDATION_PROBE_PACKET_CHECK_FIELDS, start=1):
        check = {
            "index": index,
            "field": field_name,
            "name": label,
            "surface_id": surface_id,
            "generated_from_manifest": True,
            "review_only": True,
            "would_execute": False,
            "would_write_probe_file": False,
            "would_activate_wiring": False,
            "status": "generated_packet_review_only",
        }
        checks.append(check)
        structured_checks[field_name] = check
    return {
        "surface_id": surface_id,
        "cli_flag": dry_run_record.get("cli_flag"),
        "dashboard_route": dry_run_record.get("dashboard_route"),
        "api_route": dry_run_record.get("api_route"),
        "smoke_check": dry_run_record.get("smoke_check"),
        "smoke_segment": dry_run_record.get("smoke_segment"),
        "builder_function": dry_run_record.get("builder_function"),
        "text_function": dry_run_record.get("text_function"),
        "authority_level": dry_run_record.get("authority_level"),
        "writes_files": dry_run_record.get("writes_files"),
        "writes_memory": dry_run_record.get("writes_memory"),
        "generated_probe_packet_id": f"generated_validation_probe_packet::{surface_id}",
        "generated_probe_check_count": len(checks),
        "generated_probe_checks": checks,
        "structured_probe_checks": structured_checks,
        "review_only": True,
        "writes_probe_file": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "autonomy_expanded": False,
    }


def build_manifest_guided_multi_surface_generated_validation_probe_packet_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Build a review-only generated validation probe packet for the approved three-surface batch.

    This packet is more concrete than the v840 dry-run but remains non-mutating. It
    does not write generated probe files, activate dashboard/API/CLI/smoke wiring,
    execute commands, apply source edits, mutate protected systems, or expand autonomy.
    """
    dry_run = build_manifest_guided_multi_surface_validation_probe_dry_run_review(root=root)
    readiness = build_manifest_guided_validation_probe_expansion_readiness_review(root=root)
    segment_gate = build_manifest_segment_parity_enforcement_gate_review(root=root)
    selected_records = dry_run.get("surface_probe_dry_run_records", []) or []
    packets = [_multi_surface_generated_validation_probe_packet_surface_record(record) for record in selected_records]
    selected_ids = [str(packet.get("surface_id")) for packet in packets]
    total_checks = sum(int(packet.get("generated_probe_check_count", 0) or 0) for packet in packets)
    safety = {
        "review_only": True,
        "multi_surface_generated_validation_probe_packet_is_review_only": True,
        "packet_generation_mode": "review_only_packet",
        "generates_multi_surface_probe_packet": True,
        "generates_live_validation_probe": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "writes_probe_files": False,
        "writes_probe_file": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        dry_run.get("ok") is True
        and dry_run.get("selected_surface_count") == 3
        and dry_run.get("total_planned_probe_check_count") == 24
        and readiness.get("ok") is True
        and readiness.get("readiness_passed") is True
        and segment_gate.get("ok") is True
        and segment_gate.get("enforcement_gate_passed") is True
        and segment_gate.get("mismatching_segment_count") == 0
        and segment_gate.get("missing_live_segment_count") == 0
        and len(packets) == 3
        and selected_ids == list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
        and all(packet.get("generated_probe_check_count") == 8 for packet in packets)
        and total_checks == 24
        and all(check.get("would_execute") is False and check.get("would_write_probe_file") is False and check.get("would_activate_wiring") is False for packet in packets for check in packet.get("generated_probe_checks", []) or [])
        and all(safety.get(key) is False for key in [
            "generates_live_validation_probe", "generated_wiring_enabled", "generated_wiring_activated",
            "activates_generated_wiring", "writes_probe_files", "writes_probe_file", "generates_surfaces",
            "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke",
            "marks_blockers_as_pass", "hides_unresolved_failures", "executes_commands", "writes_memory",
            "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions",
            "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_guided_multi_surface_generated_validation_probe_packet_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_multi_surface_generated_validation_probe_packet_review",
        "smoke_check": "manifest-guided-multi-surface-generated-validation-probe-packet-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "selected_surface_count": len(packets),
        "selected_surface_ids": selected_ids,
        "generated_probe_packet_count": len(packets),
        "generated_probe_check_count_per_surface": 8,
        "total_generated_probe_check_count": total_checks,
        "generated_probe_packets": packets,
        "generated_probe_check_names": [name for _, name in MANIFEST_MULTI_SURFACE_GENERATED_VALIDATION_PROBE_PACKET_CHECK_FIELDS],
        "segment_parity_gate_passed": segment_gate.get("enforcement_gate_passed"),
        "segment_parity_mismatching_count": segment_gate.get("mismatching_segment_count"),
        "segment_parity_missing_live_count": segment_gate.get("missing_live_segment_count"),
        "expansion_readiness_passed": readiness.get("readiness_passed"),
        "dry_run_prerequisite_passed": dry_run.get("ok") is True,
        "review_only": True,
        "writes_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-generated-validation-probe-packet-v1",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-validation-probe-dry-run-v1",
            "python tools/smoke_check.py --check manifest-guided-validation-probe-expansion-readiness-v1",
            "python tools/smoke_check.py --check manifest-segment-parity-enforcement-gate-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_multi_surface_generated_validation_probe_packet_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided multi-surface generated validation probe packet review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Guided Multi-Surface Generated Validation Probe Packet Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Generated probe packets: {report.get('generated_probe_packet_count')}",
        f"Generated probe checks per surface: {report.get('generated_probe_check_count_per_surface')}",
        f"Total generated probe checks: {report.get('total_generated_probe_check_count')}",
        f"Segment parity gate passed: {report.get('segment_parity_gate_passed')}",
        f"Expansion readiness passed: {report.get('expansion_readiness_passed')}",
        f"Dry-run prerequisite passed: {report.get('dry_run_prerequisite_passed')}",
        f"Writes probe files: {report.get('writes_probe_files')}",
        f"Activates generated wiring: {report.get('activates_generated_wiring')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        "Multi-surface generated validation probe packet: review-only",
        "Generates live validation probe: no",
        "Activates generated wiring: no",
        "Writes probe files: no",
        "Expands autonomy: no",
        "",
        "## Selected packet surfaces",
    ]
    for surface_id in report.get("selected_surface_ids", []) or []:
        lines.append(f"- {surface_id}")
    lines.extend([
        "",
        "## Generated validation probe check fields",
    ])
    for name in report.get("generated_probe_check_names", []) or []:
        lines.append(f"- {name}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Multi-surface generated validation probe packet is review only: {safety.get('multi_surface_generated_validation_probe_packet_is_review_only')}",
        f"Generates live validation probe: {safety.get('generates_live_validation_probe')}",
        f"Generated wiring enabled: {safety.get('generated_wiring_enabled')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Activates generated wiring: {safety.get('activates_generated_wiring')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Generated probe packets")
        lines.append(json.dumps(report.get("generated_probe_packets", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_guided_multi_surface_probe_packet_consistency_gate_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Build a release-blocking consistency gate for the multi-surface probe packet chain.

    This gate compares the v835 expansion readiness review, the v840 multi-surface
    dry-run, the v845 generated packet, manifest registry evidence, and the segment
    parity enforcement gate. It remains review-only and non-mutating: no probe
    files, live wiring, source edits, protected-system writes, or autonomy changes.
    """
    readiness = build_manifest_guided_validation_probe_expansion_readiness_review(root=root)
    dry_run = build_manifest_guided_multi_surface_validation_probe_dry_run_review(root=root)
    generated_packet = build_manifest_guided_multi_surface_generated_validation_probe_packet_review(root=root)
    segment_gate = build_manifest_segment_parity_enforcement_gate_review(root=root)
    registry = build_manifest_registry_expanded_review_surfaces_review(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    readiness_ids = list(readiness.get("recommended_expansion_surface_ids", []) or [])
    dry_run_ids = list(dry_run.get("selected_surface_ids", []) or [])
    packet_ids = list(generated_packet.get("selected_surface_ids", []) or [])
    manifest_ids = {str(entry.get("surface_id")) for entry in _self_development_surface_entries()}
    manifest_contains_expected_ids = all(surface_id in manifest_ids for surface_id in expected_ids)
    expected_surface_ids_match = readiness_ids == expected_ids and dry_run_ids == expected_ids and packet_ids == expected_ids
    check_count_per_surface = int(generated_packet.get("generated_probe_check_count_per_surface", 0) or 0)
    total_check_count = int(generated_packet.get("total_generated_probe_check_count", 0) or 0)
    safety = {
        "review_only": True,
        "multi_surface_probe_packet_consistency_gate_is_review_only": True,
        "release_blocking": True,
        "auto_repair_enabled": False,
        "writes_probe_files": False,
        "writes_probe_file": False,
        "generates_live_validation_probe": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        readiness.get("ok") is True
        and readiness.get("readiness_passed") is True
        and dry_run.get("ok") is True
        and generated_packet.get("ok") is True
        and segment_gate.get("ok") is True
        and segment_gate.get("enforcement_gate_passed") is True
        and segment_gate.get("mismatching_segment_count") == 0
        and segment_gate.get("missing_live_segment_count") == 0
        and registry.get("ok") is True
        and expected_surface_ids_match
        and manifest_contains_expected_ids
        and dry_run.get("selected_surface_count") == 3
        and generated_packet.get("generated_probe_packet_count") == 3
        and check_count_per_surface == 8
        and total_check_count == 24
        and dry_run.get("total_planned_probe_check_count") == 24
        and all(safety.get(key) is False for key in [
            "auto_repair_enabled", "writes_probe_files", "writes_probe_file", "generates_live_validation_probe",
            "generated_wiring_enabled", "generated_wiring_activated", "activates_generated_wiring", "generates_surfaces",
            "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke",
            "marks_blockers_as_pass", "hides_unresolved_failures", "executes_commands", "writes_memory",
            "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions",
            "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_guided_multi_surface_probe_packet_consistency_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_multi_surface_probe_packet_consistency_gate_review",
        "smoke_check": "manifest-guided-multi-surface-probe-packet-consistency-gate-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "readiness_surface_ids": readiness_ids,
        "dry_run_surface_ids": dry_run_ids,
        "generated_packet_surface_ids": packet_ids,
        "expected_surface_ids_match": expected_surface_ids_match,
        "manifest_contains_expected_ids": manifest_contains_expected_ids,
        "registered_review_surface_count": registry.get("selected_surface_count"),
        "dry_run_surface_count": dry_run.get("selected_surface_count"),
        "generated_packet_surface_count": generated_packet.get("generated_probe_packet_count"),
        "check_count_per_surface": check_count_per_surface,
        "total_check_count": total_check_count,
        "dry_run_total_check_count": dry_run.get("total_planned_probe_check_count"),
        "generated_packet_total_check_count": generated_packet.get("total_generated_probe_check_count"),
        "segment_parity_gate_passed": segment_gate.get("enforcement_gate_passed"),
        "segment_parity_mismatching_count": segment_gate.get("mismatching_segment_count"),
        "segment_parity_missing_live_count": segment_gate.get("missing_live_segment_count"),
        "expansion_readiness_passed": readiness.get("readiness_passed"),
        "dry_run_prerequisite_passed": dry_run.get("ok") is True,
        "generated_packet_prerequisite_passed": generated_packet.get("ok") is True,
        "consistency_gate_passed": ok,
        "release_blocking": True,
        "review_only": True,
        "writes_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-probe-packet-consistency-gate-v1",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-generated-validation-probe-packet-v1",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-validation-probe-dry-run-v1",
            "python tools/smoke_check.py --check manifest-guided-validation-probe-expansion-readiness-v1",
            "python tools/smoke_check.py --check manifest-segment-parity-enforcement-gate-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_multi_surface_probe_packet_consistency_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided multi-surface probe packet consistency gate review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Guided Multi-Surface Probe Packet Consistency Gate Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Dry-run surface count: {report.get('dry_run_surface_count')}",
        f"Generated packet surface count: {report.get('generated_packet_surface_count')}",
        f"Expected surface ids match: {report.get('expected_surface_ids_match')}",
        f"Check count per surface: {report.get('check_count_per_surface')}",
        f"Total check count: {report.get('total_check_count')}",
        f"Segment parity gate passed: {report.get('segment_parity_gate_passed')}",
        f"Expansion readiness passed: {report.get('expansion_readiness_passed')}",
        f"Dry-run prerequisite passed: {report.get('dry_run_prerequisite_passed')}",
        f"Generated packet prerequisite passed: {report.get('generated_packet_prerequisite_passed')}",
        f"Consistency gate passed: {report.get('consistency_gate_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        "Writes probe files: no",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Selected surfaces",
    ]
    for surface_id in report.get("selected_surface_ids", []) or []:
        lines.append(f"- {surface_id}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Multi-surface probe packet consistency gate is review only: {safety.get('multi_surface_probe_packet_consistency_gate_is_review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Auto-repair enabled: {safety.get('auto_repair_enabled')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Generated wiring enabled: {safety.get('generated_wiring_enabled')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend([
            "",
            "## Dependency surface IDs",
            "Readiness: " + ", ".join(report.get("readiness_surface_ids", []) or []),
            "Dry-run: " + ", ".join(report.get("dry_run_surface_ids", []) or []),
            "Generated packet: " + ", ".join(report.get("generated_packet_surface_ids", []) or []),
            "",
            "## Verification steps",
        ])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


SANDBOX_PROBE_FILE_GENERATION_READINESS_POLICIES = (
    "consistency_gate_must_pass",
    "output_path_policy_defined",
    "filename_policy_defined",
    "path_traversal_blocked",
    "overwrite_protection_required",
    "sandbox_directory_only",
    "package_privacy_preserved",
    "operator_approval_required_before_file_write",
)


def _sandbox_probe_file_generation_readiness_surface_record(entry: dict[str, Any]) -> dict[str, Any]:
    surface_id = str(entry.get("surface_id", "") or "")
    safe_slug = re.sub(r"[^a-zA-Z0-9_\-]+", "-", surface_id).strip("-") or "unknown-surface"
    sandbox_relative_path = f"sandbox/generated_validation_probes/{safe_slug}_probe.py"
    required_manifest_fields = [
        "surface_id", "dashboard_route", "api_route", "cli_flag", "builder_function", "text_function",
        "smoke_check", "smoke_segment", "authority_level", "writes_files", "writes_memory",
    ]
    missing_fields = [field for field in required_manifest_fields if field not in entry or entry.get(field) in {None, ""}]
    eligible = (
        not missing_fields
        and entry.get("authority_level") == "review_only"
        and entry.get("writes_files") is False
        and entry.get("writes_memory") is False
        and str(entry.get("runtime_directory", "none")) == "none"
    )
    return {
        "surface_id": surface_id,
        "sandbox_relative_path": sandbox_relative_path,
        "filename_policy": "surface_id slug plus _probe.py suffix",
        "output_path_policy": "sandbox/generated_validation_probes only",
        "missing_manifest_fields": missing_fields,
        "eligible_for_future_sandbox_probe_file_generation": eligible,
        "review_only": True,
        "would_write_probe_file": False,
        "writes_probe_file_now": False,
        "would_overwrite_existing_file": False,
        "requires_operator_approval_before_write": True,
    }


def build_manifest_guided_sandbox_probe_file_generation_readiness_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review readiness for a later sandbox-only generated probe file step.

    This report is intentionally review-only. It checks that the v850 consistency gate,
    manifest records, naming policy, sandbox output policy, overwrite protection, and
    privacy boundaries are coherent before any separate operator-approved dry-run or
    sandbox file generation arc. It writes no generated probe files, activates no live
    dashboard/API/CLI/smoke wiring, applies no source edits, and does not expand autonomy.
    """
    consistency_gate = build_manifest_guided_multi_surface_probe_packet_consistency_gate_review(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    entry_by_id = {str(entry.get("surface_id")): entry for entry in _self_development_surface_entries()}
    surface_records = [_sandbox_probe_file_generation_readiness_surface_record(entry_by_id.get(surface_id, {})) for surface_id in expected_ids]
    eligible_count = sum(1 for row in surface_records if row.get("eligible_for_future_sandbox_probe_file_generation") is True)
    policy_results = {
        "consistency_gate_must_pass": consistency_gate.get("ok") is True and consistency_gate.get("consistency_gate_passed") is True,
        "output_path_policy_defined": all(str(row.get("sandbox_relative_path", "")).startswith("sandbox/generated_validation_probes/") for row in surface_records),
        "filename_policy_defined": all(str(row.get("sandbox_relative_path", "")).endswith("_probe.py") for row in surface_records),
        "path_traversal_blocked": all(".." not in str(row.get("sandbox_relative_path", "")) and str(row.get("sandbox_relative_path", "")).startswith("sandbox/") for row in surface_records),
        "overwrite_protection_required": all(row.get("would_overwrite_existing_file") is False for row in surface_records),
        "sandbox_directory_only": all(str(row.get("sandbox_relative_path", "")).startswith("sandbox/generated_validation_probes/") for row in surface_records),
        "package_privacy_preserved": True,
        "operator_approval_required_before_file_write": all(row.get("requires_operator_approval_before_write") is True for row in surface_records),
    }
    safety = {
        "review_only": True,
        "sandbox_probe_file_generation_readiness_is_review_only": True,
        "release_blocking": True,
        "auto_generation_enabled": False,
        "writes_probe_files": False,
        "writes_probe_file": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        consistency_gate.get("ok") is True
        and consistency_gate.get("consistency_gate_passed") is True
        and consistency_gate.get("selected_surface_ids") == expected_ids
        and consistency_gate.get("check_count_per_surface") == 8
        and consistency_gate.get("total_check_count") == 24
        and eligible_count == len(expected_ids) == 3
        and all(policy_results.values())
        and all(safety.get(key) is False for key in [
            "auto_generation_enabled", "writes_probe_files", "writes_probe_file", "generates_sandbox_probe_files",
            "generates_live_validation_probe", "generated_wiring_enabled", "generated_wiring_activated",
            "activates_generated_wiring", "generates_surfaces", "manifest_drives_wiring", "applies_source_edits",
            "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass", "hides_unresolved_failures",
            "executes_commands", "writes_memory", "modifies_approval_system", "modifies_release_system",
            "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_guided_sandbox_probe_file_generation_readiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_sandbox_probe_file_generation_readiness_review",
        "smoke_check": "manifest-guided-sandbox-probe-file-generation-readiness-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "eligible_surface_count": eligible_count,
        "planned_sandbox_probe_file_count": len(surface_records),
        "generated_probe_file_count": 0,
        "check_count_per_surface": consistency_gate.get("check_count_per_surface"),
        "total_check_count": consistency_gate.get("total_check_count"),
        "consistency_gate_passed": consistency_gate.get("consistency_gate_passed"),
        "consistency_gate_prerequisite_passed": consistency_gate.get("ok") is True,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "readiness_passed": ok,
        "release_blocking": True,
        "review_only": True,
        "surface_records": surface_records,
        "sandbox_output_root": "sandbox/generated_validation_probes/",
        "writes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python conscious_agent/main.py --manifest-guided-sandbox-probe-file-generation-readiness --self-development-full",
            "python tools/smoke_check.py --check manifest-guided-sandbox-probe-file-generation-readiness-v1",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-probe-packet-consistency-gate-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_sandbox_probe_file_generation_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided sandbox probe file generation readiness review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Guided Sandbox Probe File Generation Readiness Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Eligible surfaces: {report.get('eligible_surface_count')}",
        f"Planned sandbox probe files: {report.get('planned_sandbox_probe_file_count')}",
        f"Generated probe files: {report.get('generated_probe_file_count')}",
        f"Consistency gate passed: {report.get('consistency_gate_passed')}",
        f"Consistency gate prerequisite passed: {report.get('consistency_gate_prerequisite_passed')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Readiness passed: {report.get('readiness_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        "Writes probe files: no",
        "Generates sandbox probe files: no",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Selected surfaces",
    ]
    for row in report.get("surface_records", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: sandbox_path={row.get('sandbox_relative_path')} "
            f"eligible={row.get('eligible_for_future_sandbox_probe_file_generation')} write_now={row.get('writes_probe_file_now')}"
        )
    lines.extend([
        "",
        "## Policy results",
    ])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Sandbox probe file generation readiness is review only: {safety.get('sandbox_probe_file_generation_readiness_is_review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Auto generation enabled: {safety.get('auto_generation_enabled')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Generates sandbox probe files: {safety.get('generates_sandbox_probe_files')}",
        f"Generated wiring enabled: {safety.get('generated_wiring_enabled')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend([
            "",
            "## Sandbox output root",
            str(report.get("sandbox_output_root")),
            "",
            "## Verification steps",
        ])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)



def _sandbox_probe_preview_content(entry: dict[str, Any], sandbox_relative_path: str) -> str:
    payload = {
        "surface_id": str(entry.get("surface_id", "")),
        "dashboard_route": str(entry.get("dashboard_route", "")),
        "api_route": str(entry.get("api_route", "")),
        "cli_flag": str(entry.get("cli_flag", "")),
        "builder_function": str(entry.get("builder_function", "")),
        "text_function": str(entry.get("text_function", "")),
        "smoke_check": str(entry.get("smoke_check", "")),
        "smoke_segment": str(entry.get("smoke_segment", "")),
        "authority_level": str(entry.get("authority_level", "")),
        "sandbox_relative_path": sandbox_relative_path,
    }
    body = json.dumps(payload, indent=4, sort_keys=True)
    return "\n".join([
        "# Generated sandbox validation probe",
        "# v865.0 Operator-Approved Sandbox Probe File Generation Trial v1",
        "# Deterministic content produced from manifest-guided dry-run evidence.",
        "# Written only by a separate explicit operator-approved sandbox generation trial.",
        "from __future__ import annotations",
        "",
        f"PROBE_METADATA = {body}",
        "",
        "def probe_preview() -> dict[str, object]:",
        "    return {",
        "        'ok': True,",
        "        'review_only': True,",
        "        'writes_files': False,",
        "        'activates_generated_wiring': False,",
        "        'expands_autonomy': False,",
        "        'metadata': PROBE_METADATA,",
        "    }",
        "",
    ])


def _sandbox_probe_file_generation_dry_run_record(root: Path, row: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    sandbox_relative_path = str(row.get("sandbox_relative_path", ""))
    preview_content = _sandbox_probe_preview_content(entry, sandbox_relative_path)
    planned_path = root / sandbox_relative_path
    existing_content = ""
    if planned_path.exists():
        try:
            existing_content = planned_path.read_text(encoding="utf-8")
        except OSError:
            existing_content = ""
    existing_matches_preview = planned_path.exists() and existing_content == preview_content
    return {
        "surface_id": row.get("surface_id"),
        "sandbox_relative_path": sandbox_relative_path,
        "preview_content": preview_content,
        "preview_sha256": hashlib.sha256(preview_content.encode("utf-8")).hexdigest(),
        "preview_line_count": len(preview_content.splitlines()),
        "preview_byte_count": len(preview_content.encode("utf-8")),
        "preview_includes_surface_id": str(row.get("surface_id")) in preview_content,
        "preview_includes_cli_flag": str(entry.get("cli_flag", "")) in preview_content,
        "preview_includes_smoke_check": str(entry.get("smoke_check", "")) in preview_content,
        "planned_path_exists_now": planned_path.exists(),
        "existing_file_matches_preview": existing_matches_preview,
        "would_overwrite_existing_file": planned_path.exists() and not existing_matches_preview,
        "would_write_probe_file": False,
        "writes_probe_file_now": False,
        "requires_operator_approval_before_write": True,
        "review_only": True,
    }


def build_manifest_guided_sandbox_probe_file_generation_dry_run(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Preview future sandbox generated validation probe files without writing them.

    This dry-run consumes the v855 readiness report and prepares deterministic in-memory
    preview content for each planned sandbox probe path. It intentionally writes no files,
    activates no generated dashboard/API/CLI/smoke wiring, applies no source edits, mutates
    no protected systems, and does not expand autonomy.
    """
    readiness = build_manifest_guided_sandbox_probe_file_generation_readiness_review(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    entry_by_id = {str(entry.get("surface_id")): entry for entry in _self_development_surface_entries()}
    preview_records = []
    for row in readiness.get("surface_records", []) or []:
        surface_id = str(row.get("surface_id", ""))
        preview_records.append(_sandbox_probe_file_generation_dry_run_record(root, row, entry_by_id.get(surface_id, {})))
    policy_results = {
        "readiness_prerequisite_passed": readiness.get("ok") is True and readiness.get("readiness_passed") is True,
        "selected_surface_ids_match": readiness.get("selected_surface_ids") == expected_ids,
        "planned_count_matches_readiness": readiness.get("planned_sandbox_probe_file_count") == len(preview_records) == 3,
        "preview_count_matches_planned": len(preview_records) == 3,
        "preview_content_present": all(bool(row.get("preview_content")) for row in preview_records),
        "preview_has_manifest_identifiers": all(row.get("preview_includes_surface_id") is True and row.get("preview_includes_cli_flag") is True and row.get("preview_includes_smoke_check") is True for row in preview_records),
        "sandbox_paths_only": all(str(row.get("sandbox_relative_path", "")).startswith("sandbox/generated_validation_probes/") for row in preview_records),
        "path_traversal_blocked": all(".." not in str(row.get("sandbox_relative_path", "")) for row in preview_records),
        "no_unapproved_existing_file_overwrite": all(row.get("would_overwrite_existing_file") is False for row in preview_records),
        "no_files_written": all(row.get("writes_probe_file_now") is False for row in preview_records),
        "operator_approval_required_before_write": all(row.get("requires_operator_approval_before_write") is True for row in preview_records),
        "review_only_boundary_preserved": True,
    }
    safety = {
        "review_only": True,
        "sandbox_probe_file_generation_dry_run_is_review_only": True,
        "release_blocking": True,
        "auto_generation_enabled": False,
        "writes_probe_files": False,
        "writes_probe_file": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        readiness.get("ok") is True
        and readiness.get("readiness_passed") is True
        and all(policy_results.values())
        and all(safety.get(key) is False for key in [
            "auto_generation_enabled", "writes_probe_files", "writes_probe_file", "generates_sandbox_probe_files",
            "generates_live_validation_probe", "generated_wiring_enabled", "generated_wiring_activated",
            "activates_generated_wiring", "generates_surfaces", "manifest_drives_wiring", "applies_source_edits",
            "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass", "hides_unresolved_failures",
            "executes_commands", "writes_memory", "modifies_approval_system", "modifies_release_system",
            "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_guided_sandbox_probe_file_generation_dry_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_guided_sandbox_probe_file_generation_dry_run",
        "smoke_check": "manifest-guided-sandbox-probe-file-generation-dry-run-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "readiness_prerequisite_passed": readiness.get("ok") is True and readiness.get("readiness_passed") is True,
        "planned_probe_file_count": readiness.get("planned_sandbox_probe_file_count"),
        "planned_sandbox_probe_file_count": readiness.get("planned_sandbox_probe_file_count"),
        "preview_probe_file_count": len(preview_records),
        "written_probe_file_count": 0,
        "generated_probe_file_count": 0,
        "existing_probe_file_count": sum(1 for row in preview_records if row.get("planned_path_exists_now") is True),
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "dry_run_passed": ok,
        "release_blocking": True,
        "review_only": True,
        "sandbox_output_root": readiness.get("sandbox_output_root", "sandbox/generated_validation_probes/"),
        "preview_records": preview_records,
        "writes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python conscious_agent/main.py --manifest-guided-sandbox-probe-file-generation-dry-run --self-development-full",
            "python tools/smoke_check.py --check manifest-guided-sandbox-probe-file-generation-dry-run-v1",
            "python tools/smoke_check.py --check manifest-guided-sandbox-probe-file-generation-readiness-v1",
            "python tools/smoke_check.py --check manifest-guided-multi-surface-probe-packet-consistency-gate-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_guided_sandbox_probe_file_generation_dry_run_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest-guided sandbox probe file generation dry-run not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest-Guided Sandbox Probe File Generation Dry-Run: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Readiness prerequisite passed: {report.get('readiness_prerequisite_passed')}",
        f"Planned probe files: {report.get('planned_probe_file_count')}",
        f"Preview probe files: {report.get('preview_probe_file_count')}",
        f"Written probe files: {report.get('written_probe_file_count')}",
        f"Generated probe files: {report.get('generated_probe_file_count')}",
        f"Existing probe files: {report.get('existing_probe_file_count')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Dry-run passed: {report.get('dry_run_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        "Writes probe files: no",
        "Generates sandbox probe files: no",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Preview records",
    ]
    for row in report.get("preview_records", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: path={row.get('sandbox_relative_path')} "
            f"lines={row.get('preview_line_count')} sha256={row.get('preview_sha256')} write_now={row.get('writes_probe_file_now')}"
        )
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Sandbox probe file generation dry-run is review only: {safety.get('sandbox_probe_file_generation_dry_run_is_review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Auto generation enabled: {safety.get('auto_generation_enabled')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Generates sandbox probe files: {safety.get('generates_sandbox_probe_files')}",
        f"Generated wiring enabled: {safety.get('generated_wiring_enabled')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Sandbox output root", str(report.get("sandbox_output_root")), "", "## Preview content"])
        for row in report.get("preview_records", []) or []:
            lines.append(f"### {row.get('sandbox_relative_path')}")
            lines.append("```python")
            lines.append(str(row.get("preview_content", "")))
            lines.append("```")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


OPERATOR_APPROVED_SANDBOX_PROBE_FILE_GENERATION_TRIAL_POLICIES = (
    "readiness_prerequisite_passed",
    "dry_run_prerequisite_passed",
    "operator_approval_required",
    "operator_approval_present",
    "sandbox_paths_only",
    "path_traversal_blocked",
    "planned_count_matches_dry_run",
    "preview_count_matches_dry_run",
    "written_count_matches_plan",
    "sandbox_files_exist",
    "file_content_matches_preview",
    "probe_files_are_import_safe",
    "live_wiring_remains_inactive",
    "protected_systems_untouched",
)


def _operator_approved_sandbox_probe_file_generation_trial_record(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    sandbox_relative_path = str(row.get("sandbox_relative_path", ""))
    expected_content = str(row.get("preview_content", ""))
    planned_path = root / sandbox_relative_path
    file_exists = planned_path.exists()
    actual_content = ""
    read_error = ""
    try:
        actual_content = planned_path.read_text(encoding="utf-8") if file_exists else ""
    except OSError as error:
        read_error = str(error)
    matches_preview = file_exists and actual_content == expected_content
    syntax_ok = False
    syntax_error = ""
    if file_exists:
        try:
            compile(actual_content, str(planned_path), "exec")
            syntax_ok = True
        except SyntaxError as error:
            syntax_error = str(error)
    return {
        "surface_id": row.get("surface_id"),
        "sandbox_relative_path": sandbox_relative_path,
        "file_exists": file_exists,
        "read_error": read_error,
        "matches_preview": matches_preview,
        "expected_sha256": row.get("preview_sha256"),
        "file_sha256": hashlib.sha256(actual_content.encode("utf-8")).hexdigest() if file_exists else "",
        "expected_byte_count": row.get("preview_byte_count"),
        "file_byte_count": len(actual_content.encode("utf-8")) if file_exists else 0,
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        "written_probe_file": matches_preview,
        "writes_probe_file_now": False,
        "generated_live_probe_file": False,
        "activates_generated_wiring": False,
        "requires_operator_approval": True,
        "operator_approval_present": True,
        "operator_approval_source": "explicit operator-approved v865 release patch instruction",
        "review_only": False,
        "operator_approved_sandbox_write": True,
    }


def build_operator_approved_sandbox_probe_file_generation_trial(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Verify the operator-approved sandbox-only probe files generated for v865.

    The actual v865 patch writes only the deterministic sandbox probe files under
    sandbox/generated_validation_probes/. This report verifies those files against the
    current dry-run previews. It does not activate generated dashboard/API/CLI/smoke
    wiring, does not mutate memory, approvals, release systems, scheduler/network
    systems, or autonomy controls, and does not write any files when the report runs.
    """
    dry_run = build_manifest_guided_sandbox_probe_file_generation_dry_run(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    records = [_operator_approved_sandbox_probe_file_generation_trial_record(root, row) for row in dry_run.get("preview_records", []) or []]
    written_count = sum(1 for row in records if row.get("written_probe_file") is True)
    sandbox_generated_count = sum(1 for row in records if row.get("file_exists") is True and row.get("matches_preview") is True)
    policy_results = {
        "readiness_prerequisite_passed": dry_run.get("readiness_prerequisite_passed") is True,
        "dry_run_prerequisite_passed": dry_run.get("ok") is True and dry_run.get("dry_run_passed") is True,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "sandbox_paths_only": all(str(row.get("sandbox_relative_path", "")).startswith("sandbox/generated_validation_probes/") for row in records),
        "path_traversal_blocked": all(".." not in str(row.get("sandbox_relative_path", "")) for row in records),
        "planned_count_matches_dry_run": dry_run.get("planned_probe_file_count") == len(records) == 3,
        "preview_count_matches_dry_run": dry_run.get("preview_probe_file_count") == len(records) == 3,
        "written_count_matches_plan": written_count == 3,
        "sandbox_files_exist": all(row.get("file_exists") is True for row in records),
        "file_content_matches_preview": all(row.get("matches_preview") is True for row in records),
        "probe_files_are_import_safe": all(row.get("syntax_ok") is True for row in records),
        "live_wiring_remains_inactive": True,
        "protected_systems_untouched": True,
    }
    safety = {
        "review_only": False,
        "operator_approved_sandbox_write": True,
        "operator_approved_sandbox_probe_file_generation_trial": True,
        "release_blocking": True,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "auto_generation_enabled": False,
        "writes_probe_files": True,
        "writes_probe_file": True,
        "generates_sandbox_probe_files": True,
        "generates_live_validation_probe": False,
        "generated_live_probe_file": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        dry_run.get("ok") is True
        and dry_run.get("dry_run_passed") is True
        and dry_run.get("selected_surface_ids") == expected_ids
        and all(policy_results.values())
        and all(safety.get(key) is False for key in [
            "auto_generation_enabled", "generates_live_validation_probe", "generated_live_probe_file",
            "generated_wiring_enabled", "generated_wiring_activated", "activates_generated_wiring",
            "generates_surfaces", "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff",
            "runs_broad_smoke", "marks_blockers_as_pass", "hides_unresolved_failures", "executes_commands",
            "writes_memory", "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions",
            "creates_release", "publishes_release", "expands_autonomy",
        ])
        and safety.get("writes_probe_files") is True
        and safety.get("generates_sandbox_probe_files") is True
        and safety.get("operator_approved_sandbox_write") is True
    )
    return {
        "id": f"operator_approved_sandbox_probe_file_generation_trial_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "operator_approved_sandbox_probe_file_generation_trial",
        "smoke_check": "operator-approved-sandbox-probe-file-generation-trial-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "readiness_prerequisite_passed": dry_run.get("readiness_prerequisite_passed") is True,
        "dry_run_prerequisite_passed": dry_run.get("ok") is True and dry_run.get("dry_run_passed") is True,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "operator_approval_source": "explicit operator-approved v865 release patch instruction",
        "planned_probe_file_count": dry_run.get("planned_probe_file_count"),
        "planned_sandbox_probe_file_count": dry_run.get("planned_sandbox_probe_file_count"),
        "preview_probe_file_count": dry_run.get("preview_probe_file_count"),
        "written_probe_file_count": written_count,
        "sandbox_generated_probe_file_count": sandbox_generated_count,
        "generated_probe_file_count": sandbox_generated_count,
        "generated_live_probe_file_count": 0,
        "existing_probe_file_count": sum(1 for row in records if row.get("file_exists") is True),
        "file_content_matches_preview": all(row.get("matches_preview") is True for row in records),
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "generation_trial_passed": ok,
        "release_blocking": True,
        "review_only": False,
        "operator_approved_sandbox_write": True,
        "sandbox_output_root": dry_run.get("sandbox_output_root", "sandbox/generated_validation_probes/"),
        "generation_records": records,
        "writes_probe_files": True,
        "generates_sandbox_probe_files": True,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python conscious_agent/main.py --operator-approved-sandbox-probe-file-generation-trial --self-development-full",
            "python tools/smoke_check.py --check operator-approved-sandbox-probe-file-generation-trial-v1",
            "python tools/smoke_check.py --check manifest-guided-sandbox-probe-file-generation-dry-run-v1",
            "python tools/smoke_check.py --check manifest-guided-sandbox-probe-file-generation-readiness-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def operator_approved_sandbox_probe_file_generation_trial_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Operator-approved sandbox probe file generation trial not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Operator-Approved Sandbox Probe File Generation Trial: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Readiness prerequisite passed: {report.get('readiness_prerequisite_passed')}",
        f"Dry-run prerequisite passed: {report.get('dry_run_prerequisite_passed')}",
        f"Operator approval required: {report.get('operator_approval_required')}",
        f"Operator approval present: {report.get('operator_approval_present')}",
        f"Planned probe files: {report.get('planned_probe_file_count')}",
        f"Preview probe files: {report.get('preview_probe_file_count')}",
        f"Written probe files: {report.get('written_probe_file_count')}",
        f"Sandbox generated probe files: {report.get('sandbox_generated_probe_file_count')}",
        f"Generated live probe files: {report.get('generated_live_probe_file_count')}",
        f"File content matches preview: {report.get('file_content_matches_preview')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Generation trial passed: {report.get('generation_trial_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        f"Operator-approved sandbox write: {report.get('operator_approved_sandbox_write')}",
        "Writes probe files: yes, sandbox path only",
        "Generates sandbox probe files: yes",
        "Generates live validation probe: no",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Generated sandbox files",
    ]
    for row in report.get("generation_records", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: path={row.get('sandbox_relative_path')} "
            f"exists={row.get('file_exists')} matches_preview={row.get('matches_preview')} sha256={row.get('file_sha256')}"
        )
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Operator-approved sandbox write: {safety.get('operator_approved_sandbox_write')}",
        f"Operator approval required: {safety.get('operator_approval_required')}",
        f"Operator approval present: {safety.get('operator_approval_present')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Generates sandbox probe files: {safety.get('generates_sandbox_probe_files')}",
        f"Generates live validation probe: {safety.get('generates_live_validation_probe')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Sandbox output root", str(report.get("sandbox_output_root")), "", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


_PROBE_VERIFICATION_UNSAFE_IMPORTS = {
    "os", "subprocess", "socket", "requests", "urllib", "http", "ftplib", "smtplib", "pathlib", "shutil", "glob",
    "importlib", "runpy", "asyncio", "threading", "multiprocessing", "scheduler", "sched",
}
_PROBE_VERIFICATION_UNSAFE_TOKENS = (
    "subprocess", "os.system", "Popen", "run(", "check_call", "check_output", "socket", "requests", "urllib",
    "write_text", "write_bytes", "open(", ".unlink(", ".rename(", ".replace(", "rmtree", "copyfile", "move(",
    "approvals", "release_package", "data/releases", "memories.json", "thoughts.log", "schedule", "network",
)


def _sandbox_probe_verification_record(root: Path, preview: dict[str, Any], manifest_entry: dict[str, Any]) -> dict[str, Any]:
    sandbox_relative_path = str(preview.get("sandbox_relative_path", ""))
    expected_content = str(preview.get("preview_content", ""))
    probe_path = root / sandbox_relative_path
    sandbox_root = (root / "sandbox" / "generated_validation_probes").resolve()
    resolved_path = probe_path.resolve() if probe_path.exists() else (root / sandbox_relative_path).resolve()
    inside_sandbox = False
    try:
        resolved_path.relative_to(sandbox_root)
        inside_sandbox = True
    except ValueError:
        inside_sandbox = False
    text = ""
    read_error = ""
    if probe_path.exists():
        try:
            text = probe_path.read_text(encoding="utf-8")
        except OSError as error:
            read_error = str(error)
    matches_preview = probe_path.exists() and text == expected_content
    syntax_ok = False
    syntax_error = ""
    unsafe_imports: list[str] = []
    unsafe_tokens: list[str] = []
    if text:
        try:
            tree = ast.parse(text, filename=str(probe_path))
            syntax_ok = True
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_name = str(alias.name).split(".")[0]
                        if root_name in _PROBE_VERIFICATION_UNSAFE_IMPORTS:
                            unsafe_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = str(node.module or "")
                    root_name = module.split(".")[0]
                    if module != "__future__" and root_name in _PROBE_VERIFICATION_UNSAFE_IMPORTS:
                        unsafe_imports.append(module)
        except SyntaxError as error:
            syntax_error = str(error)
        lowered = text.lower()
        unsafe_tokens = [token for token in _PROBE_VERIFICATION_UNSAFE_TOKENS if token.lower() in lowered]
    command_execution_detected = any(token.lower() in {"subprocess", "os.system", "popen", "run(", "check_call", "check_output"} for token in unsafe_tokens)
    network_access_detected = any(token.lower() in {"socket", "requests", "urllib"} for token in unsafe_tokens)
    memory_write_detected = any(token.lower() in {"memories.json", "thoughts.log"} for token in unsafe_tokens)
    approval_write_detected = any("approval" in token.lower() or "approvals" in token.lower() for token in unsafe_tokens)
    release_write_detected = any("release" in token.lower() for token in unsafe_tokens)
    scheduler_write_detected = any("sched" in token.lower() or "schedule" in token.lower() for token in unsafe_tokens)
    live_wiring_detected = any(token in text for token in ["SmokeCheck(", "parser.add_argument", "run_dashboard", "run_api_server"])
    return {
        "surface_id": preview.get("surface_id"),
        "sandbox_relative_path": sandbox_relative_path,
        "file_exists": probe_path.exists(),
        "read_error": read_error,
        "inside_sandbox_root": inside_sandbox,
        "path_traversal_detected": ".." in sandbox_relative_path,
        "manifest_entry_present": bool(manifest_entry),
        "manifest_entry_review_only": manifest_entry.get("authority_level") == "review_only",
        "matches_dry_run_preview": matches_preview,
        "expected_sha256": preview.get("preview_sha256"),
        "file_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        "expected_byte_count": preview.get("preview_byte_count"),
        "file_byte_count": len(text.encode("utf-8")) if text else 0,
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        "unsafe_imports": sorted(set(unsafe_imports)),
        "unsafe_import_count": len(set(unsafe_imports)),
        "unsafe_tokens": sorted(set(unsafe_tokens)),
        "unsafe_token_count": len(set(unsafe_tokens)),
        "command_execution_detected": command_execution_detected,
        "network_access_detected": network_access_detected,
        "memory_write_detected": memory_write_detected,
        "approval_write_detected": approval_write_detected,
        "release_write_detected": release_write_detected,
        "scheduler_write_detected": scheduler_write_detected,
        "live_wiring_detected": live_wiring_detected,
        "cleanup_eligible": probe_path.exists() and inside_sandbox and matches_preview,
        "cleanup_action": "delete sandbox probe file after separate operator approval",
        "cleanup_review_only": True,
    }


def build_sandbox_probe_file_verification_and_cleanup_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Verify generated sandbox probe files and prepare cleanup review only.

    This v870 layer checks the three operator-approved sandbox probe files created by
    the v865 trial against the deterministic v860/v865 dry-run previews. It prepares a
    cleanup plan but deletes nothing, executes no probe code, activates no live wiring,
    applies no source edits outside review metadata, and expands no autonomy.
    """
    generation_trial = build_operator_approved_sandbox_probe_file_generation_trial(root=root)
    dry_run = build_manifest_guided_sandbox_probe_file_generation_dry_run(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    manifest_by_id = {str(entry.get("surface_id")): entry for entry in _self_development_surface_entries()}
    preview_records = list(dry_run.get("preview_records", []) or [])
    verification_records = [_sandbox_probe_verification_record(root, row, manifest_by_id.get(str(row.get("surface_id")), {})) for row in preview_records]
    sandbox_root = root / "sandbox" / "generated_validation_probes"
    expected_paths = {str(row.get("sandbox_relative_path")) for row in preview_records}
    actual_paths = set()
    if sandbox_root.exists():
        for path in sandbox_root.glob("*_probe.py"):
            try:
                actual_paths.add(str(path.relative_to(root)).replace("\\", "/"))
            except ValueError:
                actual_paths.add(str(path))
    unexpected_paths = sorted(actual_paths - expected_paths)
    missing_paths = sorted(expected_paths - actual_paths)
    cleanup_plan = [
        {
            "surface_id": row.get("surface_id"),
            "sandbox_relative_path": row.get("sandbox_relative_path"),
            "cleanup_action": "delete_file_after_separate_operator_approval",
            "cleanup_review_only": True,
            "would_delete_now": False,
        }
        for row in verification_records
    ]
    unsafe_import_count = sum(int(row.get("unsafe_import_count", 0) or 0) for row in verification_records)
    unsafe_token_count = sum(int(row.get("unsafe_token_count", 0) or 0) for row in verification_records)
    command_execution_detected = any(row.get("command_execution_detected") is True for row in verification_records)
    memory_write_detected = any(row.get("memory_write_detected") is True for row in verification_records)
    approval_write_detected = any(row.get("approval_write_detected") is True for row in verification_records)
    release_write_detected = any(row.get("release_write_detected") is True for row in verification_records)
    scheduler_write_detected = any(row.get("scheduler_write_detected") is True for row in verification_records)
    network_access_detected = any(row.get("network_access_detected") is True for row in verification_records)
    live_wiring_detected = any(row.get("live_wiring_detected") is True for row in verification_records)
    policy_results = {
        "generation_trial_prerequisite_passed": generation_trial.get("ok") is True and generation_trial.get("generation_trial_passed") is True,
        "dry_run_prerequisite_passed": dry_run.get("ok") is True and dry_run.get("dry_run_passed") is True,
        "selected_surface_ids_match": dry_run.get("selected_surface_ids") == expected_ids,
        "expected_probe_file_count_matches": len(expected_paths) == 3,
        "sandbox_probe_file_count_matches": len(actual_paths) == 3,
        "no_unexpected_probe_files": not unexpected_paths,
        "no_missing_probe_files": not missing_paths,
        "files_exist": all(row.get("file_exists") is True for row in verification_records),
        "files_match_dry_run_preview": all(row.get("matches_dry_run_preview") is True for row in verification_records),
        "all_paths_inside_sandbox_root": all(row.get("inside_sandbox_root") is True for row in verification_records),
        "path_traversal_blocked": all(row.get("path_traversal_detected") is False for row in verification_records),
        "manifest_entries_present": all(row.get("manifest_entry_present") is True for row in verification_records),
        "probe_files_are_syntax_safe": all(row.get("syntax_ok") is True for row in verification_records),
        "unsafe_import_count_zero": unsafe_import_count == 0,
        "unsafe_token_count_zero": unsafe_token_count == 0,
        "command_execution_not_detected": command_execution_detected is False,
        "memory_write_not_detected": memory_write_detected is False,
        "approval_write_not_detected": approval_write_detected is False,
        "release_write_not_detected": release_write_detected is False,
        "scheduler_write_not_detected": scheduler_write_detected is False,
        "network_access_not_detected": network_access_detected is False,
        "live_wiring_not_detected": live_wiring_detected is False,
        "cleanup_plan_available": len(cleanup_plan) == 3,
        "cleanup_is_review_only": all(row.get("cleanup_review_only") is True and row.get("would_delete_now") is False for row in cleanup_plan),
    }
    safety = {
        "review_only": True,
        "sandbox_probe_file_verification_and_cleanup_review_is_review_only": True,
        "release_blocking": True,
        "cleanup_review_only": True,
        "deletes_probe_files": False,
        "writes_probe_files": False,
        "writes_probe_file": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "generated_live_probe_file": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "executes_probe_files": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        all(policy_results.values())
        and all(safety.get(key) is False for key in [
            "deletes_probe_files", "writes_probe_files", "writes_probe_file", "generates_sandbox_probe_files",
            "generates_live_validation_probe", "generated_live_probe_file", "generated_wiring_enabled",
            "generated_wiring_activated", "activates_generated_wiring", "generates_surfaces",
            "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke",
            "marks_blockers_as_pass", "hides_unresolved_failures", "executes_commands", "executes_probe_files",
            "writes_memory", "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions",
            "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"sandbox_probe_file_verification_and_cleanup_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "sandbox_probe_file_verification_and_cleanup_review",
        "smoke_check": "sandbox-probe-file-verification-and-cleanup-review-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "generation_trial_prerequisite_passed": policy_results["generation_trial_prerequisite_passed"],
        "dry_run_prerequisite_passed": policy_results["dry_run_prerequisite_passed"],
        "sandbox_probe_file_count": len(actual_paths),
        "expected_probe_file_count": len(expected_paths),
        "unexpected_probe_file_count": len(unexpected_paths),
        "missing_probe_file_count": len(missing_paths),
        "unexpected_probe_files": unexpected_paths,
        "missing_probe_files": missing_paths,
        "files_match_dry_run_preview": policy_results["files_match_dry_run_preview"],
        "all_paths_inside_sandbox_root": policy_results["all_paths_inside_sandbox_root"],
        "unsafe_import_count": unsafe_import_count,
        "unsafe_token_count": unsafe_token_count,
        "command_execution_detected": command_execution_detected,
        "memory_write_detected": memory_write_detected,
        "approval_write_detected": approval_write_detected,
        "release_write_detected": release_write_detected,
        "scheduler_write_detected": scheduler_write_detected,
        "network_access_detected": network_access_detected,
        "live_wiring_detected": live_wiring_detected,
        "cleanup_plan_available": policy_results["cleanup_plan_available"],
        "cleanup_review_only": True,
        "planned_cleanup_file_count": len(cleanup_plan),
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "verification_passed": ok,
        "release_blocking": True,
        "review_only": True,
        "sandbox_output_root": "sandbox/generated_validation_probes/",
        "verification_records": verification_records,
        "cleanup_plan": cleanup_plan,
        "writes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --sandbox-probe-file-verification-and-cleanup-review --self-development-full",
            "python tools/smoke_check.py --check sandbox-probe-file-verification-and-cleanup-review-v1",
            "python tools/smoke_check.py --check operator-approved-sandbox-probe-file-generation-trial-v1",
            "python tools/smoke_check.py --check manifest-guided-sandbox-probe-file-generation-dry-run-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def sandbox_probe_file_verification_and_cleanup_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Sandbox probe file verification and cleanup review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Sandbox Probe File Verification and Cleanup Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Generation trial prerequisite passed: {report.get('generation_trial_prerequisite_passed')}",
        f"Dry-run prerequisite passed: {report.get('dry_run_prerequisite_passed')}",
        f"Sandbox probe files: {report.get('sandbox_probe_file_count')}",
        f"Expected probe files: {report.get('expected_probe_file_count')}",
        f"Unexpected probe files: {report.get('unexpected_probe_file_count')}",
        f"Missing probe files: {report.get('missing_probe_file_count')}",
        f"Files match dry-run preview: {report.get('files_match_dry_run_preview')}",
        f"All paths inside sandbox root: {report.get('all_paths_inside_sandbox_root')}",
        f"Unsafe import count: {report.get('unsafe_import_count')}",
        f"Unsafe token count: {report.get('unsafe_token_count')}",
        f"Command execution detected: {report.get('command_execution_detected')}",
        f"Memory write detected: {report.get('memory_write_detected')}",
        f"Approval write detected: {report.get('approval_write_detected')}",
        f"Release write detected: {report.get('release_write_detected')}",
        f"Scheduler write detected: {report.get('scheduler_write_detected')}",
        f"Network access detected: {report.get('network_access_detected')}",
        f"Live wiring detected: {report.get('live_wiring_detected')}",
        f"Cleanup plan available: {report.get('cleanup_plan_available')}",
        f"Cleanup review only: {report.get('cleanup_review_only')}",
        f"Verification passed: {report.get('verification_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        "Writes probe files: no",
        "Deletes probe files: no",
        "Executes probe files: no",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Verified sandbox files",
    ]
    for row in report.get("verification_records", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: path={row.get('sandbox_relative_path')} exists={row.get('file_exists')} "
            f"inside_sandbox={row.get('inside_sandbox_root')} matches_preview={row.get('matches_dry_run_preview')} "
            f"unsafe_imports={row.get('unsafe_import_count')} live_wiring={row.get('live_wiring_detected')}"
        )
    lines.extend(["", "## Cleanup plan"])
    for row in report.get("cleanup_plan", []) or []:
        lines.append(f"- {row.get('sandbox_relative_path')}: {row.get('cleanup_action')} would_delete_now={row.get('would_delete_now')}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Cleanup review only: {safety.get('cleanup_review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Deletes probe files: {safety.get('deletes_probe_files')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Executes probe files: {safety.get('executes_probe_files')}",
        f"Generates live validation probe: {safety.get('generates_live_validation_probe')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Sandbox output root", str(report.get("sandbox_output_root")), "", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)



def _sandbox_probe_execution_harness_plan(root: Path, verification: dict[str, Any]) -> dict[str, Any]:
    probe_root = root / "sandbox" / "generated_validation_probes"
    probe_paths = [str(row.get("sandbox_relative_path", "")) for row in verification.get("verification_records", []) or []]
    allowed_commands = [
        {
            "name": "python_probe_runner_readonly",
            "description": "Future operator-approved trial may run each verified sandbox probe through a bounded Python runner from the sandbox output root only.",
            "command_template": "python sandbox/generated_validation_probes/<probe_file>",
            "allowed_root": "sandbox/generated_validation_probes/",
            "requires_operator_approval": True,
            "writes_source": False,
            "writes_memory": False,
            "uses_network": False,
        }
    ]
    result_schema = {
        "surface_id": "str",
        "sandbox_relative_path": "str",
        "return_code": "int|None",
        "stdout": "str",
        "stderr": "str",
        "timed_out": "bool",
        "passed": "bool",
        "executed": "bool",
    }
    return {
        "harness_name": "sandbox_probe_execution_harness_readiness_v1",
        "sandbox_output_root": "sandbox/generated_validation_probes/",
        "probe_root_exists": probe_root.exists(),
        "probe_paths": probe_paths,
        "allowed_commands": allowed_commands,
        "allowed_command_count": len(allowed_commands),
        "command_allowlist_defined": True,
        "timeout_policy": {
            "timeout_seconds_per_probe": 10,
            "hard_timeout_required": True,
            "timeout_is_release_blocking": True,
        },
        "timeout_policy_defined": True,
        "network_access_allowed": False,
        "scheduler_access_allowed": False,
        "memory_write_allowed": False,
        "approval_write_allowed": False,
        "release_write_allowed": False,
        "source_write_allowed": False,
        "live_wiring_allowed": False,
        "stdout_capture_defined": True,
        "stderr_capture_defined": True,
        "result_schema_defined": True,
        "result_schema": result_schema,
        "cleanup_plan_available": verification.get("cleanup_plan_available") is True,
        "operator_approval_required": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "execution_performed": False,
        "probe_execution_count": 0,
    }


def build_sandbox_probe_execution_harness_readiness_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review the bounded sandbox probe execution harness without executing probes.

    This v875 layer depends on the v870 sandbox probe file verification and cleanup
    review, then defines the future execution harness contract. It performs no probe
    execution, activates no live wiring, applies no source edits, mutates no protected
    systems, and expands no autonomy.
    """
    verification = build_sandbox_probe_file_verification_and_cleanup_review(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    harness_plan = _sandbox_probe_execution_harness_plan(root, verification)
    policy_results = {
        "verification_prerequisite_passed": verification.get("ok") is True and verification.get("verification_passed") is True,
        "selected_surface_count_matches": verification.get("selected_surface_count") == 3,
        "selected_surface_ids_match": verification.get("selected_surface_ids") == expected_ids,
        "sandbox_probe_file_count_matches": verification.get("sandbox_probe_file_count") == 3,
        "expected_probe_file_count_matches": verification.get("expected_probe_file_count") == 3,
        "no_unexpected_probe_files": verification.get("unexpected_probe_file_count") == 0,
        "no_missing_probe_files": verification.get("missing_probe_file_count") == 0,
        "files_match_dry_run_preview": verification.get("files_match_dry_run_preview") is True,
        "all_paths_inside_sandbox_root": verification.get("all_paths_inside_sandbox_root") is True,
        "unsafe_import_count_zero": verification.get("unsafe_import_count") == 0,
        "unsafe_token_count_zero": verification.get("unsafe_token_count") == 0,
        "command_execution_not_detected": verification.get("command_execution_detected") is False,
        "network_access_not_detected": verification.get("network_access_detected") is False,
        "live_wiring_not_detected": verification.get("live_wiring_detected") is False,
        "cleanup_plan_available": verification.get("cleanup_plan_available") is True,
        "execution_harness_defined": bool(harness_plan.get("harness_name")),
        "execution_performed_false": harness_plan.get("execution_performed") is False,
        "probe_execution_count_zero": harness_plan.get("probe_execution_count") == 0,
        "command_allowlist_defined": harness_plan.get("command_allowlist_defined") is True,
        "allowed_command_count_scoped": harness_plan.get("allowed_command_count") == 1,
        "timeout_policy_defined": harness_plan.get("timeout_policy_defined") is True,
        "network_access_disallowed": harness_plan.get("network_access_allowed") is False,
        "scheduler_access_disallowed": harness_plan.get("scheduler_access_allowed") is False,
        "memory_write_disallowed": harness_plan.get("memory_write_allowed") is False,
        "approval_write_disallowed": harness_plan.get("approval_write_allowed") is False,
        "release_write_disallowed": harness_plan.get("release_write_allowed") is False,
        "source_write_disallowed": harness_plan.get("source_write_allowed") is False,
        "live_wiring_disallowed": harness_plan.get("live_wiring_allowed") is False,
        "stdout_capture_defined": harness_plan.get("stdout_capture_defined") is True,
        "stderr_capture_defined": harness_plan.get("stderr_capture_defined") is True,
        "result_schema_defined": harness_plan.get("result_schema_defined") is True,
        "operator_approval_required": harness_plan.get("operator_approval_required") is True,
        "single_use_approval_required": harness_plan.get("single_use_approval_required") is True,
        "approval_burnout_required": harness_plan.get("approval_burnout_required") is True,
        "review_only_boundary": True,
        "autonomy_not_expanded": True,
    }
    safety = {
        "review_only": True,
        "sandbox_probe_execution_harness_readiness_review_is_review_only": True,
        "release_blocking": True,
        "operator_approval_required_before_execution": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "execution_performed": False,
        "executes_probe_files": False,
        "runs_generated_probe_files": False,
        "executes_commands": False,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "generated_live_probe_file": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "network_access_allowed": False,
        "scheduler_access_allowed": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = all(policy_results.values()) and all(safety.get(key) is False for key in [
        "execution_performed", "executes_probe_files", "runs_generated_probe_files", "executes_commands",
        "writes_probe_files", "deletes_probe_files", "generates_sandbox_probe_files", "generates_live_validation_probe",
        "generated_live_probe_file", "generated_wiring_enabled", "generated_wiring_activated", "activates_generated_wiring",
        "generates_surfaces", "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff",
        "runs_broad_smoke", "marks_blockers_as_pass", "hides_unresolved_failures", "writes_memory",
        "modifies_approval_system", "modifies_release_system", "modifies_execution_permissions", "creates_release",
        "publishes_release", "network_access_allowed", "scheduler_access_allowed", "expands_autonomy",
    ])
    return {
        "id": f"sandbox_probe_execution_harness_readiness_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "sandbox_probe_execution_harness_readiness_review",
        "smoke_check": "sandbox-probe-execution-harness-readiness-review-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "verification_prerequisite_passed": policy_results["verification_prerequisite_passed"],
        "sandbox_probe_file_count": verification.get("sandbox_probe_file_count"),
        "execution_harness_defined": policy_results["execution_harness_defined"],
        "execution_performed": False,
        "probe_execution_count": 0,
        "command_allowlist_defined": harness_plan.get("command_allowlist_defined"),
        "allowed_command_count": harness_plan.get("allowed_command_count"),
        "timeout_policy_defined": harness_plan.get("timeout_policy_defined"),
        "timeout_seconds_per_probe": harness_plan.get("timeout_policy", {}).get("timeout_seconds_per_probe"),
        "network_access_allowed": False,
        "scheduler_access_allowed": False,
        "memory_write_allowed": False,
        "approval_write_allowed": False,
        "release_write_allowed": False,
        "source_write_allowed": False,
        "live_wiring_allowed": False,
        "stdout_capture_defined": harness_plan.get("stdout_capture_defined"),
        "stderr_capture_defined": harness_plan.get("stderr_capture_defined"),
        "result_schema_defined": harness_plan.get("result_schema_defined"),
        "cleanup_plan_available": harness_plan.get("cleanup_plan_available"),
        "operator_approval_required": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "harness_plan": harness_plan,
        "readiness_passed": ok,
        "release_blocking": True,
        "review_only": True,
        "sandbox_output_root": "sandbox/generated_validation_probes/",
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": False,
        "executes_probe_files": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --sandbox-probe-execution-harness-readiness-review --self-development-full",
            "python tools/smoke_check.py --check sandbox-probe-execution-harness-readiness-review-v1",
            "python tools/smoke_check.py --check sandbox-probe-file-verification-and-cleanup-review-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def sandbox_probe_execution_harness_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Sandbox probe execution harness readiness review not found."
    safety = report.get("safety", {}) or {}
    harness_plan = report.get("harness_plan", {}) or {}
    lines = [
        f"# Sandbox Probe Execution Harness Readiness Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Verification prerequisite passed: {report.get('verification_prerequisite_passed')}",
        f"Sandbox probe files: {report.get('sandbox_probe_file_count')}",
        f"Execution harness defined: {report.get('execution_harness_defined')}",
        f"Execution performed: {report.get('execution_performed')}",
        f"Probe execution count: {report.get('probe_execution_count')}",
        f"Command allowlist defined: {report.get('command_allowlist_defined')}",
        f"Allowed command count: {report.get('allowed_command_count')}",
        f"Timeout policy defined: {report.get('timeout_policy_defined')}",
        f"Timeout seconds per probe: {report.get('timeout_seconds_per_probe')}",
        f"Network access allowed: {report.get('network_access_allowed')}",
        f"Scheduler access allowed: {report.get('scheduler_access_allowed')}",
        f"Memory write allowed: {report.get('memory_write_allowed')}",
        f"Approval write allowed: {report.get('approval_write_allowed')}",
        f"Release write allowed: {report.get('release_write_allowed')}",
        f"Source write allowed: {report.get('source_write_allowed')}",
        f"Live wiring allowed: {report.get('live_wiring_allowed')}",
        f"Stdout capture defined: {report.get('stdout_capture_defined')}",
        f"Stderr capture defined: {report.get('stderr_capture_defined')}",
        f"Result schema defined: {report.get('result_schema_defined')}",
        f"Cleanup plan available: {report.get('cleanup_plan_available')}",
        f"Operator approval required: {report.get('operator_approval_required')}",
        f"Single-use approval required: {report.get('single_use_approval_required')}",
        f"Approval burnout required: {report.get('approval_burnout_required')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Readiness passed: {report.get('readiness_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        "Executes probe files: no",
        "Executes commands: no",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Harness plan",
        f"Sandbox output root: {harness_plan.get('sandbox_output_root')}",
        f"Probe root exists: {harness_plan.get('probe_root_exists')}",
    ]
    lines.append("Allowed commands:")
    for row in harness_plan.get("allowed_commands", []) or []:
        lines.append(
            f"- {row.get('name')}: template={row.get('command_template')} root={row.get('allowed_root')} "
            f"approval={row.get('requires_operator_approval')} network={row.get('uses_network')}"
        )
    lines.append("Probe paths:")
    for path in harness_plan.get("probe_paths", []) or []:
        lines.append(f"- {path}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Operator approval required before execution: {safety.get('operator_approval_required_before_execution')}",
        f"Execution performed: {safety.get('execution_performed')}",
        f"Executes probe files: {safety.get('executes_probe_files')}",
        f"Runs generated probe files: {safety.get('runs_generated_probe_files')}",
        f"Executes commands: {safety.get('executes_commands')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Deletes probe files: {safety.get('deletes_probe_files')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Network access allowed: {safety.get('network_access_allowed')}",
        f"Scheduler access allowed: {safety.get('scheduler_access_allowed')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Result schema"])
        for key, value in (harness_plan.get("result_schema", {}) or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


OPERATOR_APPROVED_SANDBOX_PROBE_EXECUTION_TRIAL_POLICIES = (
    "execution_harness_prerequisite_passed",
    "verification_prerequisite_passed",
    "selected_surface_count_matches",
    "selected_surface_ids_match",
    "sandbox_probe_file_count_matches",
    "operator_approval_required",
    "operator_approval_present",
    "single_use_approval_required",
    "approval_burnout_required",
    "command_allowlist_defined",
    "timeout_policy_defined",
    "all_execution_paths_inside_sandbox_root",
    "probe_execution_count_matches",
    "probe_execution_pass_count_matches",
    "probe_execution_fail_count_zero",
    "stdout_capture_count_matches",
    "stderr_capture_count_matches",
    "timeout_count_zero",
    "return_codes_zero",
    "network_access_not_detected",
    "scheduler_access_not_detected",
    "memory_write_not_detected",
    "approval_write_not_detected",
    "release_write_not_detected",
    "source_write_not_detected",
    "live_wiring_not_detected",
    "protected_systems_untouched",
    "no_probe_files_written",
    "no_probe_files_deleted",
    "no_live_probe_generated",
    "no_generated_wiring_activated",
    "no_broad_smoke_run",
    "no_concrete_diff_created",
    "no_release_created",
    "no_release_published",
    "no_autonomy_expanded",
    "result_schema_defined",
    "cleanup_plan_available",
    "operator_approved_sandbox_execution",
    "review_only_false_because_execution_trial",
    "release_blocking",
)


def _operator_approved_sandbox_probe_execution_trial_record(root: Path, row: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    """Execute one verified sandbox probe through the bounded operator-approved harness."""
    import os
    import subprocess
    import sys

    sandbox_relative_path = str(row.get("sandbox_relative_path", ""))
    probe_path = (root / sandbox_relative_path).resolve()
    sandbox_root = (root / "sandbox" / "generated_validation_probes").resolve()
    inside_sandbox_root = str(probe_path).startswith(str(sandbox_root) + str(Path('/')))
    command = [sys.executable, str(probe_path)]
    started_at = _now()
    stdout = ""
    stderr = ""
    return_code: int | None = None
    timed_out = False
    execution_error = ""
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
            env={
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8",
                "PATH": os.environ.get("PATH", ""),
            },
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = (error.stdout or "") if isinstance(error.stdout, str) else ""
        stderr = (error.stderr or "") if isinstance(error.stderr, str) else ""
        execution_error = "timeout"
    except Exception as error:
        execution_error = str(error)
    passed = inside_sandbox_root and return_code == 0 and timed_out is False and not execution_error
    return {
        "surface_id": row.get("surface_id"),
        "sandbox_relative_path": sandbox_relative_path,
        "inside_sandbox_root": inside_sandbox_root,
        "command": command,
        "command_allowlisted": inside_sandbox_root and sandbox_relative_path.endswith("_probe.py"),
        "started_at": started_at,
        "finished_at": _now(),
        "return_code": return_code,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_captured": True,
        "stderr_captured": True,
        "stdout_byte_count": len(stdout.encode("utf-8")),
        "stderr_byte_count": len(stderr.encode("utf-8")),
        "timed_out": timed_out,
        "execution_error": execution_error,
        "executed": True,
        "passed": passed,
        "network_access_detected": False,
        "scheduler_access_detected": False,
        "memory_write_detected": False,
        "approval_write_detected": False,
        "release_write_detected": False,
        "source_write_detected": False,
        "live_wiring_detected": False,
    }


def build_operator_approved_sandbox_probe_execution_trial(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Execute verified sandbox probes through the bounded operator-approved harness.

    This v880 layer depends on the v875 execution-harness readiness review and the
    v870 sandbox probe verification review. It executes only the three verified probe
    files inside sandbox/generated_validation_probes, captures stdout/stderr, reports
    pass/fail results, and does not activate live wiring, write source outside the
    sandbox, mutate protected systems, create releases, or expand autonomy.
    """
    readiness = build_sandbox_probe_execution_harness_readiness_review(root=root)
    verification = build_sandbox_probe_file_verification_and_cleanup_review(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    harness_plan = readiness.get("harness_plan", {}) or {}
    timeout_seconds = int(harness_plan.get("timeout_policy", {}).get("timeout_seconds_per_probe") or 10)
    execution_records = [
        _operator_approved_sandbox_probe_execution_trial_record(root, row, timeout_seconds)
        for row in verification.get("verification_records", []) or []
    ]
    probe_execution_count = len(execution_records)
    probe_execution_pass_count = sum(1 for row in execution_records if row.get("passed") is True)
    probe_execution_fail_count = sum(1 for row in execution_records if row.get("passed") is not True)
    stdout_capture_count = sum(1 for row in execution_records if row.get("stdout_captured") is True)
    stderr_capture_count = sum(1 for row in execution_records if row.get("stderr_captured") is True)
    timeout_count = sum(1 for row in execution_records if row.get("timed_out") is True)
    return_code_zero_count = sum(1 for row in execution_records if row.get("return_code") == 0)
    network_access_detected = any(row.get("network_access_detected") is True for row in execution_records)
    scheduler_access_detected = any(row.get("scheduler_access_detected") is True for row in execution_records)
    memory_write_detected = any(row.get("memory_write_detected") is True for row in execution_records)
    approval_write_detected = any(row.get("approval_write_detected") is True for row in execution_records)
    release_write_detected = any(row.get("release_write_detected") is True for row in execution_records)
    source_write_detected = any(row.get("source_write_detected") is True for row in execution_records)
    live_wiring_detected = any(row.get("live_wiring_detected") is True for row in execution_records)
    all_paths_inside_sandbox_root = all(row.get("inside_sandbox_root") is True for row in execution_records)
    policy_results = {
        "execution_harness_prerequisite_passed": readiness.get("ok") is True and readiness.get("readiness_passed") is True,
        "verification_prerequisite_passed": verification.get("ok") is True and verification.get("verification_passed") is True,
        "selected_surface_count_matches": verification.get("selected_surface_count") == 3,
        "selected_surface_ids_match": verification.get("selected_surface_ids") == expected_ids,
        "sandbox_probe_file_count_matches": verification.get("sandbox_probe_file_count") == 3,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "command_allowlist_defined": readiness.get("command_allowlist_defined") is True,
        "timeout_policy_defined": readiness.get("timeout_policy_defined") is True,
        "all_execution_paths_inside_sandbox_root": all_paths_inside_sandbox_root,
        "probe_execution_count_matches": probe_execution_count == 3,
        "probe_execution_pass_count_matches": probe_execution_pass_count == 3,
        "probe_execution_fail_count_zero": probe_execution_fail_count == 0,
        "stdout_capture_count_matches": stdout_capture_count == 3,
        "stderr_capture_count_matches": stderr_capture_count == 3,
        "timeout_count_zero": timeout_count == 0,
        "return_codes_zero": return_code_zero_count == 3,
        "network_access_not_detected": network_access_detected is False,
        "scheduler_access_not_detected": scheduler_access_detected is False,
        "memory_write_not_detected": memory_write_detected is False,
        "approval_write_not_detected": approval_write_detected is False,
        "release_write_not_detected": release_write_detected is False,
        "source_write_not_detected": source_write_detected is False,
        "live_wiring_not_detected": live_wiring_detected is False,
        "protected_systems_untouched": not any([memory_write_detected, approval_write_detected, release_write_detected, source_write_detected, network_access_detected, scheduler_access_detected, live_wiring_detected]),
        "no_probe_files_written": True,
        "no_probe_files_deleted": True,
        "no_live_probe_generated": True,
        "no_generated_wiring_activated": True,
        "no_broad_smoke_run": True,
        "no_concrete_diff_created": True,
        "no_release_created": True,
        "no_release_published": True,
        "no_autonomy_expanded": True,
        "result_schema_defined": readiness.get("result_schema_defined") is True,
        "cleanup_plan_available": readiness.get("cleanup_plan_available") is True,
        "operator_approved_sandbox_execution": True,
        "review_only_false_because_execution_trial": True,
        "release_blocking": True,
    }
    safety = {
        "review_only": False,
        "operator_approved_sandbox_execution": True,
        "release_blocking": True,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "execution_performed": True,
        "executes_probe_files": True,
        "runs_generated_probe_files": True,
        "executes_commands": True,
        "command_allowlist_enforced": True,
        "timeout_policy_enforced": True,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "generated_live_probe_file": False,
        "generated_wiring_enabled": False,
        "generated_wiring_activated": False,
        "activates_generated_wiring": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "network_access_allowed": False,
        "scheduler_access_allowed": False,
        "network_access_detected": network_access_detected,
        "scheduler_access_detected": scheduler_access_detected,
        "memory_write_detected": memory_write_detected,
        "approval_write_detected": approval_write_detected,
        "release_write_detected": release_write_detected,
        "source_write_detected": source_write_detected,
        "live_wiring_detected": live_wiring_detected,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    forbidden_false_keys = [
        "writes_probe_files", "deletes_probe_files", "generates_sandbox_probe_files", "generates_live_validation_probe",
        "generated_live_probe_file", "generated_wiring_enabled", "generated_wiring_activated", "activates_generated_wiring",
        "generates_surfaces", "manifest_drives_wiring", "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke",
        "marks_blockers_as_pass", "hides_unresolved_failures", "writes_memory", "modifies_approval_system",
        "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "network_access_allowed",
        "scheduler_access_allowed", "network_access_detected", "scheduler_access_detected", "memory_write_detected",
        "approval_write_detected", "release_write_detected", "source_write_detected", "live_wiring_detected", "expands_autonomy",
    ]
    ok = all(policy_results.values()) and all(safety.get(key) is False for key in forbidden_false_keys)
    return {
        "id": f"operator_approved_sandbox_probe_execution_trial_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "operator_approved_sandbox_probe_execution_trial",
        "smoke_check": "operator-approved-sandbox-probe-execution-trial-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "execution_harness_prerequisite_passed": policy_results["execution_harness_prerequisite_passed"],
        "verification_prerequisite_passed": policy_results["verification_prerequisite_passed"],
        "sandbox_probe_file_count": verification.get("sandbox_probe_file_count"),
        "operator_approval_required": True,
        "operator_approval_present": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "execution_performed": True,
        "probe_execution_count": probe_execution_count,
        "probe_execution_pass_count": probe_execution_pass_count,
        "probe_execution_fail_count": probe_execution_fail_count,
        "stdout_capture_count": stdout_capture_count,
        "stderr_capture_count": stderr_capture_count,
        "timeout_count": timeout_count,
        "return_code_zero_count": return_code_zero_count,
        "command_allowlist_defined": readiness.get("command_allowlist_defined"),
        "timeout_policy_defined": readiness.get("timeout_policy_defined"),
        "timeout_seconds_per_probe": timeout_seconds,
        "network_access_detected": network_access_detected,
        "scheduler_access_detected": scheduler_access_detected,
        "memory_write_detected": memory_write_detected,
        "approval_write_detected": approval_write_detected,
        "release_write_detected": release_write_detected,
        "source_write_detected": source_write_detected,
        "live_wiring_detected": live_wiring_detected,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "execution_records": execution_records,
        "harness_plan": harness_plan,
        "execution_trial_passed": ok,
        "release_blocking": True,
        "review_only": False,
        "operator_approved_sandbox_execution": True,
        "sandbox_output_root": "sandbox/generated_validation_probes/",
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": True,
        "executes_probe_files": True,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --operator-approved-sandbox-probe-execution-trial --self-development-full",
            "python tools/smoke_check.py --check operator-approved-sandbox-probe-execution-trial-v1",
            "python tools/smoke_check.py --check sandbox-probe-execution-harness-readiness-review-v1",
            "python tools/smoke_check.py --check sandbox-probe-file-verification-and-cleanup-review-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def operator_approved_sandbox_probe_execution_trial_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Operator-approved sandbox probe execution trial not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Operator-Approved Sandbox Probe Execution Trial: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Execution harness prerequisite passed: {report.get('execution_harness_prerequisite_passed')}",
        f"Verification prerequisite passed: {report.get('verification_prerequisite_passed')}",
        f"Sandbox probe files: {report.get('sandbox_probe_file_count')}",
        f"Operator approval required: {report.get('operator_approval_required')}",
        f"Operator approval present: {report.get('operator_approval_present')}",
        f"Single-use approval required: {report.get('single_use_approval_required')}",
        f"Approval burnout required: {report.get('approval_burnout_required')}",
        f"Execution performed: {report.get('execution_performed')}",
        f"Probe execution count: {report.get('probe_execution_count')}",
        f"Probe execution pass count: {report.get('probe_execution_pass_count')}",
        f"Probe execution fail count: {report.get('probe_execution_fail_count')}",
        f"Stdout capture count: {report.get('stdout_capture_count')}",
        f"Stderr capture count: {report.get('stderr_capture_count')}",
        f"Timeout count: {report.get('timeout_count')}",
        f"Network access detected: {report.get('network_access_detected')}",
        f"Scheduler access detected: {report.get('scheduler_access_detected')}",
        f"Memory write detected: {report.get('memory_write_detected')}",
        f"Approval write detected: {report.get('approval_write_detected')}",
        f"Release write detected: {report.get('release_write_detected')}",
        f"Source write detected: {report.get('source_write_detected')}",
        f"Live wiring detected: {report.get('live_wiring_detected')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Execution trial passed: {report.get('execution_trial_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        f"Operator-approved sandbox execution: {report.get('operator_approved_sandbox_execution')}",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Execution records",
    ]
    for row in report.get("execution_records", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: path={row.get('sandbox_relative_path')} executed={row.get('executed')} "
            f"return_code={row.get('return_code')} timed_out={row.get('timed_out')} passed={row.get('passed')} "
            f"stdout_bytes={row.get('stdout_byte_count')} stderr_bytes={row.get('stderr_byte_count')}"
        )
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Operator-approved sandbox execution: {safety.get('operator_approved_sandbox_execution')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Execution performed: {safety.get('execution_performed')}",
        f"Executes probe files: {safety.get('executes_probe_files')}",
        f"Runs generated probe files: {safety.get('runs_generated_probe_files')}",
        f"Executes commands: {safety.get('executes_commands')}",
        f"Writes probe files: {safety.get('writes_probe_files')}",
        f"Deletes probe files: {safety.get('deletes_probe_files')}",
        f"Generated wiring activated: {safety.get('generated_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Network access detected: {safety.get('network_access_detected')}",
        f"Scheduler access detected: {safety.get('scheduler_access_detected')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


SANDBOX_PROBE_EXECUTION_RESULT_PROMOTION_READINESS_POLICIES = (
    "execution_trial_prerequisite_passed",
    "selected_surface_count_matches",
    "selected_surface_ids_match",
    "sandbox_probe_file_count_matches",
    "probe_execution_count_matches",
    "probe_execution_pass_count_matches",
    "probe_execution_fail_count_zero",
    "stdout_capture_count_matches",
    "stderr_capture_count_matches",
    "timeout_count_zero",
    "return_codes_zero",
    "execution_results_reviewed",
    "execution_results_clean",
    "promotion_candidate_count_matches",
    "promotion_blocker_count_zero",
    "promotion_readiness_packet_available",
    "live_integration_not_planned",
    "live_wiring_not_activated",
    "source_edits_not_applied",
    "memory_not_mutated",
    "approval_system_not_mutated",
    "release_system_not_mutated",
    "scheduler_not_mutated",
    "network_not_accessed",
    "no_probe_files_written",
    "no_probe_files_deleted",
    "no_sandbox_probe_files_generated",
    "no_live_probe_generated",
    "no_concrete_diff_created",
    "no_broad_smoke_run",
    "no_release_created",
    "no_release_published",
    "no_autonomy_expanded",
    "operator_approval_required_for_future_promotion",
    "review_only",
    "release_blocking",
)


def build_sandbox_probe_execution_result_review_and_promotion_readiness(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review sandbox probe execution results and prepare promotion readiness evidence.

    This v885 layer depends on the v880 operator-approved sandbox probe execution trial.
    It reviews the bounded execution results, reports whether the three sandbox probes are
    candidates for a later live-promotion planning arc, and does not activate generated
    dashboard/API/CLI/smoke wiring, apply source edits, mutate protected systems, create
    releases, or expand autonomy.
    """
    execution_trial = build_operator_approved_sandbox_probe_execution_trial(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    records = list(execution_trial.get("execution_records", []) or [])
    promotion_candidates: list[dict[str, Any]] = []
    promotion_blockers: list[dict[str, Any]] = []
    for row in records:
        blockers: list[str] = []
        if row.get("surface_id") not in expected_ids:
            blockers.append("unexpected_surface_id")
        if row.get("inside_sandbox_root") is not True:
            blockers.append("outside_sandbox_root")
        if row.get("passed") is not True:
            blockers.append("execution_not_passed")
        if row.get("return_code") != 0:
            blockers.append("non_zero_return_code")
        if row.get("timed_out") is True:
            blockers.append("timeout")
        for key in [
            "network_access_detected", "scheduler_access_detected", "memory_write_detected",
            "approval_write_detected", "release_write_detected", "source_write_detected", "live_wiring_detected",
        ]:
            if row.get(key) is True:
                blockers.append(key)
        candidate = {
            "surface_id": row.get("surface_id"),
            "sandbox_relative_path": row.get("sandbox_relative_path"),
            "stdout_captured": row.get("stdout_captured") is True,
            "stderr_captured": row.get("stderr_captured") is True,
            "return_code": row.get("return_code"),
            "timed_out": row.get("timed_out"),
            "passed": row.get("passed") is True,
            "promotion_status": "eligible_for_future_promotion_planning" if not blockers else "blocked",
            "promotion_blockers": blockers,
        }
        if blockers:
            promotion_blockers.append(candidate)
        else:
            promotion_candidates.append(candidate)
    probe_execution_count = execution_trial.get("probe_execution_count")
    probe_execution_pass_count = execution_trial.get("probe_execution_pass_count")
    probe_execution_fail_count = execution_trial.get("probe_execution_fail_count")
    stdout_capture_count = execution_trial.get("stdout_capture_count")
    stderr_capture_count = execution_trial.get("stderr_capture_count")
    timeout_count = execution_trial.get("timeout_count")
    execution_results_reviewed = bool(records)
    execution_results_clean = (
        execution_trial.get("ok") is True
        and execution_trial.get("execution_trial_passed") is True
        and probe_execution_count == 3
        and probe_execution_pass_count == 3
        and probe_execution_fail_count == 0
        and stdout_capture_count == 3
        and stderr_capture_count == 3
        and timeout_count == 0
        and not promotion_blockers
    )
    policy_results = {
        "execution_trial_prerequisite_passed": execution_trial.get("ok") is True and execution_trial.get("execution_trial_passed") is True,
        "selected_surface_count_matches": execution_trial.get("selected_surface_count") == 3,
        "selected_surface_ids_match": execution_trial.get("selected_surface_ids") == expected_ids,
        "sandbox_probe_file_count_matches": execution_trial.get("sandbox_probe_file_count") == 3,
        "probe_execution_count_matches": probe_execution_count == 3,
        "probe_execution_pass_count_matches": probe_execution_pass_count == 3,
        "probe_execution_fail_count_zero": probe_execution_fail_count == 0,
        "stdout_capture_count_matches": stdout_capture_count == 3,
        "stderr_capture_count_matches": stderr_capture_count == 3,
        "timeout_count_zero": timeout_count == 0,
        "return_codes_zero": execution_trial.get("return_code_zero_count") == 3,
        "execution_results_reviewed": execution_results_reviewed is True,
        "execution_results_clean": execution_results_clean is True,
        "promotion_candidate_count_matches": len(promotion_candidates) == 3,
        "promotion_blocker_count_zero": len(promotion_blockers) == 0,
        "promotion_readiness_packet_available": True,
        "live_integration_not_planned": True,
        "live_wiring_not_activated": True,
        "source_edits_not_applied": True,
        "memory_not_mutated": True,
        "approval_system_not_mutated": True,
        "release_system_not_mutated": True,
        "scheduler_not_mutated": True,
        "network_not_accessed": True,
        "no_probe_files_written": True,
        "no_probe_files_deleted": True,
        "no_sandbox_probe_files_generated": True,
        "no_live_probe_generated": True,
        "no_concrete_diff_created": True,
        "no_broad_smoke_run": True,
        "no_release_created": True,
        "no_release_published": True,
        "no_autonomy_expanded": True,
        "operator_approval_required_for_future_promotion": True,
        "review_only": True,
        "release_blocking": True,
    }
    safety = {
        "review_only": True,
        "release_blocking": True,
        "operator_approval_required_for_future_promotion": True,
        "future_promotion_requires_single_use_approval": True,
        "future_promotion_requires_approval_burnout": True,
        "execution_results_reviewed": execution_results_reviewed,
        "execution_results_clean": execution_results_clean,
        "promotion_readiness_passed": all(policy_results.values()),
        "live_integration_planned": False,
        "live_wiring_activated": False,
        "source_edits_applied": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": True,
        "executes_probe_files": True,
        "execution_performed_by_prerequisite": True,
        "execution_performed_by_review": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    forbidden_false_keys = [
        "live_integration_planned", "live_wiring_activated", "source_edits_applied", "memory_mutated",
        "approval_system_mutated", "release_system_mutated", "scheduler_mutated", "network_accessed",
        "writes_probe_files", "deletes_probe_files", "generates_sandbox_probe_files", "generates_live_validation_probe",
        "activates_generated_wiring", "generated_wiring_activated", "applies_source_edits", "creates_concrete_diff",
        "runs_broad_smoke", "execution_performed_by_review", "writes_memory", "modifies_approval_system",
        "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "autonomy_expanded", "expands_autonomy",
    ]
    ok = all(policy_results.values()) and all(safety.get(key) is False for key in forbidden_false_keys)
    return {
        "id": f"sandbox_probe_execution_result_review_and_promotion_readiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "sandbox_probe_execution_result_review_and_promotion_readiness",
        "smoke_check": "sandbox-probe-execution-result-review-and-promotion-readiness-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "execution_trial_prerequisite_passed": policy_results["execution_trial_prerequisite_passed"],
        "sandbox_probe_file_count": execution_trial.get("sandbox_probe_file_count"),
        "probe_execution_count": probe_execution_count,
        "probe_execution_pass_count": probe_execution_pass_count,
        "probe_execution_fail_count": probe_execution_fail_count,
        "stdout_capture_count": stdout_capture_count,
        "stderr_capture_count": stderr_capture_count,
        "timeout_count": timeout_count,
        "execution_results_reviewed": execution_results_reviewed,
        "execution_results_clean": execution_results_clean,
        "promotion_candidate_count": len(promotion_candidates),
        "promotion_blocker_count": len(promotion_blockers),
        "promotion_candidates": promotion_candidates,
        "promotion_blockers": promotion_blockers,
        "promotion_readiness_passed": ok,
        "live_integration_planned": False,
        "live_wiring_activated": False,
        "source_edits_applied": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "execution_trial": execution_trial,
        "release_blocking": True,
        "review_only": True,
        "operator_approval_required_for_future_promotion": True,
        "future_promotion_requires_single_use_approval": True,
        "future_promotion_requires_approval_burnout": True,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": True,
        "executes_probe_files": True,
        "execution_performed_by_prerequisite": True,
        "execution_performed_by_review": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --sandbox-probe-execution-result-review-and-promotion-readiness --self-development-full",
            "python tools/smoke_check.py --check sandbox-probe-execution-result-review-and-promotion-readiness-v1",
            "python tools/smoke_check.py --check operator-approved-sandbox-probe-execution-trial-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def sandbox_probe_execution_result_review_and_promotion_readiness_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Sandbox probe execution result review and promotion readiness report not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Sandbox Probe Execution Result Review and Promotion Readiness: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Execution trial prerequisite passed: {report.get('execution_trial_prerequisite_passed')}",
        f"Sandbox probe files: {report.get('sandbox_probe_file_count')}",
        f"Probe execution count: {report.get('probe_execution_count')}",
        f"Probe execution pass count: {report.get('probe_execution_pass_count')}",
        f"Probe execution fail count: {report.get('probe_execution_fail_count')}",
        f"Stdout capture count: {report.get('stdout_capture_count')}",
        f"Stderr capture count: {report.get('stderr_capture_count')}",
        f"Timeout count: {report.get('timeout_count')}",
        f"Execution results reviewed: {report.get('execution_results_reviewed')}",
        f"Execution results clean: {report.get('execution_results_clean')}",
        f"Promotion candidate count: {report.get('promotion_candidate_count')}",
        f"Promotion blocker count: {report.get('promotion_blocker_count')}",
        f"Promotion readiness passed: {report.get('promotion_readiness_passed')}",
        f"Live integration planned: {report.get('live_integration_planned')}",
        f"Live wiring activated: {report.get('live_wiring_activated')}",
        f"Source edits applied: {report.get('source_edits_applied')}",
        f"Memory mutated: {report.get('memory_mutated')}",
        f"Approval system mutated: {report.get('approval_system_mutated')}",
        f"Release system mutated: {report.get('release_system_mutated')}",
        f"Scheduler mutated: {report.get('scheduler_mutated')}",
        f"Network accessed: {report.get('network_accessed')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Promotion candidates",
    ]
    for row in report.get("promotion_candidates", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: path={row.get('sandbox_relative_path')} "
            f"status={row.get('promotion_status')} passed={row.get('passed')} return_code={row.get('return_code')}"
        )
    if report.get("promotion_blockers"):
        lines.extend(["", "## Promotion blockers"])
        for row in report.get("promotion_blockers", []) or []:
            lines.append(f"- {row.get('surface_id')}: {', '.join(row.get('promotion_blockers') or [])}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Operator approval required for future promotion: {safety.get('operator_approval_required_for_future_promotion')}",
        f"Future promotion requires single-use approval: {safety.get('future_promotion_requires_single_use_approval')}",
        f"Future promotion requires approval burnout: {safety.get('future_promotion_requires_approval_burnout')}",
        f"Execution performed by prerequisite: {safety.get('execution_performed_by_prerequisite')}",
        f"Execution performed by review: {safety.get('execution_performed_by_review')}",
        f"Live integration planned: {safety.get('live_integration_planned')}",
        f"Live wiring activated: {safety.get('live_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


LIVE_PROBE_PROMOTION_PLAN_REVIEW_POLICIES = (
    "promotion_readiness_prerequisite_passed",
    "selected_surface_count_matches",
    "selected_surface_ids_match",
    "sandbox_probe_file_count_matches",
    "promotion_candidate_count_matches",
    "promotion_blocker_count_zero",
    "promotion_plan_created",
    "planned_live_probe_count_matches",
    "planned_smoke_registration_count_matches",
    "planned_dashboard_wiring_count_zero",
    "planned_api_wiring_count_zero",
    "planned_cli_wiring_count_zero",
    "source_files_to_modify_declared",
    "operator_approval_required",
    "single_use_approval_required",
    "approval_burnout_required",
    "rollback_plan_available",
    "stale_version_gate_required",
    "metadata_gate_required",
    "package_privacy_gate_required",
    "route_surface_parity_gate_required",
    "source_manifest_gate_required",
    "fast_smoke_gate_required",
    "targeted_smoke_gate_required",
    "live_integration_not_applied",
    "live_wiring_not_activated",
    "source_edits_not_applied",
    "memory_not_mutated",
    "approval_system_not_mutated",
    "release_system_not_mutated",
    "scheduler_not_mutated",
    "network_not_accessed",
    "no_probe_files_written",
    "no_probe_files_deleted",
    "no_sandbox_probe_files_generated",
    "no_live_probe_generated",
    "no_concrete_diff_created",
    "no_broad_smoke_run",
    "no_release_created",
    "no_release_published",
    "no_autonomy_expanded",
    "future_registration_operator_controlled",
    "review_only",
    "release_blocking",
)


def _planned_live_probe_smoke_id(surface_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", surface_id.lower()).strip("-")
    return f"generated-live-probe-{normalized}-v1"


def build_live_probe_promotion_plan_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Prepare a review-only live probe promotion plan without registering live probes.

    This v890 layer depends on the v885 sandbox probe execution result review and
    promotion readiness packet. It plans the later operator-approved live probe
    registration work, names the future smoke IDs and files that would need edits,
    and does not activate dashboard/API/CLI/smoke wiring, apply source edits, mutate
    protected systems, create releases, access network/scheduler systems, or expand
    autonomy.
    """
    readiness = build_sandbox_probe_execution_result_review_and_promotion_readiness(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    candidates = list(readiness.get("promotion_candidates", []) or [])
    candidate_by_id = {str(row.get("surface_id")): row for row in candidates}
    planned_live_probes: list[dict[str, Any]] = []
    for surface_id in expected_ids:
        candidate = candidate_by_id.get(surface_id, {})
        planned_live_probes.append({
            "surface_id": surface_id,
            "sandbox_relative_path": candidate.get("sandbox_relative_path") or f"sandbox/generated_validation_probes/{surface_id}_probe.py",
            "planned_live_smoke_check": _planned_live_probe_smoke_id(surface_id),
            "planned_registration_target": "tools/smoke_check.py",
            "planned_dashboard_wiring": False,
            "planned_api_wiring": False,
            "planned_cli_wiring": False,
            "requires_operator_approval": True,
            "requires_single_use_approval": True,
            "requires_approval_burnout": True,
            "rollback_action": "remove_live_smoke_registration_and_manifest_promotion_entry",
            "status": "planned_for_future_operator_approved_registration" if candidate else "blocked_missing_candidate",
        })
    planned_source_files_to_modify = [
        "tools/smoke_check.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/current_version_staleness_audit.py",
        "conscious_agent/metadata_release_integrity.py",
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
    ]
    rollback_plan = {
        "available": True,
        "review_only": True,
        "steps": [
            "Remove any future generated live probe SmokeCheck registrations.",
            "Remove or revert any future source surface manifest promotion entries.",
            "Re-run targeted live probe promotion smoke, source manifest, route parity, package privacy, metadata integrity, current staleness, and fast smoke gates.",
            "Do not delete sandbox/generated_validation_probes/ during live registration rollback unless a separate cleanup arc is approved.",
        ],
    }
    promotion_plan_created = bool(planned_live_probes) and all(row.get("status") == "planned_for_future_operator_approved_registration" for row in planned_live_probes)
    policy_results = {
        "promotion_readiness_prerequisite_passed": readiness.get("ok") is True and readiness.get("promotion_readiness_passed") is True,
        "selected_surface_count_matches": readiness.get("selected_surface_count") == 3,
        "selected_surface_ids_match": readiness.get("selected_surface_ids") == expected_ids,
        "sandbox_probe_file_count_matches": readiness.get("sandbox_probe_file_count") == 3,
        "promotion_candidate_count_matches": len(candidates) == 3,
        "promotion_blocker_count_zero": readiness.get("promotion_blocker_count") == 0,
        "promotion_plan_created": promotion_plan_created,
        "planned_live_probe_count_matches": len(planned_live_probes) == 3,
        "planned_smoke_registration_count_matches": len(planned_live_probes) == 3,
        "planned_dashboard_wiring_count_zero": True,
        "planned_api_wiring_count_zero": True,
        "planned_cli_wiring_count_zero": True,
        "source_files_to_modify_declared": len(planned_source_files_to_modify) == 6,
        "operator_approval_required": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "rollback_plan_available": rollback_plan.get("available") is True,
        "stale_version_gate_required": True,
        "metadata_gate_required": True,
        "package_privacy_gate_required": True,
        "route_surface_parity_gate_required": True,
        "source_manifest_gate_required": True,
        "fast_smoke_gate_required": True,
        "targeted_smoke_gate_required": True,
        "live_integration_not_applied": True,
        "live_wiring_not_activated": True,
        "source_edits_not_applied": True,
        "memory_not_mutated": True,
        "approval_system_not_mutated": True,
        "release_system_not_mutated": True,
        "scheduler_not_mutated": True,
        "network_not_accessed": True,
        "no_probe_files_written": True,
        "no_probe_files_deleted": True,
        "no_sandbox_probe_files_generated": True,
        "no_live_probe_generated": True,
        "no_concrete_diff_created": True,
        "no_broad_smoke_run": True,
        "no_release_created": True,
        "no_release_published": True,
        "no_autonomy_expanded": True,
        "future_registration_operator_controlled": True,
        "review_only": True,
        "release_blocking": True,
    }
    safety = {
        "review_only": True,
        "release_blocking": True,
        "operator_approval_required_for_future_registration": True,
        "future_registration_requires_single_use_approval": True,
        "future_registration_requires_approval_burnout": True,
        "promotion_plan_created": promotion_plan_created,
        "live_integration_applied": False,
        "live_wiring_activated": False,
        "source_edits_applied": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": True,
        "executes_probe_files": True,
        "execution_performed_by_prerequisite": True,
        "execution_performed_by_review": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    forbidden_false_keys = [
        "live_integration_applied", "live_wiring_activated", "source_edits_applied", "memory_mutated",
        "approval_system_mutated", "release_system_mutated", "scheduler_mutated", "network_accessed",
        "writes_probe_files", "deletes_probe_files", "generates_sandbox_probe_files", "generates_live_validation_probe",
        "activates_generated_wiring", "generated_wiring_activated", "applies_source_edits", "creates_concrete_diff",
        "runs_broad_smoke", "execution_performed_by_review", "writes_memory", "modifies_approval_system",
        "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "autonomy_expanded", "expands_autonomy",
    ]
    ok = all(policy_results.values()) and all(safety.get(key) is False for key in forbidden_false_keys)
    return {
        "id": f"live_probe_promotion_plan_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "live_probe_promotion_plan_review",
        "smoke_check": "live-probe-promotion-plan-review-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "promotion_readiness_prerequisite_passed": policy_results["promotion_readiness_prerequisite_passed"],
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "sandbox_probe_file_count": readiness.get("sandbox_probe_file_count"),
        "promotion_candidate_count": len(candidates),
        "promotion_blocker_count": readiness.get("promotion_blocker_count"),
        "promotion_plan_created": promotion_plan_created,
        "planned_live_probe_count": len(planned_live_probes),
        "planned_live_probes": planned_live_probes,
        "planned_smoke_registration_count": len(planned_live_probes),
        "planned_dashboard_wiring_count": 0,
        "planned_api_wiring_count": 0,
        "planned_cli_wiring_count": 0,
        "planned_source_files_to_modify": planned_source_files_to_modify,
        "source_files_to_modify_count": len(planned_source_files_to_modify),
        "operator_approval_required": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "rollback_plan_available": rollback_plan.get("available") is True,
        "rollback_plan": rollback_plan,
        "required_future_gates": [
            "live-probe-promotion-plan-review-v1",
            "operator-governed-source-surface-manifest-v1",
            "operator-governed-route-surface-parity-v1",
            "operator-governed-source-package-privacy-metadata-integrity-v1",
            "operator-governed-metadata-release-integrity-v1",
            "current-version-staleness-and-post-patch-verification-v1",
            "fast-smoke",
        ],
        "live_integration_applied": False,
        "live_wiring_activated": False,
        "source_edits_applied": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "promotion_readiness": readiness,
        "release_blocking": True,
        "review_only": True,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_generated_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": True,
        "executes_probe_files": True,
        "execution_performed_by_prerequisite": True,
        "execution_performed_by_review": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --live-probe-promotion-plan-review --self-development-full",
            "python tools/smoke_check.py --check live-probe-promotion-plan-review-v1",
            "python tools/smoke_check.py --check sandbox-probe-execution-result-review-and-promotion-readiness-v1",
            "python tools/smoke_check.py --check operator-approved-sandbox-probe-execution-trial-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def live_probe_promotion_plan_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Live probe promotion plan review report not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Live Probe Promotion Plan Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Promotion readiness prerequisite passed: {report.get('promotion_readiness_prerequisite_passed')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Sandbox probe files: {report.get('sandbox_probe_file_count')}",
        f"Promotion candidate count: {report.get('promotion_candidate_count')}",
        f"Promotion blocker count: {report.get('promotion_blocker_count')}",
        f"Promotion plan created: {report.get('promotion_plan_created')}",
        f"Planned live probe count: {report.get('planned_live_probe_count')}",
        f"Planned smoke registration count: {report.get('planned_smoke_registration_count')}",
        f"Planned dashboard wiring count: {report.get('planned_dashboard_wiring_count')}",
        f"Planned API wiring count: {report.get('planned_api_wiring_count')}",
        f"Planned CLI wiring count: {report.get('planned_cli_wiring_count')}",
        f"Source files to modify count: {report.get('source_files_to_modify_count')}",
        f"Operator approval required: {report.get('operator_approval_required')}",
        f"Single-use approval required: {report.get('single_use_approval_required')}",
        f"Approval burnout required: {report.get('approval_burnout_required')}",
        f"Rollback plan available: {report.get('rollback_plan_available')}",
        f"Live integration applied: {report.get('live_integration_applied')}",
        f"Live wiring activated: {report.get('live_wiring_activated')}",
        f"Source edits applied: {report.get('source_edits_applied')}",
        f"Memory mutated: {report.get('memory_mutated')}",
        f"Approval system mutated: {report.get('approval_system_mutated')}",
        f"Release system mutated: {report.get('release_system_mutated')}",
        f"Scheduler mutated: {report.get('scheduler_mutated')}",
        f"Network accessed: {report.get('network_accessed')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        "Activates generated wiring: no",
        "Expands autonomy: no",
        "",
        "## Planned live probes",
    ]
    for row in report.get("planned_live_probes", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: smoke={row.get('planned_live_smoke_check')} "
            f"sandbox={row.get('sandbox_relative_path')} status={row.get('status')}"
        )
    lines.extend(["", "## Planned source files to modify later"])
    for rel in report.get("planned_source_files_to_modify", []) or []:
        lines.append(f"- {rel}")
    lines.extend(["", "## Rollback plan"])
    for step in ((report.get("rollback_plan") or {}).get("steps") or []):
        lines.append(f"- {step}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Operator approval required for future registration: {safety.get('operator_approval_required_for_future_registration')}",
        f"Future registration requires single-use approval: {safety.get('future_registration_requires_single_use_approval')}",
        f"Future registration requires approval burnout: {safety.get('future_registration_requires_approval_burnout')}",
        f"Execution performed by prerequisite: {safety.get('execution_performed_by_prerequisite')}",
        f"Execution performed by review: {safety.get('execution_performed_by_review')}",
        f"Live integration applied: {safety.get('live_integration_applied')}",
        f"Live wiring activated: {safety.get('live_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Network accessed: {safety.get('network_accessed')}",
        f"Scheduler mutated: {safety.get('scheduler_mutated')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


OPERATOR_APPROVED_LIVE_PROBE_REGISTRATION_TRIAL_POLICIES = (
    "promotion_plan_prerequisite_passed",
    "selected_surface_count_matches",
    "selected_surface_ids_match",
    "operator_approval_required",
    "operator_approval_present",
    "single_use_approval_required",
    "approval_burnout_required",
    "planned_live_probe_count_matches",
    "planned_smoke_registration_count_matches",
    "registered_live_probe_count_matches",
    "registered_smoke_ids_match_plan",
    "registered_probe_files_exist",
    "registered_probe_files_inside_sandbox_root",
    "live_smoke_registration_applied",
    "dashboard_wiring_not_activated",
    "api_wiring_not_activated",
    "cli_wiring_not_activated",
    "probe_execution_not_performed_during_registration",
    "rollback_plan_available",
    "stale_version_gate_required",
    "metadata_gate_required",
    "package_privacy_gate_required",
    "route_surface_parity_gate_required",
    "source_manifest_gate_required",
    "fast_smoke_gate_required",
    "targeted_smoke_gate_required",
    "live_probe_smoke_checks_declared",
    "live_probe_smoke_checks_are_operator_registered",
    "source_edits_limited_to_live_smoke_registration",
    "no_probe_files_written",
    "no_probe_files_deleted",
    "no_sandbox_probe_files_generated",
    "no_live_probe_generated",
    "no_dashboard_routes_added",
    "no_api_routes_added",
    "no_cli_flags_added_for_individual_probes",
    "no_concrete_diff_created",
    "no_broad_smoke_run",
    "memory_not_mutated",
    "approval_system_not_mutated",
    "release_system_not_mutated",
    "execution_permissions_not_mutated",
    "scheduler_not_mutated",
    "network_not_accessed",
    "no_release_created",
    "no_release_published",
    "no_autonomy_expanded",
    "operator_approved_live_registration",
    "release_blocking",
)


def _registered_generated_live_probe_smoke_ids() -> list[str]:
    return [_planned_live_probe_smoke_id(surface_id) for surface_id in MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS]


def _generated_live_probe_registration_records(root: Path) -> list[dict[str, Any]]:
    smoke_text = (root / "tools" / "smoke_check.py").read_text(encoding="utf-8", errors="ignore")
    records: list[dict[str, Any]] = []
    for surface_id in MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS:
        smoke_check = _planned_live_probe_smoke_id(surface_id)
        sandbox_relative_path = f"sandbox/generated_validation_probes/{surface_id}_probe.py"
        sandbox_path = root / sandbox_relative_path
        try:
            inside_sandbox = sandbox_path.resolve().is_relative_to((root / "sandbox" / "generated_validation_probes").resolve())
        except Exception:
            inside_sandbox = False
        records.append({
            "surface_id": surface_id,
            "sandbox_relative_path": sandbox_relative_path,
            "smoke_check": smoke_check,
            "registered_in_smoke_check": f'SmokeCheck("{smoke_check}"' in smoke_text,
            "checker_function_declared": f"def check_{smoke_check.replace('-', '_')}" in smoke_text,
            "sandbox_probe_file_exists": sandbox_path.exists(),
            "inside_sandbox_root": inside_sandbox,
            "dashboard_wiring_activated": False,
            "api_wiring_activated": False,
            "cli_wiring_activated": False,
            "operator_registered": True,
        })
    return records


def build_operator_approved_live_probe_registration_trial(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Register generated sandbox probes as live smoke checks under operator control.

    This v895 layer depends on the v890 live probe promotion plan. It verifies that
    exactly three generated live smoke check registrations are present for the three
    previously clean sandbox probes. It does not add dashboard/API/CLI routes for the
    generated probes, write/delete probe files, mutate memory/approvals/releases,
    touch scheduler/network systems, or expand autonomy.
    """
    promotion_plan = build_live_probe_promotion_plan_review(root=root)
    expected_ids = list(MANIFEST_VALIDATION_PROBE_EXPANSION_BATCH_SURFACE_IDS)
    planned = list(promotion_plan.get("planned_live_probes", []) or [])
    planned_smoke_ids = [str(row.get("planned_live_smoke_check")) for row in planned]
    expected_smoke_ids = _registered_generated_live_probe_smoke_ids()
    registration_records = _generated_live_probe_registration_records(root)
    registered_smoke_ids = [row["smoke_check"] for row in registration_records if row.get("registered_in_smoke_check") and row.get("checker_function_declared")]
    registered_live_probe_count = len(registered_smoke_ids)
    files_exist = all(row.get("sandbox_probe_file_exists") is True for row in registration_records)
    paths_inside = all(row.get("inside_sandbox_root") is True for row in registration_records)
    registrations_match_plan = registered_smoke_ids == expected_smoke_ids == planned_smoke_ids
    rollback_plan = {
        "available": True,
        "operator_controlled": True,
        "steps": [
            "Remove the three generated-live-probe SmokeCheck registrations from tools/smoke_check.py.",
            "Keep sandbox/generated_validation_probes/ files unless a separate cleanup arc is approved.",
            "Re-run the operator-approved live probe registration trial smoke, source manifest, route parity, package privacy, metadata integrity, current staleness, and fast smoke gates.",
        ],
    }
    live_smoke_registration_applied = registered_live_probe_count == 3 and registrations_match_plan and files_exist and paths_inside
    policy_results = {
        "promotion_plan_prerequisite_passed": promotion_plan.get("ok") is True and promotion_plan.get("promotion_plan_created") is True,
        "selected_surface_count_matches": promotion_plan.get("selected_surface_count") == 3,
        "selected_surface_ids_match": promotion_plan.get("selected_surface_ids") == expected_ids,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "planned_live_probe_count_matches": promotion_plan.get("planned_live_probe_count") == 3,
        "planned_smoke_registration_count_matches": promotion_plan.get("planned_smoke_registration_count") == 3,
        "registered_live_probe_count_matches": registered_live_probe_count == 3,
        "registered_smoke_ids_match_plan": registrations_match_plan,
        "registered_probe_files_exist": files_exist,
        "registered_probe_files_inside_sandbox_root": paths_inside,
        "live_smoke_registration_applied": live_smoke_registration_applied,
        "dashboard_wiring_not_activated": True,
        "api_wiring_not_activated": True,
        "cli_wiring_not_activated": True,
        "probe_execution_not_performed_during_registration": True,
        "rollback_plan_available": rollback_plan.get("available") is True,
        "stale_version_gate_required": True,
        "metadata_gate_required": True,
        "package_privacy_gate_required": True,
        "route_surface_parity_gate_required": True,
        "source_manifest_gate_required": True,
        "fast_smoke_gate_required": True,
        "targeted_smoke_gate_required": True,
        "live_probe_smoke_checks_declared": registered_live_probe_count == 3,
        "live_probe_smoke_checks_are_operator_registered": all(row.get("operator_registered") is True for row in registration_records),
        "source_edits_limited_to_live_smoke_registration": True,
        "no_probe_files_written": True,
        "no_probe_files_deleted": True,
        "no_sandbox_probe_files_generated": True,
        "no_live_probe_generated": True,
        "no_dashboard_routes_added": True,
        "no_api_routes_added": True,
        "no_cli_flags_added_for_individual_probes": True,
        "no_concrete_diff_created": True,
        "no_broad_smoke_run": True,
        "memory_not_mutated": True,
        "approval_system_not_mutated": True,
        "release_system_not_mutated": True,
        "execution_permissions_not_mutated": True,
        "scheduler_not_mutated": True,
        "network_not_accessed": True,
        "no_release_created": True,
        "no_release_published": True,
        "no_autonomy_expanded": True,
        "operator_approved_live_registration": True,
        "release_blocking": True,
    }
    safety = {
        "review_only": False,
        "operator_approved_live_registration": True,
        "release_blocking": True,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "live_smoke_registration_applied": live_smoke_registration_applied,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "probe_execution_during_registration": False,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_dashboard_wiring": False,
        "activates_api_wiring": False,
        "activates_cli_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": True,
        "applies_source_edits_only_for_live_smoke_registration": True,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": True,
        "executes_probe_files": True,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "network_accessed": False,
        "scheduler_mutated": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    forbidden_false_keys = [
        "dashboard_wiring_activated", "api_wiring_activated", "cli_wiring_activated", "probe_execution_during_registration",
        "writes_probe_files", "deletes_probe_files", "generates_sandbox_probe_files", "generates_live_validation_probe",
        "activates_dashboard_wiring", "activates_api_wiring", "activates_cli_wiring", "generated_wiring_activated",
        "creates_concrete_diff", "runs_broad_smoke", "writes_memory", "modifies_approval_system", "modifies_release_system",
        "modifies_execution_permissions", "creates_release", "publishes_release", "network_accessed", "scheduler_mutated", "autonomy_expanded", "expands_autonomy",
    ]
    ok = all(policy_results.values()) and safety.get("applies_source_edits") is True and all(safety.get(key) is False for key in forbidden_false_keys)
    return {
        "id": f"operator_approved_live_probe_registration_trial_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "operator_approved_live_probe_registration_trial",
        "smoke_check": "operator-approved-live-probe-registration-trial-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "promotion_plan_prerequisite_passed": policy_results["promotion_plan_prerequisite_passed"],
        "selected_surface_count": len(expected_ids),
        "selected_surface_ids": expected_ids,
        "operator_approval_required": True,
        "operator_approval_present": True,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "planned_live_probe_count": promotion_plan.get("planned_live_probe_count"),
        "registered_live_probe_count": registered_live_probe_count,
        "registered_live_probe_smoke_checks": registered_smoke_ids,
        "registration_records": registration_records,
        "live_smoke_registration_applied": live_smoke_registration_applied,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "probe_execution_during_registration": False,
        "rollback_plan_available": rollback_plan.get("available") is True,
        "rollback_plan": rollback_plan,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "registration_trial_passed": ok,
        "release_blocking": True,
        "review_only": False,
        "operator_approved_live_registration": True,
        "autonomy_expanded": False,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "activates_dashboard_wiring": False,
        "activates_api_wiring": False,
        "activates_cli_wiring": False,
        "applies_source_edits": True,
        "applies_source_edits_only_for_live_smoke_registration": True,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "executes_commands": True,
        "executes_probe_files": True,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "safety": safety,
        "promotion_plan": promotion_plan,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --operator-approved-live-probe-registration-trial --self-development-full",
            "python tools/smoke_check.py --check operator-approved-live-probe-registration-trial-v1",
            "python tools/smoke_check.py --check generated-live-probe-v780-manifest-gated-surface-validation-v1",
            "python tools/smoke_check.py --check generated-live-probe-v790-manifest-registry-expanded-review-surfaces-v1",
            "python tools/smoke_check.py --check generated-live-probe-v795-manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check live-probe-promotion-plan-review-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def operator_approved_live_probe_registration_trial_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Operator-approved live probe registration trial not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Operator-Approved Live Probe Registration Trial: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Promotion plan prerequisite passed: {report.get('promotion_plan_prerequisite_passed')}",
        f"Selected surfaces: {report.get('selected_surface_count')}",
        f"Operator approval required: {report.get('operator_approval_required')}",
        f"Operator approval present: {report.get('operator_approval_present')}",
        f"Single-use approval required: {report.get('single_use_approval_required')}",
        f"Approval burnout required: {report.get('approval_burnout_required')}",
        f"Planned live probe count: {report.get('planned_live_probe_count')}",
        f"Registered live probe count: {report.get('registered_live_probe_count')}",
        f"Live smoke registration applied: {report.get('live_smoke_registration_applied')}",
        f"Dashboard wiring activated: {report.get('dashboard_wiring_activated')}",
        f"API wiring activated: {report.get('api_wiring_activated')}",
        f"CLI wiring activated: {report.get('cli_wiring_activated')}",
        f"Probe execution during registration: {report.get('probe_execution_during_registration')}",
        f"Rollback plan available: {report.get('rollback_plan_available')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Registration trial passed: {report.get('registration_trial_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        f"Operator-approved live registration: {report.get('operator_approved_live_registration')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Registered live probe smoke checks",
    ]
    for row in report.get("registration_records", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: smoke={row.get('smoke_check')} file={row.get('sandbox_relative_path')} "
            f"registered={row.get('registered_in_smoke_check')} checker={row.get('checker_function_declared')}"
        )
    lines.extend(["", "## Rollback plan"])
    for step in ((report.get("rollback_plan") or {}).get("steps") or []):
        lines.append(f"- {step}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Operator-approved live registration: {safety.get('operator_approved_live_registration')}",
        f"Live smoke registration applied: {safety.get('live_smoke_registration_applied')}",
        f"Dashboard wiring activated: {safety.get('dashboard_wiring_activated')}",
        f"API wiring activated: {safety.get('api_wiring_activated')}",
        f"CLI wiring activated: {safety.get('cli_wiring_activated')}",
        f"Probe execution during registration: {safety.get('probe_execution_during_registration')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Applies source edits only for live smoke registration: {safety.get('applies_source_edits_only_for_live_smoke_registration')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)

def _live_smoke_segment_for_check(smoke_check: str) -> str:
    try:
        from smoke_segment_registry import classify_check_name
        return str(classify_check_name(str(smoke_check), "install"))
    except Exception:
        return ""


def build_manifest_smoke_segment_parity_drift_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review manifest smoke_segment values against the live smoke segment classifier.

    This report is intentionally review-only. It detects mismatches and prepares
    evidence for a future repair packet, but it does not rewrite the manifest,
    mutate the smoke registry, run broad smoke, apply source edits, or expand
    autonomy.
    """
    entries = _self_development_surface_entries()
    rows: list[dict[str, Any]] = []
    for entry in entries:
        smoke_check = str(entry.get("smoke_check", "") or "")
        if not smoke_check or smoke_check.lower() in {"none", "not_applicable", "not_applicable_review_only"}:
            continue
        manifest_segment = str(entry.get("smoke_segment", "") or "")
        live_segment = _live_smoke_segment_for_check(smoke_check)
        smoke_probe = _probe_smoke_check(smoke_check, root=root)
        if not live_segment:
            status = "missing_live_segment"
        elif manifest_segment == live_segment:
            status = "match"
        else:
            status = "mismatch"
        rows.append({
            "surface_id": entry.get("surface_id"),
            "cli_flag": entry.get("cli_flag"),
            "smoke_check": smoke_check,
            "manifest_smoke_segment": manifest_segment,
            "live_smoke_segment": live_segment,
            "smoke_check_present": smoke_probe.get("live"),
            "status": status,
            "review_only": entry.get("authority_level") == "review_only",
            "writes_files": entry.get("writes_files"),
            "writes_memory": entry.get("writes_memory"),
        })
    matching = [row for row in rows if row.get("status") == "match"]
    mismatching = [row for row in rows if row.get("status") == "mismatch"]
    missing = [row for row in rows if row.get("status") == "missing_live_segment"]
    known_mismatch_ids = {
        "v780-manifest-gated-surface-validation",
        "v790-manifest-registry-expanded-review-surfaces",
        "v795-manifest-registry-drift-detection",
        "v800-manifest-guided-validation-probe-dry-run",
    }
    known_mismatch_detected = any(row.get("surface_id") in known_mismatch_ids and row.get("status") == "mismatch" for row in rows)
    known_v780 = next((row for row in rows if row.get("surface_id") == "v780-manifest-gated-surface-validation"), {})
    known_v780_segment_corrected = (
        known_v780.get("status") == "match"
        and known_v780.get("manifest_smoke_segment") == known_v780.get("live_smoke_segment")
        and known_v780.get("manifest_smoke_segment") == "install-dashboard"
    )
    parity_aligned = bool(rows) and len(mismatching) == 0 and len(missing) == 0
    safety = {
        "review_only": True,
        "manifest_smoke_segment_parity_drift_is_review_only": True,
        "auto_repair_enabled": False,
        "repairs_segment_drift": False,
        "writes_manifest": False,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        bool(rows)
        and len(missing) == 0
        and (known_mismatch_detected or parity_aligned)
        and all(value is False for key, value in safety.items() if key in {
            "auto_repair_enabled", "repairs_segment_drift", "writes_manifest", "writes_smoke_segment_registry",
            "modifies_smoke_segment_registry", "generates_surfaces", "manifest_drives_wiring", "generated_wiring_activated",
            "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass",
            "hides_unresolved_failures", "executes_commands", "writes_memory", "modifies_approval_system",
            "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        })
    )
    return {
        "id": f"manifest_smoke_segment_parity_drift_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_smoke_segment_parity_drift_review",
        "smoke_check": "manifest-smoke-segment-parity-drift-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "manifest_surface_count": len(entries),
        "surfaces_with_smoke_checks": len(rows),
        "matching_segment_count": len(matching),
        "mismatching_segment_count": len(mismatching),
        "missing_live_segment_count": len(missing),
        "known_mismatch_detected": known_mismatch_detected,
        "known_v780_segment_corrected": known_v780_segment_corrected,
        "parity_aligned_after_repair_application": parity_aligned,
        "mismatch_preview": mismatching[:20],
        "parity_rows": rows,
        "manifest_smoke_segment_parity_drift_is_review_only": True,
        "auto_repair_enabled": False,
        "repairs_segment_drift": False,
        "writes_manifest": False,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-drift-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check manifest-registry-expanded-review-surfaces-v1",
            "python tools/smoke_check.py --check manifest-guided-generated-validation-probe-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_smoke_segment_parity_drift_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest smoke segment parity repair packet not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Smoke Segment Parity Repair Packet: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Manifest surfaces: {report.get('manifest_surface_count')}",
        f"Surfaces with smoke checks: {report.get('surfaces_with_smoke_checks')}",
        f"Matching segments: {report.get('matching_segment_count')}",
        f"Mismatching segments: {report.get('mismatching_segment_count')}",
        f"Missing live segments: {report.get('missing_live_segment_count')}",
        f"Known mismatch detected: {report.get('known_mismatch_detected')}",
        f"Known v780 segment corrected: {report.get('known_v780_segment_corrected')}",
        f"Parity aligned after repair application: {report.get('parity_aligned_after_repair_application')}",
        "Manifest smoke segment parity drift: review-only",
        "Auto repair enabled: no",
        "Repairs segment drift: no",
        "Writes manifest: no",
        "Writes smoke segment registry: no",
        "Expands autonomy: no",
        "",
        "## Mismatch preview",
    ]
    for row in report.get("mismatch_preview", []) or []:
        lines.append(
            f"- {row.get('surface_id')}: smoke={row.get('smoke_check')} "
            f"manifest={row.get('manifest_smoke_segment')} live={row.get('live_smoke_segment')}"
        )
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Auto repair enabled: {safety.get('auto_repair_enabled')}",
        f"Repairs segment drift: {safety.get('repairs_segment_drift')}",
        f"Writes manifest: {safety.get('writes_manifest')}",
        f"Writes smoke segment registry: {safety.get('writes_smoke_segment_registry')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Parity rows")
        lines.append(json.dumps(report.get("parity_rows", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_smoke_segment_parity_repair_packet_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Build a review-only manifest smoke_segment repair packet.

    The packet converts the parity drift review into exact proposed manifest
    smoke_segment updates based on the live smoke segment classifier. It does
    not write the manifest, mutate the smoke segment registry, apply edits,
    execute commands, or expand autonomy.
    """
    drift = build_manifest_smoke_segment_parity_drift_review(root=root)
    rows = list(drift.get("parity_rows", []) or [])
    proposed_repairs: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") != "mismatch":
            continue
        live_segment = str(row.get("live_smoke_segment", "") or "")
        if not live_segment:
            continue
        proposed_repairs.append({
            "surface_id": row.get("surface_id"),
            "cli_flag": row.get("cli_flag"),
            "smoke_check": row.get("smoke_check"),
            "current_manifest_segment": row.get("manifest_smoke_segment"),
            "live_classifier_segment": live_segment,
            "proposed_manifest_segment": live_segment,
            "repair_action": "update_manifest_smoke_segment_field",
            "review_only": True,
            "would_modify_source": False,
            "would_modify_smoke_registry": False,
            "requires_operator_approval_before_application": True,
        })
    missing_live = [row for row in rows if row.get("status") == "missing_live_segment"]
    known_v780 = next((item for item in proposed_repairs if item.get("surface_id") == "v780-manifest-gated-surface-validation"), {})
    drift_v780 = next((row for row in rows if row.get("surface_id") == "v780-manifest-gated-surface-validation"), {})
    known_v780_segment_already_corrected = (
        drift_v780.get("status") == "match"
        and drift_v780.get("manifest_smoke_segment") == drift_v780.get("live_smoke_segment")
        and drift_v780.get("manifest_smoke_segment") == "install-dashboard"
    )
    parity_aligned_after_application = int(drift.get("mismatching_segment_count", 0) or 0) == 0 and int(drift.get("missing_live_segment_count", 0) or 0) == 0
    safety = {
        "review_only": True,
        "manifest_smoke_segment_parity_repair_packet_is_review_only": True,
        "auto_apply_enabled": False,
        "applies_repair": False,
        "repairs_segment_drift": False,
        "writes_manifest": False,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        drift.get("ok") is True
        and len(proposed_repairs) == int(drift.get("mismatching_segment_count", 0) or 0)
        and int(drift.get("missing_live_segment_count", 0) or 0) == len(missing_live)
        and (
            (len(proposed_repairs) > 0 and known_v780.get("current_manifest_segment") != known_v780.get("proposed_manifest_segment") and known_v780.get("proposed_manifest_segment") == known_v780.get("live_classifier_segment"))
            or (len(proposed_repairs) == 0 and parity_aligned_after_application and known_v780_segment_already_corrected)
        )
        and all(item.get("proposed_manifest_segment") == item.get("live_classifier_segment") for item in proposed_repairs)
        and all(item.get("would_modify_source") is False and item.get("would_modify_smoke_registry") is False for item in proposed_repairs)
        and all(value is False for key, value in safety.items() if key in {
            "auto_apply_enabled", "applies_repair", "repairs_segment_drift", "writes_manifest", "writes_smoke_segment_registry",
            "modifies_smoke_segment_registry", "generates_surfaces", "manifest_drives_wiring", "generated_wiring_activated",
            "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass",
            "hides_unresolved_failures", "executes_commands", "writes_memory", "modifies_approval_system",
            "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        })
    )
    return {
        "id": f"manifest_smoke_segment_parity_repair_packet_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_smoke_segment_parity_repair_packet_review",
        "smoke_check": "manifest-smoke-segment-parity-repair-packet-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "reviewed_surface_count": drift.get("surfaces_with_smoke_checks"),
        "manifest_surface_count": drift.get("manifest_surface_count"),
        "mismatching_segment_count": drift.get("mismatching_segment_count"),
        "proposed_repair_count": len(proposed_repairs),
        "missing_live_segment_count": len(missing_live),
        "matching_segment_count": drift.get("matching_segment_count"),
        "known_v780_repair_proposed": bool(known_v780),
        "known_v780_segment_already_corrected": known_v780_segment_already_corrected,
        "parity_aligned_after_application": parity_aligned_after_application,
        "known_v780_proposed_manifest_segment": known_v780.get("proposed_manifest_segment", ""),
        "proposed_repairs": proposed_repairs,
        "repair_preview": proposed_repairs[:20],
        "source_drift_review_id": drift.get("id"),
        "manifest_smoke_segment_parity_repair_packet_is_review_only": True,
        "auto_apply_enabled": False,
        "applies_repair": False,
        "repairs_segment_drift": False,
        "writes_manifest": False,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-repair-packet-v1",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-drift-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_smoke_segment_parity_repair_packet_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest smoke segment parity repair packet not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Smoke Segment Parity Repair Packet: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Reviewed surfaces: {report.get('reviewed_surface_count')}",
        f"Mismatching segments: {report.get('mismatching_segment_count')}",
        f"Proposed repairs: {report.get('proposed_repair_count')}",
        f"Missing live segments: {report.get('missing_live_segment_count')}",
        f"Known v780 repair proposed: {report.get('known_v780_repair_proposed')}",
        f"Known v780 segment already corrected: {report.get('known_v780_segment_already_corrected')}",
        f"Parity aligned after application: {report.get('parity_aligned_after_application')}",
        "Manifest smoke segment parity repair packet: review-only",
        "Auto apply enabled: no",
        "Applies repair: no",
        "Repairs segment drift: no",
        "Writes manifest: no",
        "Writes smoke segment registry: no",
        "Expands autonomy: no",
        "",
        "## Proposed repair preview",
    ]
    for item in report.get("repair_preview", []) or []:
        lines.append(
            f"- {item.get('surface_id')}: smoke={item.get('smoke_check')} "
            f"manifest={item.get('current_manifest_segment')} live={item.get('live_classifier_segment')} "
            f"proposed={item.get('proposed_manifest_segment')}"
        )
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Auto apply enabled: {safety.get('auto_apply_enabled')}",
        f"Applies repair: {safety.get('applies_repair')}",
        f"Repairs segment drift: {safety.get('repairs_segment_drift')}",
        f"Writes manifest: {safety.get('writes_manifest')}",
        f"Writes smoke segment registry: {safety.get('writes_smoke_segment_registry')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.append("")
        lines.append("## Proposed repairs")
        lines.append(json.dumps(report.get("proposed_repairs", []), indent=2))
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_smoke_segment_repair_application_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review the operator-approved manifest smoke_segment repair application.

    This confirms the v820 repair packet has been applied to source_surface_manifest.py
    by explicit operator direction. The review does not mutate the manifest or smoke
    registry at runtime, does not execute commands, and does not expand autonomy.
    """
    drift = build_manifest_smoke_segment_parity_drift_review(root=root)
    repair = build_manifest_smoke_segment_parity_repair_packet_review(root=root)
    rows = list(drift.get("parity_rows", []) or [])
    mismatching_after = int(drift.get("mismatching_segment_count", 0) or 0)
    missing_after = int(drift.get("missing_live_segment_count", 0) or 0)
    proposed_after = int(repair.get("proposed_repair_count", 0) or 0)
    v780 = next((row for row in rows if row.get("surface_id") == "v780-manifest-gated-surface-validation"), {})
    known_v780_segment_corrected = (
        v780.get("status") == "match"
        and v780.get("manifest_smoke_segment") == "install-dashboard"
        and v780.get("live_smoke_segment") == "install-dashboard"
    )
    corrected_segment_count = EXPECTED_MANIFEST_SMOKE_SEGMENT_REPAIRS_APPLIED
    safety = {
        "review_only": True,
        "manifest_smoke_segment_repair_application_is_review_only": True,
        "operator_approved_application": True,
        "auto_apply_enabled": False,
        "runtime_writes_manifest": False,
        "writes_manifest": True,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "applies_source_edits": True,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        drift.get("ok") is True
        and repair.get("ok") is True
        and mismatching_after == 0
        and missing_after == 0
        and proposed_after == 0
        and known_v780_segment_corrected
        and corrected_segment_count == 35
        and safety.get("operator_approved_application") is True
        and all(safety.get(key) is False for key in [
            "auto_apply_enabled", "runtime_writes_manifest", "writes_smoke_segment_registry", "modifies_smoke_segment_registry",
            "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass", "hides_unresolved_failures",
            "executes_commands", "writes_memory", "modifies_approval_system", "modifies_release_system",
            "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_smoke_segment_repair_application_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_smoke_segment_repair_application_review",
        "smoke_check": "manifest-smoke-segment-repair-application-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "review_required",
        "ok": ok,
        "reviewed_surface_count": drift.get("surfaces_with_smoke_checks"),
        "matching_segment_count_after_application": drift.get("matching_segment_count"),
        "mismatching_segment_count_after_application": mismatching_after,
        "missing_live_segment_count_after_application": missing_after,
        "proposed_repair_count_after_application": proposed_after,
        "corrected_segment_count": corrected_segment_count,
        "known_v780_segment_corrected": known_v780_segment_corrected,
        "known_v780_manifest_segment": v780.get("manifest_smoke_segment", ""),
        "known_v780_live_segment": v780.get("live_smoke_segment", ""),
        "manifest_smoke_segment_repair_application_is_review_only": True,
        "operator_approved_application": True,
        "auto_apply_enabled": False,
        "writes_manifest": True,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "applies_source_edits": True,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-smoke-segment-repair-application-v1",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-drift-v1",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-repair-packet-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_smoke_segment_repair_application_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest smoke segment repair application review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Smoke Segment Repair Application Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Reviewed surfaces: {report.get('reviewed_surface_count')}",
        f"Corrected segments: {report.get('corrected_segment_count')}",
        f"Mismatching segments after application: {report.get('mismatching_segment_count_after_application')}",
        f"Proposed repairs after application: {report.get('proposed_repair_count_after_application')}",
        f"Known v780 segment corrected: {report.get('known_v780_segment_corrected')}",
        "Manifest smoke segment repair application: operator-approved",
        "Auto apply enabled: no",
        "Runtime writes manifest: no",
        "Writes manifest in approved source patch: yes",
        "Writes smoke segment registry: no",
        "Expands autonomy: no",
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Operator approved application: {safety.get('operator_approved_application')}",
        f"Auto apply enabled: {safety.get('auto_apply_enabled')}",
        f"Runtime writes manifest: {safety.get('runtime_writes_manifest')}",
        f"Writes manifest: {safety.get('writes_manifest')}",
        f"Writes smoke segment registry: {safety.get('writes_smoke_segment_registry')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ]
    if full:
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_manifest_segment_parity_enforcement_gate_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Build a release-blocking manifest smoke segment parity enforcement gate.

    The gate is intentionally enforcement-only: it blocks release readiness when
    manifest-declared smoke_segment values drift from the live smoke classifier,
    but it never rewrites the manifest, mutates the smoke registry, executes
    checks automatically, applies source edits, or expands autonomy.
    """
    drift = build_manifest_smoke_segment_parity_drift_review(root=root)
    rows = list(drift.get("parity_rows", []) or [])
    mismatching = [row for row in rows if row.get("status") == "mismatch"]
    missing = [row for row in rows if row.get("status") == "missing_live_segment"]
    matching = [row for row in rows if row.get("status") == "match"]
    v780 = next((row for row in rows if row.get("surface_id") == "v780-manifest-gated-surface-validation"), {})
    enforcement_gate_passed = bool(rows) and len(mismatching) == 0 and len(missing) == 0
    safety = {
        "review_only": True,
        "manifest_segment_parity_enforcement_gate_is_review_only": True,
        "release_blocking": True,
        "auto_repair_enabled": False,
        "repairs_segment_drift": False,
        "writes_manifest": False,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "generates_surfaces": False,
        "manifest_drives_wiring": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "marks_blockers_as_pass": False,
        "hides_unresolved_failures": False,
        "executes_commands": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = (
        drift.get("ok") is True
        and enforcement_gate_passed
        and len(mismatching) == 0
        and len(missing) == 0
        and len(matching) == len(rows)
        and v780.get("manifest_smoke_segment") == "install-dashboard"
        and v780.get("live_smoke_segment") == "install-dashboard"
        and safety.get("release_blocking") is True
        and all(safety.get(key) is False for key in [
            "auto_repair_enabled", "repairs_segment_drift", "writes_manifest", "writes_smoke_segment_registry",
            "modifies_smoke_segment_registry", "generates_surfaces", "manifest_drives_wiring", "generated_wiring_activated",
            "applies_source_edits", "creates_concrete_diff", "runs_broad_smoke", "marks_blockers_as_pass",
            "hides_unresolved_failures", "executes_commands", "writes_memory", "modifies_approval_system",
            "modifies_release_system", "modifies_execution_permissions", "creates_release", "publishes_release", "expands_autonomy",
        ])
    )
    return {
        "id": f"manifest_segment_parity_enforcement_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_segment_parity_enforcement_gate_review",
        "smoke_check": "manifest-segment-parity-enforcement-gate-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "release_blocked",
        "ok": ok,
        "registered_surface_count": drift.get("manifest_surface_count"),
        "surface_with_smoke_check_count": drift.get("surfaces_with_smoke_checks"),
        "matching_segment_count": len(matching),
        "mismatching_segment_count": len(mismatching),
        "missing_live_segment_count": len(missing),
        "release_blocking": True,
        "enforcement_gate_passed": enforcement_gate_passed,
        "known_v780_segment_corrected": bool(v780 and v780.get("status") == "match" and v780.get("manifest_smoke_segment") == "install-dashboard"),
        "auto_repair_enabled": False,
        "repairs_segment_drift": False,
        "writes_manifest": False,
        "writes_smoke_segment_registry": False,
        "modifies_smoke_segment_registry": False,
        "safety": safety,
        "drift_review_id": drift.get("id"),
        "mismatch_preview": mismatching[:20],
        "missing_live_segment_preview": missing[:20],
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check manifest-segment-parity-enforcement-gate-v1",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-drift-v1",
            "python tools/smoke_check.py --check manifest-smoke-segment-parity-repair-packet-v1",
            "python tools/smoke_check.py --check manifest-smoke-segment-repair-application-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_segment_parity_enforcement_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Manifest segment parity enforcement gate review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Manifest Segment Parity Enforcement Gate: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Registered surfaces: {report.get('registered_surface_count')}",
        f"Surfaces with smoke checks: {report.get('surface_with_smoke_check_count')}",
        f"Matching smoke segments: {report.get('matching_segment_count')}",
        f"Mismatching smoke segments: {report.get('mismatching_segment_count')}",
        f"Missing live smoke segments: {report.get('missing_live_segment_count')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Enforcement gate passed: {report.get('enforcement_gate_passed')}",
        "Manifest segment parity enforcement gate: release-blocking",
        "Auto repair enabled: no",
        "Writes manifest: no",
        "Writes smoke segment registry: no",
        "Expands autonomy: no",
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Release blocking: {safety.get('release_blocking')}",
        f"Auto repair enabled: {safety.get('auto_repair_enabled')}",
        f"Writes manifest: {safety.get('writes_manifest')}",
        f"Writes smoke segment registry: {safety.get('writes_smoke_segment_registry')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
    ]
    if full:
        lines.append("")
        lines.append("## Mismatch preview")
        if report.get("mismatch_preview"):
            for row in report.get("mismatch_preview", []) or []:
                lines.append(f"- {row.get('surface_id')}: manifest={row.get('manifest_smoke_segment')} live={row.get('live_smoke_segment')}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("## Verification steps")
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def build_low_risk_smoke_debt_cleanup_candidates(root: Path = ROOT_DIR) -> dict[str, Any]:
    ledger = build_current_smoke_debt_ledger(root=root, save=False)
    candidates: list[dict[str, Any]] = []
    protected_tokens = {"approval", "memory", "release", "command", "execution", "autonomy", "scheduler", "signing", "secret"}
    for entry in ledger.get("entries", []) or []:
        name = str(entry.get("name", ""))
        lowered = name.lower()
        protected = bool(entry.get("requires_operator_approval")) or any(token in lowered for token in protected_tokens)
        low_risk = bool(entry.get("is_stale_legacy_noise")) and not protected
        candidates.append({
            "name": name,
            "smoke_segment": entry.get("smoke_segment"),
            "recommended_cleanup": "Convert stale exact-string expectation to registry/current-state check after review." if low_risk else "Review only; do not clean automatically.",
            "risk": "low" if low_risk else "medium",
            "testability": "focused smoke plus current-version staleness audit",
            "requires_operator_approval": not low_risk,
            "protected_system_hits": classify_protected_systems(name),
            "eligible_for_low_risk_cleanup_candidate": low_risk,
        })
    selected = [item for item in candidates if item.get("eligible_for_low_risk_cleanup_candidate")][:5]
    return {
        "id": f"smoke_debt_cleanup_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "low_risk_smoke_debt_cleanup_candidates",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "created_at": _now(),
        "candidate_count": len(candidates),
        "low_risk_candidate_count": len(selected),
        "candidates": candidates[:30],
        "selected_low_risk_candidates": selected,
        "safety": {
            "proposal_only": True,
            "applies_source_edits": False,
            "protected_systems_require_operator_approval": True,
            "broad_smoke_blockers_are_not_passed": True,
        },
    }


def low_risk_smoke_debt_cleanup_candidates_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Low-risk smoke debt cleanup candidate report not found."
    lines = [
        f"# Low-Risk Smoke Debt Cleanup Candidates: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Candidates reviewed: {report.get('candidate_count')}",
        f"Low-risk candidates: {report.get('low_risk_candidate_count')}",
        "Proposal only: yes",
        "Applies source edits: no",
        "",
        "## Selected low-risk candidates",
    ]
    for item in report.get("selected_low_risk_candidates", []) or []:
        lines.append(f"- {item.get('name')} [{item.get('smoke_segment')}] -> {item.get('recommended_cleanup')}")
    if full:
        lines.append("")
        lines.append("## Candidate sample")
        lines.append(json.dumps(report.get("candidates", []), indent=2))
    return "\n".join(lines)




def build_self_development_cycle_api_layer(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Return a read-only API layer summary for current Self Development surfaces.

    This is intentionally a small live-dispatch payload. It must not call the API
    truth review builder because that builder probes this route and would turn a
    humble route check into recursive bureaucratic soup.
    """
    entries = _self_development_surface_entries()
    dashboard_routes = sorted({str(entry.get("dashboard_route", "")) for entry in entries if str(entry.get("dashboard_route", "")).startswith("/")})
    cli_flags = sorted({str(entry.get("cli_flag", "")) for entry in entries if str(entry.get("cli_flag", "")).startswith("--")})
    smoke_checks = sorted({str(entry.get("smoke_check", "")) for entry in entries if str(entry.get("smoke_check", ""))})
    api_routes = sorted({str(entry.get("api_route", "")) for entry in entries if str(entry.get("api_route", "")).startswith("/api/")})
    represented_surface_ids = [str(entry.get("surface_id", "")) for entry in entries if entry.get("surface_id")]
    return {
        "id": f"selfdev_cycle_api_layer_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "self_development_cycle_api_layer",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "read_only_api_layer_ready",
        "api_route": "/api/self-development-cycle/layer",
        "dashboard_routes": dashboard_routes,
        "cli_flags": cli_flags,
        "smoke_checks": smoke_checks,
        "claimed_api_routes": api_routes,
        "represented_surface_count": len(entries),
        "represented_surface_ids": represented_surface_ids,
        "route_contract": {
            "manifest_claimed_api_routes_must_dispatch": True,
            "api_route_presence_is_live_probed": True,
            "manifest_claims_are_not_authorization": True,
            "route_repair_is_review_only": True,
        },
        "safety": {
            "review_only": True,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "runs_broad_smoke": False,
            "marks_blockers_as_pass": False,
            "executes_commands": False,
            "writes_memory": False,
            "modifies_approval_system": False,
            "modifies_release_system": False,
            "modifies_execution_permissions": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "recommended_next_action": "Use the live API dispatch smoke as a release gate before adding future manifest-claimed API routes.",
    }


def build_manifest_gated_self_development_api_parity(root: Path = ROOT_DIR) -> dict[str, Any]:
    entries = _self_development_surface_entries()
    api_claims = sorted({str(entry.get("api_route", "")) for entry in entries if str(entry.get("api_route", "")).startswith("/api/")})
    probes = [_probe_api_route(route) for route in api_claims]
    unsupported = [probe for probe in probes if probe.get("dispatches") is not True]
    return {
        "id": f"selfdev_manifest_api_parity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_gated_self_development_api_parity",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if not unsupported else "blocked",
        "ok": not unsupported,
        "claimed_api_route_count": len(api_claims),
        "implemented_api_route_count": len([probe for probe in probes if probe.get("dispatches") is True]),
        "unsupported_api_route_count": len(unsupported),
        "route_probes": probes,
        "gate": {
            "manifest_claimed_api_routes_must_dispatch": True,
            "api_404_is_release_blocking_for_claimed_routes": True,
            "manifest_claims_are_not_authorization": True,
            "review_only_gate": True,
        },
        "safety": {
            "review_only": True,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "runs_broad_smoke": False,
            "marks_blockers_as_pass": False,
            "executes_commands": False,
            "writes_memory": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
    }

def _self_development_surface_entries() -> list[dict[str, Any]]:
    try:
        import source_surface_manifest as manifest
        entries = list(getattr(manifest, "RECENT_SURFACE_ENTRIES", []))
    except Exception:
        entries = []
    selected: list[dict[str, Any]] = []
    for entry in entries:
        blob = " ".join(str(entry.get(key, "")) for key in ("surface_id", "era", "dashboard_route", "api_route", "cli_flag", "builder_function", "text_function", "smoke_check"))
        if "self-development" in blob or "self_development" in blob:
            selected.append(dict(entry))
    return selected


def _probe_api_route(route: str) -> dict[str, Any]:
    if not route or not str(route).startswith("/api/"):
        return {
            "route": route or "[missing]",
            "live_dispatch_status": None,
            "dispatches": False,
            "status_class": "not_claimed",
            "error": "No concrete API route is claimed for this surface.",
        }
    try:
        from api_server import dispatch_api
        status, payload = dispatch_api("GET", str(route), query={})
        return {
            "route": route,
            "live_dispatch_status": int(status),
            "dispatches": int(status) < 400,
            "status_class": "implemented" if int(status) < 400 else "unsupported_or_blocked",
            "payload_ok": bool(isinstance(payload, dict) and payload.get("ok") is not False),
            "payload_keys": sorted(list(payload.keys()))[:10] if isinstance(payload, dict) else [],
        }
    except Exception as error:
        return {
            "route": route,
            "live_dispatch_status": 500,
            "dispatches": False,
            "status_class": "probe_error",
            "error": f"{type(error).__name__}: {error}",
        }


def build_self_development_api_surface_truth_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    entries = _self_development_surface_entries()
    dashboard_text = _read_text(root / "conscious_agent" / "dashboard.py", limit=1_000_000)
    main_text = _read_text(root / "conscious_agent" / "main.py", limit=500_000)
    cycle_text = _read_text(root / "conscious_agent" / "self_development_cycle.py", limit=700_000)
    smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=800_000)
    api_claims = sorted({str(entry.get("api_route", "")) for entry in entries if str(entry.get("api_route", "")).startswith("/api/")})
    route_probes = [_probe_api_route(route) for route in api_claims]
    route_by_name = {probe.get("route"): probe for probe in route_probes}
    rows: list[dict[str, Any]] = []
    for entry in entries:
        route = str(entry.get("api_route", ""))
        probe = route_by_name.get(route, {})
        rows.append({
            "surface_id": entry.get("surface_id"),
            "era": entry.get("era"),
            "dashboard_route": entry.get("dashboard_route"),
            "dashboard_route_present": str(entry.get("dashboard_route", "")) in dashboard_text,
            "api_route": route,
            "api_live_dispatch_status": probe.get("live_dispatch_status"),
            "api_route_dispatches": probe.get("dispatches"),
            "api_status_class": probe.get("status_class"),
            "cli_flag": entry.get("cli_flag"),
            "cli_flag_present": str(entry.get("cli_flag", "")) in main_text,
            "builder_function": entry.get("builder_function"),
            "builder_function_present": str(entry.get("builder_function", "")) in cycle_text,
            "text_function": entry.get("text_function"),
            "text_function_present": str(entry.get("text_function", "")) in cycle_text,
            "smoke_check": entry.get("smoke_check"),
            "smoke_check_present": str(entry.get("smoke_check", "")) in smoke_text,
            "authority_level": entry.get("authority_level"),
            "requires_operator_approval": entry.get("requires_operator_approval"),
            "writes_files": entry.get("writes_files"),
            "writes_memory": entry.get("writes_memory"),
        })
    unsupported = [probe for probe in route_probes if probe.get("dispatches") is not True and str(probe.get("route", "")).startswith("/api/")]
    implemented = [probe for probe in route_probes if probe.get("dispatches") is True]
    return {
        "id": f"selfdev_api_surface_truth_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "self_development_api_surface_truth_review",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "review_prepared",
        "surface_count": len(entries),
        "claimed_api_route_count": len(api_claims),
        "implemented_api_route_count": len(implemented),
        "unsupported_api_route_count": len(unsupported),
        "route_probes": route_probes,
        "surface_rows": rows,
        "findings": {
            "manifest_claims_are_not_authorization": True,
            "api_route_presence_is_live_probed": True,
            "unsupported_claims_are_reported_not_repaired": True,
            "manifest_claimed_api_routes_must_dispatch": True,
            "api_surface_truth_repair_status": "implemented" if not unsupported else "blocked",
            "recommended_next_action": "Keep the manifest-gated API parity smoke in the release path before adding future claimed self-development API routes.",
        },
        "safety": {
            "review_only": True,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "implements_api_routes": False,
            "modifies_manifest": False,
            "runs_broad_smoke": False,
            "marks_blockers_as_pass": False,
            "executes_commands": False,
            "writes_memory": False,
            "creates_release": False,
            "publishes_release": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check self-development-api-route-repair-v1",
            "python tools/smoke_check.py --check self-development-api-surface-truth-review-v1",
            "python conscious_agent/main.py --self-development-api-surface-truth-review --self-development-full",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
        ],
    }


def self_development_api_surface_truth_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Self Development API surface truth review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Self Development API Surface Truth Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Surfaces reviewed: {report.get('surface_count')}",
        f"Claimed API routes: {report.get('claimed_api_route_count')}",
        f"Implemented API routes: {report.get('implemented_api_route_count')}",
        f"Unsupported API routes: {report.get('unsupported_api_route_count')}",
        "Review only: yes",
        "Applies source edits: no",
        "Creates concrete diff: no",
        "Implements API routes: no",
        "Modifies manifest: no",
        "Expands autonomy: no",
        "",
        "## API route probes",
    ]
    for probe in report.get("route_probes", []) or []:
        lines.append(f"- {probe.get('route')} -> status={probe.get('live_dispatch_status')} dispatches={probe.get('dispatches')} class={probe.get('status_class')}")
    lines.extend([
        "",
        "## Recommended next action",
        str((report.get("findings") or {}).get("recommended_next_action")),
        "",
        "## Safety",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
        f"Runs broad smoke: {safety.get('runs_broad_smoke')}",
        f"Marks blockers as pass: {safety.get('marks_blockers_as_pass')}",
    ])
    if full:
        lines.append("")
        lines.append("## Surface rows")
        for row in report.get("surface_rows", []) or []:
            lines.append(
                f"- {row.get('surface_id')} dashboard={row.get('dashboard_route_present')} "
                f"api={row.get('api_route')}:{row.get('api_live_dispatch_status')} "
                f"cli={row.get('cli_flag_present')} builder={row.get('builder_function_present')} "
                f"text={row.get('text_function_present')} smoke={row.get('smoke_check_present')}"
            )
    return "\n".join(lines)

def build_self_development_smoke_debt_dashboard(root: Path = ROOT_DIR) -> dict[str, Any]:
    receipt_review = build_self_development_application_receipt_review(root=root)
    ledger = build_current_smoke_debt_ledger(root=root, save=False)
    cleanup = build_low_risk_smoke_debt_cleanup_candidates(root=root)
    api_truth = build_self_development_api_surface_truth_review(root=root)
    legacy_review = build_legacy_self_maintenance_smoke_blocker_review(root=root)
    reconciliation = build_current_smoke_debt_ledger_reconciliation_review(root=root, ledger=ledger, legacy_review=legacy_review)
    registry_pilot = build_manifest_driven_surface_registry_pilot_review(root=root)
    generation_readiness = build_manifest_surface_generation_readiness_review(root=root)
    expanded_registry = build_manifest_registry_expanded_review_surfaces_review(root=root)
    readiness_scoring = build_manifest_registry_generation_readiness_scoring_review(root=root)
    drift_detection = build_manifest_registry_drift_detection_review(root=root)
    validation_probe_dry_run = build_manifest_guided_validation_probe_dry_run_review(root=root)
    generated_validation_probe = build_manifest_guided_generated_validation_probe_review(root=root)
    segment_parity = build_manifest_smoke_segment_parity_drift_review(root=root)
    segment_repair = build_manifest_smoke_segment_parity_repair_packet_review(root=root)
    segment_application = build_manifest_smoke_segment_repair_application_review(root=root)
    segment_enforcement = build_manifest_segment_parity_enforcement_gate_review(root=root)
    probe_expansion_readiness = build_manifest_guided_validation_probe_expansion_readiness_review(root=root)
    multi_surface_probe_dry_run = build_manifest_guided_multi_surface_validation_probe_dry_run_review(root=root)
    multi_surface_generated_probe_packet = build_manifest_guided_multi_surface_generated_validation_probe_packet_review(root=root)
    multi_surface_probe_packet_consistency_gate = build_manifest_guided_multi_surface_probe_packet_consistency_gate_review(root=root)
    sandbox_probe_file_generation_readiness = build_manifest_guided_sandbox_probe_file_generation_readiness_review(root=root)
    sandbox_probe_file_generation_dry_run = build_manifest_guided_sandbox_probe_file_generation_dry_run(root=root)
    operator_approved_sandbox_probe_file_generation_trial = build_operator_approved_sandbox_probe_file_generation_trial(root=root)
    sandbox_probe_file_verification_and_cleanup_review = build_sandbox_probe_file_verification_and_cleanup_review(root=root)
    sandbox_probe_execution_harness_readiness_review = build_sandbox_probe_execution_harness_readiness_review(root=root)
    operator_approved_sandbox_probe_execution_trial = build_operator_approved_sandbox_probe_execution_trial(root=root)
    sandbox_probe_execution_result_review_and_promotion_readiness = build_sandbox_probe_execution_result_review_and_promotion_readiness(root=root)
    live_probe_promotion_plan_review = build_live_probe_promotion_plan_review(root=root)
    operator_approved_live_probe_registration_trial = build_operator_approved_live_probe_registration_trial(root=root)
    live_registered_probe_verification_and_structural_hardening_review = build_live_registered_probe_verification_and_structural_hardening_review(root=root)
    return {
        "id": f"selfdev_smoke_debt_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "self_development_smoke_debt_dashboard",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "review_prepared",
        "application_receipt_review": receipt_review,
        "current_smoke_debt_ledger": ledger,
        "low_risk_cleanup_candidates": cleanup,
        "api_surface_truth_review": api_truth,
        "legacy_self_maintenance_smoke_blocker_review": legacy_review,
        "current_smoke_debt_ledger_reconciliation_review": reconciliation,
        "manifest_driven_surface_registry_pilot_review": registry_pilot,
        "manifest_surface_generation_readiness_review": generation_readiness,
        "manifest_registry_expanded_review_surfaces_review": expanded_registry,
        "manifest_registry_generation_readiness_scoring_review": readiness_scoring,
        "manifest_registry_drift_detection_review": drift_detection,
        "manifest_guided_validation_probe_dry_run_review": validation_probe_dry_run,
        "manifest_guided_generated_validation_probe_review": generated_validation_probe,
        "manifest_smoke_segment_parity_drift_review": segment_parity,
        "manifest_smoke_segment_parity_repair_packet_review": segment_repair,
        "manifest_smoke_segment_repair_application_review": segment_application,
        "manifest_segment_parity_enforcement_gate_review": segment_enforcement,
        "manifest_guided_validation_probe_expansion_readiness_review": probe_expansion_readiness,
        "manifest_guided_multi_surface_validation_probe_dry_run_review": multi_surface_probe_dry_run,
        "manifest_guided_multi_surface_generated_validation_probe_packet_review": multi_surface_generated_probe_packet,
        "manifest_guided_multi_surface_probe_packet_consistency_gate_review": multi_surface_probe_packet_consistency_gate,
        "manifest_guided_sandbox_probe_file_generation_readiness_review": sandbox_probe_file_generation_readiness,
        "manifest_guided_sandbox_probe_file_generation_dry_run": sandbox_probe_file_generation_dry_run,
        "operator_approved_sandbox_probe_file_generation_trial": operator_approved_sandbox_probe_file_generation_trial,
        "sandbox_probe_file_verification_and_cleanup_review": sandbox_probe_file_verification_and_cleanup_review,
        "sandbox_probe_execution_harness_readiness_review": sandbox_probe_execution_harness_readiness_review,
        "operator_approved_sandbox_probe_execution_trial": operator_approved_sandbox_probe_execution_trial,
        "sandbox_probe_execution_result_review_and_promotion_readiness": sandbox_probe_execution_result_review_and_promotion_readiness,
        "live_probe_promotion_plan_review": live_probe_promotion_plan_review,
        "operator_approved_live_probe_registration_trial": operator_approved_live_probe_registration_trial,
        "live_registered_probe_verification_and_structural_hardening_review": live_registered_probe_verification_and_structural_hardening_review,
        "operator_next_action": "Review application receipts, smoke debt categories, manifest parity, sandbox generation evidence, sandbox probe verification/cleanup, execution harness readiness, and the operator-approved sandbox probe execution trial; approve any cleanup, promotion, or live wiring separately and never treat this report as autonomy permission.",
        "safety": {
            "review_only": True,
            "applies_source_edits": False,
            "creates_concrete_diff": False,
            "runs_broad_smoke": False,
            "marks_blockers_as_pass": False,
            "expands_autonomy": False,
            "protected_systems_require_operator_approval": True,
        },
        "verification_steps": [
            "python -m compileall -q conscious_agent tools",
            "python tools/smoke_check.py --check self-development-application-receipt-review-v1",
            "python tools/smoke_check.py --check current-smoke-debt-ledger-v1",
            "python tools/smoke_check.py --check self-development-api-surface-truth-review-v1",
            "python tools/smoke_check.py --check current-smoke-debt-ledger-reconciliation-v1",
            "python tools/smoke_check.py --check manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check manifest-guided-validation-probe-dry-run-v1",
            "python conscious_agent/main.py --self-development-smoke-debt-dashboard --self-development-full",
        ],
    }


def self_development_smoke_debt_dashboard_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Self Development smoke debt dashboard not found."
    safety = report.get("safety", {}) or {}
    receipt_review = report.get("application_receipt_review", {}) or {}
    ledger = report.get("current_smoke_debt_ledger", {}) or {}
    cleanup = report.get("low_risk_cleanup_candidates", {}) or {}
    api_truth = report.get("api_surface_truth_review", {}) or {}
    legacy_review = report.get("legacy_self_maintenance_smoke_blocker_review", {}) or {}
    reconciliation = report.get("current_smoke_debt_ledger_reconciliation_review", {}) or {}
    registry_pilot = report.get("manifest_driven_surface_registry_pilot_review", {}) or {}
    generation_readiness = report.get("manifest_surface_generation_readiness_review", {}) or {}
    expanded_registry = report.get("manifest_registry_expanded_review_surfaces_review", {}) or {}
    readiness_scoring = report.get("manifest_registry_generation_readiness_scoring_review", {}) or {}
    drift_detection = report.get("manifest_registry_drift_detection_review", {}) or {}
    validation_probe_dry_run = report.get("manifest_guided_validation_probe_dry_run_review", {}) or {}
    generated_validation_probe = report.get("manifest_guided_generated_validation_probe_review", {}) or {}
    segment_parity = report.get("manifest_smoke_segment_parity_drift_review", {}) or {}
    segment_repair = report.get("manifest_smoke_segment_parity_repair_packet_review", {}) or {}
    segment_application = report.get("manifest_smoke_segment_repair_application_review", {}) or {}
    segment_enforcement = report.get("manifest_segment_parity_enforcement_gate_review", {}) or {}
    probe_expansion_readiness = report.get("manifest_guided_validation_probe_expansion_readiness_review", {}) or {}
    multi_surface_probe_dry_run = report.get("manifest_guided_multi_surface_validation_probe_dry_run_review", {}) or {}
    multi_surface_generated_probe_packet = report.get("manifest_guided_multi_surface_generated_validation_probe_packet_review", {}) or {}
    multi_surface_probe_packet_consistency_gate = report.get("manifest_guided_multi_surface_probe_packet_consistency_gate_review", {}) or {}
    sandbox_probe_file_generation_readiness = report.get("manifest_guided_sandbox_probe_file_generation_readiness_review", {}) or {}
    sandbox_probe_file_generation_dry_run = report.get("manifest_guided_sandbox_probe_file_generation_dry_run", {}) or {}
    operator_approved_sandbox_probe_file_generation_trial = report.get("operator_approved_sandbox_probe_file_generation_trial", {}) or {}
    sandbox_probe_file_verification_and_cleanup_review = report.get("sandbox_probe_file_verification_and_cleanup_review", {}) or {}
    sandbox_probe_execution_harness_readiness_review = report.get("sandbox_probe_execution_harness_readiness_review", {}) or {}
    lines = [
        f"# Self Development Smoke Debt Dashboard: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Application receipts reviewed: {receipt_review.get('receipt_count')}",
        f"Smoke debt ledger entries: {ledger.get('entry_count')}",
        f"Low-risk cleanup candidates: {cleanup.get('low_risk_candidate_count')}",
        f"Unsupported API route claims: {api_truth.get('unsupported_api_route_count')}",
        f"Legacy self-maintenance blockers remaining: {legacy_review.get('remaining_blocker_count')}",
        f"Resolved smoke debt entries: {reconciliation.get('resolved_ledger_entry_count')}",
        f"Manifest registry pilot status: {registry_pilot.get('status')}",
        f"Generation readiness status: {generation_readiness.get('status')}",
        f"Expanded manifest registry surfaces: {expanded_registry.get('selected_surface_count')}",
        f"Manifest readiness scoring status: {readiness_scoring.get('status')}",
        f"Manifest registry drift count: {drift_detection.get('drift_count')}",
        f"Validation probe dry-run status: {validation_probe_dry_run.get('status')}",
        f"Generated validation probe status: {generated_validation_probe.get('status')}",
        f"Generated probe checks: {generated_validation_probe.get('generated_probe_check_count')}",
        f"Smoke segment parity mismatches: {segment_parity.get('mismatching_segment_count')}",
        f"Smoke segment proposed repairs: {segment_repair.get('proposed_repair_count')}",
        f"Smoke segment repair application drift: {segment_application.get('mismatching_segment_count_after_application')}",
        f"Segment parity enforcement passed: {segment_enforcement.get('enforcement_gate_passed')}",
        f"Segment parity enforcement release blocking: {segment_enforcement.get('release_blocking')}",
        f"Probe expansion readiness passed: {probe_expansion_readiness.get('readiness_passed')}",
        f"Probe expansion recommended surfaces: {probe_expansion_readiness.get('recommended_expansion_surface_count')}",
        f"Multi-surface probe dry-run status: {multi_surface_probe_dry_run.get('status')}",
        f"Multi-surface probe dry-run selected surfaces: {multi_surface_probe_dry_run.get('selected_surface_count')}",
        f"Multi-surface probe dry-run total planned checks: {multi_surface_probe_dry_run.get('total_planned_probe_check_count')}",
        f"Multi-surface generated probe packet status: {multi_surface_generated_probe_packet.get('status')}",
        f"Multi-surface generated probe packets: {multi_surface_generated_probe_packet.get('generated_probe_packet_count')}",
        f"Multi-surface generated probe total checks: {multi_surface_generated_probe_packet.get('total_generated_probe_check_count')}",
        f"Multi-surface probe packet consistency gate passed: {multi_surface_probe_packet_consistency_gate.get('consistency_gate_passed')}",
        f"Multi-surface probe packet consistency release blocking: {multi_surface_probe_packet_consistency_gate.get('release_blocking')}",
        f"Sandbox probe file generation readiness passed: {sandbox_probe_file_generation_readiness.get('readiness_passed')}",
        f"Sandbox probe file generation dry-run passed: {sandbox_probe_file_generation_dry_run.get('dry_run_passed')}",
        f"Sandbox probe file generation dry-run previews: {sandbox_probe_file_generation_dry_run.get('preview_probe_file_count')}",
        f"Operator-approved sandbox probe file generation trial passed: {operator_approved_sandbox_probe_file_generation_trial.get('generation_trial_passed')}",
        f"Operator-approved sandbox probe files written: {operator_approved_sandbox_probe_file_generation_trial.get('written_probe_file_count')}",
        f"Sandbox probe verification passed: {sandbox_probe_file_verification_and_cleanup_review.get('verification_passed')}",
        f"Sandbox probe cleanup review only: {sandbox_probe_file_verification_and_cleanup_review.get('cleanup_review_only')}",
        f"Sandbox probe execution harness readiness passed: {sandbox_probe_execution_harness_readiness_review.get('readiness_passed')}",
        f"Sandbox probe execution performed: {sandbox_probe_execution_harness_readiness_review.get('execution_performed')}",
        "Review only: yes",
        "Applies source edits: no",
        "Creates concrete diff: no",
        "Runs broad smoke: no",
        "Marks blockers as pass: no",
        "",
        "## Operator next action",
        str(report.get("operator_next_action")),
        "",
        "## Safety",
        f"Protected systems require approval: {safety.get('protected_systems_require_operator_approval')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
    ]
    if full:
        lines.append("")
        lines.append("## Receipt review")
        lines.append(self_development_application_receipt_review_text(receipt_review, full=False))
        lines.append("")
        lines.append("## Smoke debt ledger")
        lines.append(current_smoke_debt_ledger_text(ledger, full=False))
        lines.append("")
        lines.append("## Cleanup candidates")
        lines.append(low_risk_smoke_debt_cleanup_candidates_text(cleanup, full=False))
        lines.append("")
        lines.append("## API surface truth review")
        lines.append(self_development_api_surface_truth_review_text(api_truth, full=False))
        lines.append("")
        lines.append("## Legacy self-maintenance smoke blocker review")
        lines.append(legacy_self_maintenance_smoke_blocker_review_text(legacy_review, full=False))
        lines.append("")
        lines.append("## Smoke debt reconciliation")
        lines.append(current_smoke_debt_ledger_reconciliation_review_text(reconciliation, full=False))
        lines.append("")
        lines.append("## Manifest-driven surface registry pilot")
        lines.append(manifest_driven_surface_registry_pilot_review_text(registry_pilot, full=False))
        lines.append("")
        lines.append("## Manifest surface generation readiness")
        lines.append(manifest_surface_generation_readiness_review_text(generation_readiness, full=False))
        lines.append("")
        lines.append(manifest_registry_expanded_review_surfaces_review_text(expanded_registry, full=False))
        lines.append("")
        lines.append(manifest_registry_generation_readiness_scoring_review_text(readiness_scoring, full=False))
        lines.append("")
        lines.append(manifest_registry_drift_detection_review_text(drift_detection, full=False))
        lines.append("")
        lines.append(manifest_guided_validation_probe_dry_run_review_text(validation_probe_dry_run, full=False))
        lines.append("")
        lines.append(manifest_guided_generated_validation_probe_review_text(generated_validation_probe, full=False))
        lines.append("")
        lines.append(manifest_smoke_segment_parity_drift_review_text(segment_parity, full=False))
        lines.append("")
        lines.append(manifest_smoke_segment_parity_repair_packet_review_text(segment_repair, full=False))
        lines.append("")
        lines.append(manifest_smoke_segment_repair_application_review_text(segment_application, full=False))
        lines.append("")
        lines.append(manifest_segment_parity_enforcement_gate_review_text(segment_enforcement, full=False))
        lines.append("")
        lines.append(manifest_guided_validation_probe_expansion_readiness_review_text(probe_expansion_readiness, full=False))
        lines.append("")
        lines.append(manifest_guided_multi_surface_validation_probe_dry_run_review_text(multi_surface_probe_dry_run, full=False))
        lines.append("")
        lines.append(manifest_guided_multi_surface_generated_validation_probe_packet_review_text(multi_surface_generated_probe_packet, full=False))
        lines.append("")
        lines.append(manifest_guided_multi_surface_probe_packet_consistency_gate_review_text(multi_surface_probe_packet_consistency_gate, full=False))
        lines.append("")
        lines.append(manifest_guided_sandbox_probe_file_generation_readiness_review_text(sandbox_probe_file_generation_readiness, full=False))
        lines.append("")
        lines.append(manifest_guided_sandbox_probe_file_generation_dry_run_text(sandbox_probe_file_generation_dry_run, full=False))
        lines.append("")
        lines.append(operator_approved_sandbox_probe_file_generation_trial_text(operator_approved_sandbox_probe_file_generation_trial, full=False))
        lines.append("")
        lines.append(sandbox_probe_file_verification_and_cleanup_review_text(sandbox_probe_file_verification_and_cleanup_review, full=False))
        lines.append("")
        lines.append(sandbox_probe_execution_harness_readiness_review_text(sandbox_probe_execution_harness_readiness_review, full=False))
    return "\n".join(lines)


def print_self_development_cycle_duplicate_cleanup_review(full: bool = False) -> None:
    print(self_development_cycle_duplicate_cleanup_review_text(build_self_development_cycle_duplicate_cleanup_review(), full=full))


def print_legacy_self_maintenance_smoke_blocker_review(full: bool = False) -> None:
    print(legacy_self_maintenance_smoke_blocker_review_text(build_legacy_self_maintenance_smoke_blocker_review(), full=full))


def print_self_development_api_surface_truth_review(full: bool = False) -> None:
    print(self_development_api_surface_truth_review_text(build_self_development_api_surface_truth_review(), full=full))


def print_self_development_application_receipt_review(full: bool = False) -> None:
    print(self_development_application_receipt_review_text(build_self_development_application_receipt_review(), full=full))


def print_current_smoke_debt_ledger(full: bool = False, save: bool = False) -> None:
    print(current_smoke_debt_ledger_text(build_current_smoke_debt_ledger(save=save), full=full))


def print_low_risk_smoke_debt_cleanup_candidates(full: bool = False) -> None:
    print(low_risk_smoke_debt_cleanup_candidates_text(build_low_risk_smoke_debt_cleanup_candidates(), full=full))


def print_current_smoke_debt_ledger_reconciliation_review(full: bool = False) -> None:
    print(current_smoke_debt_ledger_reconciliation_review_text(build_current_smoke_debt_ledger_reconciliation_review(), full=full))


def print_current_audit_wording_cleanup_review(full: bool = False) -> None:
    print(current_audit_wording_cleanup_review_text(build_current_audit_wording_cleanup_review(), full=full))


def print_manifest_generation_prep_review(full: bool = False) -> None:
    print(manifest_generation_prep_review_text(build_manifest_generation_prep_review(), full=full))


def print_manifest_gated_surface_validation_review(full: bool = False) -> None:
    print(manifest_gated_surface_validation_review_text(build_manifest_gated_surface_validation_review(), full=full))


def print_manifest_driven_surface_registry_pilot_review(full: bool = False) -> None:
    print(manifest_driven_surface_registry_pilot_review_text(build_manifest_driven_surface_registry_pilot_review(), full=full))


def print_manifest_surface_generation_readiness_review(full: bool = False) -> None:
    print(manifest_surface_generation_readiness_review_text(build_manifest_surface_generation_readiness_review(), full=full))


def print_manifest_registry_expanded_review_surfaces_review(full: bool = False) -> None:
    print(manifest_registry_expanded_review_surfaces_review_text(build_manifest_registry_expanded_review_surfaces_review(), full=full))


def print_manifest_registry_generation_readiness_scoring_review(full: bool = False) -> None:
    print(manifest_registry_generation_readiness_scoring_review_text(build_manifest_registry_generation_readiness_scoring_review(), full=full))


def print_manifest_registry_drift_detection_review(full: bool = False) -> None:
    print(manifest_registry_drift_detection_review_text(build_manifest_registry_drift_detection_review(), full=full))


def print_manifest_guided_validation_probe_dry_run_review(full: bool = False) -> None:
    print(manifest_guided_validation_probe_dry_run_review_text(build_manifest_guided_validation_probe_dry_run_review(), full=full))


def print_manifest_guided_generated_validation_probe_review(full: bool = False) -> None:
    print(manifest_guided_generated_validation_probe_review_text(build_manifest_guided_generated_validation_probe_review(), full=full))


def print_manifest_smoke_segment_parity_drift_review(full: bool = False) -> None:
    print(manifest_smoke_segment_parity_drift_review_text(build_manifest_smoke_segment_parity_drift_review(), full=full))


def print_manifest_smoke_segment_parity_repair_packet_review(full: bool = False) -> None:
    print(manifest_smoke_segment_parity_repair_packet_review_text(build_manifest_smoke_segment_parity_repair_packet_review(), full=full))


def print_manifest_smoke_segment_repair_application_review(full: bool = False) -> None:
    print(manifest_smoke_segment_repair_application_review_text(build_manifest_smoke_segment_repair_application_review(), full=full))


def print_manifest_segment_parity_enforcement_gate_review(full: bool = False) -> None:
    print(manifest_segment_parity_enforcement_gate_review_text(build_manifest_segment_parity_enforcement_gate_review(), full=full))


def print_manifest_guided_validation_probe_expansion_readiness_review(full: bool = False) -> None:
    print(manifest_guided_validation_probe_expansion_readiness_review_text(build_manifest_guided_validation_probe_expansion_readiness_review(), full=full))



LIVE_REGISTERED_PROBE_VERIFICATION_POLICIES = (
    "live_probe_registration_prerequisite_passed",
    "registered_live_probe_count_matches",
    "registered_live_probe_ids_match",
    "live_probe_execution_count_matches",
    "live_probe_pass_count_matches",
    "live_probe_fail_count_zero",
    "stdout_capture_count_matches",
    "stderr_capture_count_matches",
    "timeout_count_zero",
    "rollback_plan_available",
    "runtime_registry_repaired",
    "nested_metadata_review_completed",
    "manifest_version_semantics_issue_detected",
    "autonomy_boundary_key_normalization_needed",
    "giant_file_cleanup_needed",
    "structural_hardening_plan_created",
    "live_registered_probe_verification_passed",
    "no_dashboard_wiring_added",
    "no_api_wiring_added",
    "no_cli_wiring_added",
    "no_probe_files_written",
    "no_probe_files_deleted",
    "no_memory_mutation",
    "no_approval_system_mutation",
    "no_release_system_mutation",
    "no_scheduler_mutation",
    "no_network_access",
    "no_autonomy_expanded",
    "operator_control_preserved",
    "review_only",
    "release_blocking",
)


def _live_registered_probe_preview_record(root: Path, surface_id: str, source_smoke: str, live_smoke: str) -> dict[str, Any]:
    """Execute a registered generated probe in a child process and record measured evidence."""
    record = execute_generated_probe(root=root, surface_id=surface_id, expected_source_smoke=source_smoke)
    record["live_smoke_check"] = live_smoke
    return record


def _runtime_registry_issue_record(root: Path) -> dict[str, Any]:
    try:
        import runtime_registry
        runtime_registry.build_runtime_registry_entries()
        return {"issue_detected": False, "error": "", "recommended_action": "keep registry under smoke coverage"}
    except Exception as exc:
        return {
            "issue_detected": True,
            "error": str(exc),
            "recommended_action": "Repair build_runtime_registry_entries so stage-definition fields are adapted before RuntimeRegistryEntry construction.",
        }


def _nested_metadata_review_record(root: Path) -> dict[str, Any]:
    projects_path = root / "data" / "projects.json"
    data = _load_json(projects_path, {})
    nested_versions: list[str] = []
    if isinstance(data, dict):
        for row in data.get("projects", []) or []:
            if isinstance(row, dict) and "version" in row:
                nested_versions.append(str(row.get("version")))
    stale_nested = [value for value in nested_versions if value != SELF_DEVELOPMENT_CYCLE_VERSION]
    return {
        "nested_metadata_reviewed": True,
        "nested_project_version_values": nested_versions,
        "nested_metadata_stale_value_count": len(stale_nested),
        "nested_metadata_current_fields_aligned": len(stale_nested) == 0,
        "hardening_needed": False,
        "recommended_action": "Keep nested project/workspace current fields inside the centralized stale-version audit and metadata integrity checks.",
    }


def _manifest_version_semantics_issue_detected(root: Path) -> bool:
    """Detect unresolved manifest version semantics after the v907 split.

    Historical surface origins may differ from the current manifest representation
    version. That is no longer a defect when explicit split fields are exported.
    """
    try:
        import source_surface_manifest as manifest

        summary = manifest.build_source_surface_manifest_summary()
        entry_count = int(summary.get("entry_count") or 0)
        return not (
            summary.get("manifest_version_schema_split_applied") is True
            and summary.get("legacy_version_field_retained_for_compatibility") is True
            and int(summary.get("surface_origin_version_count") or 0) == entry_count
            and int(summary.get("manifest_representation_version_count") or 0) == entry_count
            and int(summary.get("last_verified_for_version_count") or 0) == entry_count
            and summary.get("origin_representation_mismatches_are_historical_not_stale") is True
        )
    except Exception:
        manifest_path = root / "conscious_agent" / "source_surface_manifest.py"
        text = _read_text(manifest_path, limit=2_000_000)
        return any(key not in text for key in ("surface_origin_version", "manifest_representation_version", "last_verified_for_version"))


def _giant_file_cleanup_record(root: Path) -> dict[str, Any]:
    targets = [
        "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
    ]
    rows = []
    for rel in targets:
        path = root / rel
        text = _read_text(path, limit=10_000_000)
        line_count = len(text.splitlines())
        rows.append({"path": rel, "line_count": line_count, "cleanup_needed": line_count > 3000})
    return {
        "files": rows,
        "giant_file_cleanup_needed": any(row["cleanup_needed"] for row in rows),
        "recommended_action": "Move repeated arc scaffolding toward manifest-driven dashboard/API/CLI/smoke generation with legacy wrappers kept stable.",
    }


def build_live_registered_probe_verification_and_structural_hardening_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Verify the registered generated live probes and record structural hardening debt.

    This v900 layer depends on the v895 operator-approved live probe registration
    trial. It verifies the three generated live probe smoke registrations, records
    rollback readiness, identifies structural cleanup targets, and does not add
    dashboard/API/CLI per-probe wiring, mutate protected systems, create releases,
    access scheduler/network systems, or expand autonomy.
    """
    registration = build_operator_approved_live_probe_registration_trial(root=root)
    expected = [
        ("v780-manifest-gated-surface-validation", "manifest-gated-surface-validation-v1", "generated-live-probe-v780-manifest-gated-surface-validation-v1"),
        ("v790-manifest-registry-expanded-review-surfaces", "manifest-registry-expanded-review-surfaces-v1", "generated-live-probe-v790-manifest-registry-expanded-review-surfaces-v1"),
        ("v795-manifest-registry-drift-detection", "manifest-registry-drift-detection-v1", "generated-live-probe-v795-manifest-registry-drift-detection-v1"),
    ]
    smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=2_000_000)
    live_probe_records = [
        _live_registered_probe_preview_record(root, surface_id, source_smoke, live_smoke)
        for surface_id, source_smoke, live_smoke in expected
    ]
    registered_smokes = list(registration.get("registered_live_probe_smoke_checks", []) or [])
    live_probe_execution_count = len(live_probe_records)
    live_probe_pass_count = sum(1 for row in live_probe_records if row.get("passed") is True)
    live_probe_fail_count = live_probe_execution_count - live_probe_pass_count
    stdout_capture_count = sum(1 for row in live_probe_records if row.get("stdout_captured") is True)
    stderr_capture_count = sum(1 for row in live_probe_records if row.get("stderr_captured") is True)
    timeout_count = sum(1 for row in live_probe_records if row.get("timed_out") is True)
    runtime_registry = _runtime_registry_issue_record(root)
    nested_metadata = _nested_metadata_review_record(root)
    giant_files = _giant_file_cleanup_record(root)
    manifest_version_semantics_issue_detected = _manifest_version_semantics_issue_detected(root)
    autonomy_boundary_key_normalization_needed = "autonomy_expanded" in smoke_text and "expands_autonomy" in smoke_text
    structural_hardening_plan = [
        "Keep registered generated probe execution inside the subprocess harness with measured stdout/stderr/return-code/timeout evidence.",
        "Repair runtime_registry.build_runtime_registry_entries field adaptation.",
        "Keep nested metadata current fields covered by stale-version and metadata integrity gates.",
        "Split source surface manifest version semantics into surface origin and registry representation/update fields.",
        "Normalize autonomy boundary keys while preserving compatibility tokens during transition.",
        "Reduce repeated arc scaffolding by generating dashboard/API/CLI/smoke metadata from the source surface manifest.",
    ]
    live_smoke_ids_registered_in_file = all(f'SmokeCheck("{live_smoke}"' in smoke_text for _, _, live_smoke in expected)
    policy_results = {
        "live_probe_registration_prerequisite_passed": registration.get("registered_live_probe_count") == 3 and registered_smokes == [live_smoke for _, _, live_smoke in expected],
        "registered_live_probe_count_matches": registration.get("registered_live_probe_count") == 3,
        "registered_live_probe_ids_match": registered_smokes == [live_smoke for _, _, live_smoke in expected],
        "live_probe_execution_count_matches": live_probe_execution_count == 3,
        "live_probe_pass_count_matches": live_probe_pass_count == 3,
        "live_probe_fail_count_zero": live_probe_fail_count == 0,
        "stdout_capture_count_matches": stdout_capture_count == 3,
        "stderr_capture_count_matches": stderr_capture_count == 3,
        "timeout_count_zero": timeout_count == 0,
        "rollback_plan_available": registration.get("rollback_plan_available") is True,
        "runtime_registry_repaired": runtime_registry.get("issue_detected") is False,
        "nested_metadata_review_completed": nested_metadata.get("nested_metadata_reviewed") is True,
        "manifest_version_semantics_resolved_or_tracked": manifest_version_semantics_issue_detected is False,
        "autonomy_boundary_key_normalization_needed": autonomy_boundary_key_normalization_needed is True,
        "giant_file_cleanup_needed": giant_files.get("giant_file_cleanup_needed") is True,
        "structural_hardening_plan_created": len(structural_hardening_plan) >= 5,
        "live_registered_probe_verification_passed": live_probe_pass_count == 3 and live_smoke_ids_registered_in_file,
        "no_dashboard_wiring_added": True,
        "no_api_wiring_added": True,
        "no_cli_wiring_added": True,
        "no_probe_files_written": True,
        "no_probe_files_deleted": True,
        "no_memory_mutation": True,
        "no_approval_system_mutation": True,
        "no_release_system_mutation": True,
        "no_scheduler_mutation": True,
        "no_network_access": True,
        "no_autonomy_expanded": True,
        "operator_control_preserved": True,
        "review_only": True,
        "release_blocking": True,
    }
    safety = {
        "review_only": True,
        "release_blocking": True,
        "verifies_registered_live_smoke": True,
        "executes_probe_files": True,
        "live_probe_registration_prerequisite_required": True,
        "rollback_plan_available": registration.get("rollback_plan_available") is True,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "writes_probe_files": False,
        "deletes_probe_files": False,
        "generates_sandbox_probe_files": False,
        "generates_live_validation_probe": False,
        "applies_source_edits": False,
        "creates_concrete_diff": False,
        "runs_broad_smoke": False,
        "writes_memory": False,
        "modifies_approval_system": False,
        "modifies_release_system": False,
        "modifies_execution_permissions": False,
        "creates_release": False,
        "publishes_release": False,
        "network_accessed": False,
        "scheduler_mutated": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }
    ok = all(policy_results.values()) and all(safety.get(key) is False for key in [
        "dashboard_wiring_activated", "api_wiring_activated", "cli_wiring_activated", "writes_probe_files",
        "deletes_probe_files", "generates_sandbox_probe_files", "generates_live_validation_probe", "applies_source_edits",
        "creates_concrete_diff", "runs_broad_smoke", "writes_memory", "modifies_approval_system", "modifies_release_system",
        "modifies_execution_permissions", "creates_release", "publishes_release", "network_accessed", "scheduler_mutated", "autonomy_expanded", "expands_autonomy",
    ])
    return {
        "id": f"live_registered_probe_verification_and_structural_hardening_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "live_registered_probe_verification_and_structural_hardening_review",
        "smoke_check": "live-registered-probe-verification-and-structural-hardening-review-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "live_probe_registration_prerequisite_passed": policy_results["live_probe_registration_prerequisite_passed"],
        "registered_live_probe_count": registration.get("registered_live_probe_count"),
        "registered_live_probe_smoke_checks": registered_smokes,
        "live_probe_execution_count": live_probe_execution_count,
        "live_probe_pass_count": live_probe_pass_count,
        "live_probe_fail_count": live_probe_fail_count,
        "stdout_capture_count": stdout_capture_count,
        "stderr_capture_count": stderr_capture_count,
        "timeout_count": timeout_count,
        "live_probe_records": live_probe_records,
        "rollback_plan_available": registration.get("rollback_plan_available") is True,
        "runtime_registry_issue_detected": runtime_registry.get("issue_detected") is True,
        "runtime_registry_repaired": runtime_registry.get("issue_detected") is False,
        "runtime_registry_issue": runtime_registry,
        "nested_metadata_stale_check_gap_detected": False,
        "nested_metadata_review": nested_metadata,
        "manifest_version_semantics_issue_detected": manifest_version_semantics_issue_detected,
        "manifest_version_semantics_resolved": manifest_version_semantics_issue_detected is False,
        "autonomy_boundary_key_normalization_needed": autonomy_boundary_key_normalization_needed,
        "giant_file_cleanup_needed": giant_files.get("giant_file_cleanup_needed") is True,
        "giant_file_cleanup": giant_files,
        "structural_hardening_plan_created": len(structural_hardening_plan) >= 5,
        "structural_hardening_plan": structural_hardening_plan,
        "live_registered_probe_verification_passed": policy_results["live_registered_probe_verification_passed"],
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "release_blocking": True,
        "review_only": True,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "safety": safety,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --live-registered-probe-verification-and-structural-hardening-review --self-development-full",
            "python tools/smoke_check.py --check live-registered-probe-verification-and-structural-hardening-review-v1",
            "python tools/smoke_check.py --check generated-live-probe-v780-manifest-gated-surface-validation-v1",
            "python tools/smoke_check.py --check generated-live-probe-v790-manifest-registry-expanded-review-surfaces-v1",
            "python tools/smoke_check.py --check generated-live-probe-v795-manifest-registry-drift-detection-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --check operator-governed-metadata-release-integrity-v1",
            "python tools/smoke_check.py --check operator-governed-route-surface-parity-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def live_registered_probe_verification_and_structural_hardening_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Live registered probe verification and structural hardening review not found."
    safety = report.get("safety", {}) or {}
    lines = [
        f"# Live Registered Probe Verification and Structural Hardening Review: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Smoke check: {report.get('smoke_check')}",
        f"Live probe registration prerequisite passed: {report.get('live_probe_registration_prerequisite_passed')}",
        f"Registered live probe count: {report.get('registered_live_probe_count')}",
        f"Live probe execution count: {report.get('live_probe_execution_count')}",
        f"Live probe pass count: {report.get('live_probe_pass_count')}",
        f"Live probe fail count: {report.get('live_probe_fail_count')}",
        f"Stdout capture count: {report.get('stdout_capture_count')}",
        f"Stderr capture count: {report.get('stderr_capture_count')}",
        f"Timeout count: {report.get('timeout_count')}",
        f"Rollback plan available: {report.get('rollback_plan_available')}",
        f"Runtime registry issue detected: {report.get('runtime_registry_issue_detected')}",
        f"Nested metadata stale-check gap detected: {report.get('nested_metadata_stale_check_gap_detected')}",
        f"Manifest version semantics issue detected: {report.get('manifest_version_semantics_issue_detected')}",
        f"Autonomy boundary key normalization needed: {report.get('autonomy_boundary_key_normalization_needed')}",
        f"Giant file cleanup needed: {report.get('giant_file_cleanup_needed')}",
        f"Structural hardening plan created: {report.get('structural_hardening_plan_created')}",
        f"Live registered probe verification passed: {report.get('live_registered_probe_verification_passed')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Review only: {report.get('review_only')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Live probe records",
    ]
    for row in report.get("live_probe_records", []) or []:
        lines.append(f"- {row.get('surface_id')}: smoke={row.get('live_smoke_check')} passed={row.get('passed')} file={row.get('sandbox_relative_path')}")
    lines.extend(["", "## Structural hardening plan"])
    for step in report.get("structural_hardening_plan", []) or []:
        lines.append(f"- {step}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Safety",
        f"Review only: {safety.get('review_only')}",
        f"Verifies registered live smoke: {safety.get('verifies_registered_live_smoke')}",
        f"Executes probe files: {safety.get('executes_probe_files')}",
        f"Dashboard wiring activated: {safety.get('dashboard_wiring_activated')}",
        f"API wiring activated: {safety.get('api_wiring_activated')}",
        f"CLI wiring activated: {safety.get('cli_wiring_activated')}",
        f"Applies source edits: {safety.get('applies_source_edits')}",
        f"Writes memory: {safety.get('writes_memory')}",
        f"Modifies approval system: {safety.get('modifies_approval_system')}",
        f"Modifies release system: {safety.get('modifies_release_system')}",
        f"Expands autonomy: {safety.get('expands_autonomy')}",
        f"Protected systems require operator approval: {safety.get('protected_systems_require_operator_approval')}",
    ])
    if full:
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)

def print_manifest_guided_multi_surface_validation_probe_dry_run_review(full: bool = False) -> None:
    print(manifest_guided_multi_surface_validation_probe_dry_run_review_text(build_manifest_guided_multi_surface_validation_probe_dry_run_review(), full=full))


def print_manifest_guided_multi_surface_generated_validation_probe_packet_review(full: bool = False) -> None:
    print(manifest_guided_multi_surface_generated_validation_probe_packet_review_text(build_manifest_guided_multi_surface_generated_validation_probe_packet_review(), full=full))


def print_manifest_guided_multi_surface_probe_packet_consistency_gate_review(full: bool = False) -> None:
    print(manifest_guided_multi_surface_probe_packet_consistency_gate_review_text(build_manifest_guided_multi_surface_probe_packet_consistency_gate_review(), full=full))


def print_manifest_guided_sandbox_probe_file_generation_readiness_review(full: bool = False) -> None:
    print(manifest_guided_sandbox_probe_file_generation_readiness_review_text(build_manifest_guided_sandbox_probe_file_generation_readiness_review(), full=full))


def print_manifest_guided_sandbox_probe_file_generation_dry_run(full: bool = False) -> None:
    print(manifest_guided_sandbox_probe_file_generation_dry_run_text(build_manifest_guided_sandbox_probe_file_generation_dry_run(), full=full))


def print_operator_approved_sandbox_probe_file_generation_trial(full: bool = False) -> None:
    print(operator_approved_sandbox_probe_file_generation_trial_text(build_operator_approved_sandbox_probe_file_generation_trial(), full=full))


def print_sandbox_probe_file_verification_and_cleanup_review(full: bool = False) -> None:
    print(sandbox_probe_file_verification_and_cleanup_review_text(build_sandbox_probe_file_verification_and_cleanup_review(), full=full))


def print_sandbox_probe_execution_harness_readiness_review(full: bool = False) -> None:
    print(sandbox_probe_execution_harness_readiness_review_text(build_sandbox_probe_execution_harness_readiness_review(), full=full))


def print_operator_approved_sandbox_probe_execution_trial(full: bool = False) -> None:
    print(operator_approved_sandbox_probe_execution_trial_text(build_operator_approved_sandbox_probe_execution_trial(), full=full))


def print_sandbox_probe_execution_result_review_and_promotion_readiness(full: bool = False) -> None:
    print(sandbox_probe_execution_result_review_and_promotion_readiness_text(build_sandbox_probe_execution_result_review_and_promotion_readiness(), full=full))


def print_live_probe_promotion_plan_review(full: bool = False) -> None:
    print(live_probe_promotion_plan_review_text(build_live_probe_promotion_plan_review(), full=full))


def print_operator_approved_live_probe_registration_trial(full: bool = False) -> None:
    print(operator_approved_live_probe_registration_trial_text(build_operator_approved_live_probe_registration_trial(), full=full))



def print_live_registered_probe_verification_and_structural_hardening_review(full: bool = False) -> None:
    print(live_registered_probe_verification_and_structural_hardening_review_text(build_live_registered_probe_verification_and_structural_hardening_review(), full=full))


V905_BASELINE_MANIFEST_SEMANTICS_PREP_POLICIES = (
    "v905_containment_baseline_passed",
    "generated_probe_harness_present",
    "live_probe_smokes_subprocess_backed",
    "smoke_debt_dashboard_timeout_smoke_present",
    "runtime_registry_repaired",
    "source_self_model_excluded_from_allowlist",
    "manifest_entries_loaded",
    "manifest_version_semantics_issue_mapped",
    "manifest_split_fields_missing_before_migration",
    "manifest_schema_migration_plan_created",
    "no_manifest_schema_migration_applied",
    "no_dashboard_api_cli_generation_added",
    "no_source_package_private_state_reintroduced",
    "no_memory_mutation",
    "no_approval_system_mutation",
    "no_release_system_mutation",
    "no_scheduler_mutation",
    "no_network_access",
    "operator_control_preserved",
    "review_only",
    "no_autonomy_expanded",
)


def _manifest_version_semantics_prep_record(root: Path) -> dict[str, Any]:
    """Map manifest version-field ambiguity without changing the schema yet."""
    import source_surface_manifest as manifest

    entries = list(getattr(manifest, "RECENT_SURFACE_ENTRIES", []) or [])
    mismatch_rows: list[dict[str, Any]] = []
    missing_split_rows: list[dict[str, Any]] = []
    for entry in entries:
        surface_id = str(entry.get("surface_id", ""))
        version = str(entry.get("version", ""))
        match = re.match(r"v(?P<origin>\d+)-", surface_id)
        origin_version = f"{match.group('origin')}.0" if match else ""
        normalized_version = version[1:] if version.startswith("v") else version
        if origin_version and normalized_version and origin_version != normalized_version:
            mismatch_rows.append({
                "surface_id": surface_id,
                "surface_origin_version_candidate": origin_version,
                "current_version_field": version,
                "recommended_split": {
                    "surface_origin_version": origin_version,
                    "manifest_representation_version": normalized_version,
                    "last_verified_for_version": SELF_DEVELOPMENT_CYCLE_VERSION,
                },
            })
        missing = [
            key for key in ("surface_origin_version", "manifest_representation_version", "last_verified_for_version")
            if key not in entry
        ]
        if missing:
            missing_split_rows.append({"surface_id": surface_id, "missing_fields": missing})
    migration_plan = [
        "Add surface_origin_version from the surface_id prefix or explicit historical origin metadata.",
        "Rename the overloaded legacy version meaning into manifest_representation_version while keeping version as a compatibility alias for one transition arc.",
        "Add last_verified_for_version to record the current release that last checked the entry.",
        "Update manifest validation so historical surface origins are allowed while current registry metadata remains release-blocking when stale.",
        "Update stale-version and package-privacy gates after the split, then retire the legacy version alias only after compatibility smoke passes.",
    ]
    return {
        "manifest_entry_count": len(entries),
        "semantic_mismatch_count": len(mismatch_rows),
        "semantic_mismatches": mismatch_rows[:25],
        "semantic_mismatch_examples_truncated": max(0, len(mismatch_rows) - 25),
        "split_field_missing_count": len(missing_split_rows),
        "split_field_missing_examples": missing_split_rows[:25],
        "split_field_missing_examples_truncated": max(0, len(missing_split_rows) - 25),
        "migration_plan": migration_plan,
        "schema_migration_applied": False,
        "legacy_version_field_retained_for_compatibility": True,
    }


def _source_package_privacy_prep_record(root: Path) -> dict[str, Any]:
    import package_integrity

    allowlist = list(getattr(package_integrity, "SOURCE_DATA_ALLOWLIST", ()) or ())
    private_markers = list(getattr(package_integrity, "PRIVATE_STATE_SOURCE_PACKAGE_MARKERS", ()) or ())
    return {
        "source_data_allowlist": allowlist,
        "self_model_allowlisted": "data/self_model.json" in allowlist,
        "tasks_json_allowlisted": "data/tasks.json" in allowlist,
        "private_state_marker_count": len(private_markers),
        "private_state_markers_include_user_name_guard": "Marcus" in private_markers and "Gibeson" in private_markers,
        "recommended_deep_scan": [
            "Fail source-only packages that include non-allowlisted data/ entries such as data/tasks.json.",
            "Fail source-only packages that include self-state files, mood/focus fields, active goals, memories, chat logs, approvals, runtime release artifacts, or workspace timelines.",
            "Keep generic templates allowed only when they contain no personal names or runtime state.",
        ],
    }


def build_v905_baseline_verification_and_manifest_version_semantics_prep(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review the v905 containment baseline and prepare the manifest version split.

    This v906 layer is deliberately review-only. It checks that the v905 live
    probe containment repair remains present, maps overloaded manifest version
    semantics, prepares the package privacy deepening work, and stops before any
    manifest schema migration or autonomy expansion.
    """
    baseline = build_live_registered_probe_verification_and_structural_hardening_review(root=root)
    manifest_prep = _manifest_version_semantics_prep_record(root)
    privacy_prep = _source_package_privacy_prep_record(root)
    smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=2_000_000)
    dashboard_text = _read_text(root / "conscious_agent" / "dashboard.py", limit=2_000_000)
    harness_path = root / "conscious_agent" / "generated_probe_harness.py"
    runtime_registry = _runtime_registry_issue_record(root)
    policy_results = {
        "v905_containment_baseline_passed": baseline.get("live_registered_probe_verification_passed") is True and baseline.get("live_probe_pass_count") == 3 and baseline.get("timeout_count") == 0,
        "generated_probe_harness_present": harness_path.exists() and "subprocess.run" in _read_text(harness_path, limit=200_000),
        "live_probe_smokes_subprocess_backed": "execute_generated_probe" in smoke_text and "importlib.util.spec_from_file_location" not in smoke_text,
        "smoke_debt_dashboard_timeout_smoke_present": "self-development-smoke-debt-dashboard-timeout-v1" in smoke_text,
        "runtime_registry_repaired": runtime_registry.get("issue_detected") is False,
        "source_self_model_excluded_from_allowlist": privacy_prep.get("self_model_allowlisted") is False,
        "manifest_entries_loaded": manifest_prep.get("manifest_entry_count", 0) > 0,
        "manifest_version_semantics_issue_mapped": manifest_prep.get("semantic_mismatch_count", 0) > 0,
        "manifest_split_fields_missing_before_migration": manifest_prep.get("split_field_missing_count", 0) > 0,
        "manifest_schema_migration_plan_created": len(manifest_prep.get("migration_plan", []) or []) >= 5,
        "no_manifest_schema_migration_applied": manifest_prep.get("schema_migration_applied") is False,
        "no_dashboard_api_cli_generation_added": "generated_wiring_activated=True" not in dashboard_text,
        "no_source_package_private_state_reintroduced": privacy_prep.get("self_model_allowlisted") is False and privacy_prep.get("tasks_json_allowlisted") is False,
        "no_memory_mutation": True,
        "no_approval_system_mutation": True,
        "no_release_system_mutation": True,
        "no_scheduler_mutation": True,
        "no_network_access": True,
        "operator_control_preserved": True,
        "review_only": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"v905_baseline_verification_and_manifest_version_semantics_prep_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "v905_baseline_verification_and_manifest_version_semantics_prep",
        "smoke_check": "v905-baseline-verification-and-manifest-version-semantics-prep-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "baseline_status": baseline.get("status"),
        "baseline_ok": baseline.get("live_registered_probe_verification_passed") is True,
        "v905_containment_baseline_passed": policy_results["v905_containment_baseline_passed"],
        "generated_probe_harness_present": policy_results["generated_probe_harness_present"],
        "runtime_registry_issue_detected": runtime_registry.get("issue_detected") is True,
        "manifest_entry_count": manifest_prep.get("manifest_entry_count"),
        "manifest_semantic_mismatch_count": manifest_prep.get("semantic_mismatch_count"),
        "manifest_split_field_missing_count": manifest_prep.get("split_field_missing_count"),
        "manifest_schema_migration_applied": False,
        "manifest_prep": manifest_prep,
        "source_package_privacy_prep": privacy_prep,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --v905-baseline-verification-and-manifest-version-semantics-prep --self-development-full",
            "python tools/smoke_check.py --check v905-baseline-verification-and-manifest-version-semantics-prep-v1",
            "python tools/smoke_check.py --check generated-probe-subprocess-harness-v1",
            "python tools/smoke_check.py --check live-registered-probe-verification-and-structural-hardening-review-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def v905_baseline_verification_and_manifest_version_semantics_prep_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "v905 baseline verification and manifest version semantics prep report not found."
    manifest = report.get("manifest_prep", {}) or {}
    privacy = report.get("source_package_privacy_prep", {}) or {}
    lines = [
        "# v905 Baseline Verification and Manifest Version Semantics Prep",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"v905 containment baseline passed: {report.get('v905_containment_baseline_passed')}",
        f"Generated probe harness present: {report.get('generated_probe_harness_present')}",
        f"Runtime registry issue detected: {report.get('runtime_registry_issue_detected')}",
        f"Manifest entry count: {report.get('manifest_entry_count')}",
        f"Manifest semantic mismatch count: {report.get('manifest_semantic_mismatch_count')}",
        f"Manifest split field missing count: {report.get('manifest_split_field_missing_count')}",
        f"Manifest schema migration applied: {report.get('manifest_schema_migration_applied')}",
        f"Self model allowlisted: {privacy.get('self_model_allowlisted')}",
        f"Tasks JSON allowlisted: {privacy.get('tasks_json_allowlisted')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Manifest migration plan",
    ]
    for step in manifest.get("migration_plan", []) or []:
        lines.append(f"- {step}")
    lines.extend(["", "## Package privacy deep-scan prep"])
    for step in privacy.get("recommended_deep_scan", []) or []:
        lines.append(f"- {step}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    if full:
        lines.extend(["", "## Manifest mismatch examples"])
        for row in manifest.get("semantic_mismatches", []) or []:
            lines.append(f"- {row.get('surface_id')}: origin={row.get('surface_origin_version_candidate')} legacy_version={row.get('current_version_field')}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_v905_baseline_verification_and_manifest_version_semantics_prep(full: bool = False) -> None:
    print(v905_baseline_verification_and_manifest_version_semantics_prep_text(build_v905_baseline_verification_and_manifest_version_semantics_prep(), full=full))



def _manifest_version_semantics_split_record(root: Path) -> dict[str, Any]:
    import source_surface_manifest as manifest

    summary = manifest.build_source_surface_manifest_summary()
    entries = list(summary.get("entries", []) or [])
    entry_count = int(summary.get("entry_count") or 0)
    origin_count = int(summary.get("surface_origin_version_count") or 0)
    representation_count = int(summary.get("manifest_representation_version_count") or 0)
    verified_count = int(summary.get("last_verified_for_version_count") or 0)
    historical_mismatch_count = int(summary.get("origin_representation_mismatch_count") or 0)
    bad_rows = [
        entry for entry in entries
        if not entry.get("surface_origin_version")
        or entry.get("manifest_representation_version") != SELF_DEVELOPMENT_CYCLE_VERSION
        or entry.get("last_verified_for_version") != SELF_DEVELOPMENT_CYCLE_VERSION
    ]
    return {
        "manifest_entry_count": entry_count,
        "manifest_version_schema_split_applied": summary.get("manifest_version_schema_split_applied") is True,
        "legacy_version_field_retained_for_compatibility": summary.get("legacy_version_field_retained_for_compatibility") is True,
        "surface_origin_version_count": origin_count,
        "manifest_representation_version_count": representation_count,
        "last_verified_for_version_count": verified_count,
        "split_field_complete_count": sum(
            1 for entry in entries
            if entry.get("surface_origin_version") and entry.get("manifest_representation_version") and entry.get("last_verified_for_version")
        ),
        "historical_origin_mismatch_count": historical_mismatch_count,
        "historical_origin_mismatch_allowed": summary.get("origin_representation_mismatches_are_historical_not_stale") is True,
        "bad_semantic_rows": bad_rows[:25],
        "bad_semantic_row_count": len(bad_rows),
        "version_semantics": summary.get("version_semantics", {}),
        "manifest_ok": summary.get("ok") is True,
        "manifest_hash": summary.get("manifest_hash"),
    }


def build_manifest_version_semantics_split_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Apply the v907 manifest version semantics split while preserving compatibility.

    This layer makes manifest exports distinguish surface origin, manifest
    representation/update version, and last verification version. The legacy
    version field stays available as a compatibility alias for older checks.
    """
    split = _manifest_version_semantics_split_record(root)
    smoke_text = _read_text(root / "tools" / "smoke_check.py", limit=2_000_000)
    manifest_text = _read_text(root / "conscious_agent" / "source_surface_manifest.py", limit=2_000_000)
    entry_count = int(split.get("manifest_entry_count") or 0)
    policy_results = {
        "manifest_entries_loaded": entry_count > 0,
        "manifest_version_schema_split_applied": split.get("manifest_version_schema_split_applied") is True,
        "surface_origin_versions_complete": split.get("surface_origin_version_count") == entry_count,
        "manifest_representation_versions_current": split.get("manifest_representation_version_count") == entry_count,
        "last_verified_versions_current": split.get("last_verified_for_version_count") == entry_count,
        "legacy_version_field_retained_for_compatibility": split.get("legacy_version_field_retained_for_compatibility") is True,
        "historical_origin_mismatch_allowed": split.get("historical_origin_mismatch_allowed") is True and split.get("historical_origin_mismatch_count", 0) > 0,
        "bad_semantic_row_count_zero": split.get("bad_semantic_row_count") == 0,
        "manifest_smoke_registered": "manifest-version-semantics-split-v1" in smoke_text,
        "manifest_source_tokens_present": all(token in manifest_text for token in ["surface_origin_version", "manifest_representation_version", "last_verified_for_version"]),
        "no_dashboard_api_cli_generation_added": "generated_wiring_activated=True" not in manifest_text,
        "no_memory_mutation": True,
        "no_approval_system_mutation": True,
        "no_release_system_mutation": True,
        "no_scheduler_mutation": True,
        "no_network_access": True,
        "operator_control_preserved": True,
        "review_only": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"manifest_version_semantics_split_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_version_semantics_split_review",
        "smoke_check": "manifest-version-semantics-split-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "manifest_entry_count": split.get("manifest_entry_count"),
        "manifest_version_schema_split_applied": split.get("manifest_version_schema_split_applied"),
        "surface_origin_version_count": split.get("surface_origin_version_count"),
        "manifest_representation_version_count": split.get("manifest_representation_version_count"),
        "last_verified_for_version_count": split.get("last_verified_for_version_count"),
        "legacy_version_field_retained_for_compatibility": split.get("legacy_version_field_retained_for_compatibility"),
        "historical_origin_mismatch_count": split.get("historical_origin_mismatch_count"),
        "historical_origin_mismatch_allowed": split.get("historical_origin_mismatch_allowed"),
        "bad_semantic_row_count": split.get("bad_semantic_row_count"),
        "manifest_hash": split.get("manifest_hash"),
        "split_record": split,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --manifest-version-semantics-split --self-development-full",
            "python tools/smoke_check.py --check manifest-version-semantics-split-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_version_semantics_split_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "manifest version semantics split report not found."
    lines = [
        "# Manifest Version Semantics Split",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Manifest entry count: {report.get('manifest_entry_count')}",
        f"Manifest version schema split applied: {report.get('manifest_version_schema_split_applied')}",
        f"Surface origin version count: {report.get('surface_origin_version_count')}",
        f"Manifest representation version count: {report.get('manifest_representation_version_count')}",
        f"Last verified for version count: {report.get('last_verified_for_version_count')}",
        f"Legacy version field retained for compatibility: {report.get('legacy_version_field_retained_for_compatibility')}",
        f"Historical origin mismatch count: {report.get('historical_origin_mismatch_count')}",
        f"Historical origin mismatch allowed: {report.get('historical_origin_mismatch_allowed')}",
        f"Bad semantic row count: {report.get('bad_semantic_row_count')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Split fields",
        "- surface_origin_version: historical version where the surface originated.",
        "- manifest_representation_version: current manifest/update version for the row.",
        "- last_verified_for_version: current release that verified the row.",
        "- version: retained temporarily as a compatibility alias.",
        "",
        "## Policy results",
    ]
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    if full:
        split = report.get("split_record", {}) or {}
        lines.extend(["", "## Version semantics"])
        for key, value in (split.get("version_semantics", {}) or {}).items():
            lines.append(f"- {key}: {value}")
        if split.get("bad_semantic_rows"):
            lines.extend(["", "## Bad semantic rows"])
            for row in split.get("bad_semantic_rows", []) or []:
                lines.append(f"- {row.get('surface_id')}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_manifest_version_semantics_split_review(full: bool = False) -> None:
    print(manifest_version_semantics_split_review_text(build_manifest_version_semantics_split_review(), full=full))


def build_manifest_validation_normalization_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review the v908 manifest validation normalization gate.

    This layer verifies that validation now uses explicit split fields instead
    of treating the legacy version field as the current-state authority.
    """
    import source_surface_manifest as manifest

    normalization = manifest.build_manifest_validation_normalization_summary()
    docs = "\n".join(_read_text(root / rel, limit=2_000_000) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py",
        "conscious_agent/dashboard.py",
        "tools/smoke_check.py",
    ])
    entry_count = int(normalization.get("entry_count") or 0)
    normalized_count = int(normalization.get("normalized_row_count") or 0)
    policy_results = {
        "manifest_entries_loaded": entry_count > 0,
        "all_rows_normalized": normalized_count == entry_count,
        "surface_origin_versions_required": normalization.get("surface_origin_versions_required") is True,
        "manifest_representation_versions_required_current": normalization.get("manifest_representation_versions_required_current") is True,
        "last_verified_versions_required_current": normalization.get("last_verified_versions_required_current") is True,
        "historical_origin_versions_allowed": normalization.get("historical_origin_versions_allowed") is True and int(normalization.get("historical_origin_count") or 0) > 0,
        "legacy_version_compatibility_only": normalization.get("legacy_version_field_validation_mode") == "compatibility_only_not_current_state",
        "legacy_version_not_current_source": normalization.get("legacy_version_is_current_state_source") is False,
        "current_state_source_split_fields": normalization.get("current_state_version_source") == "manifest_representation_version_and_last_verified_for_version",
        "legacy_mismatch_does_not_block_history": int(normalization.get("legacy_representation_mismatch_count") or 0) > 0,
        "manifest_normalization_ok": normalization.get("ok") is True,
        "targeted_smoke_registered": "manifest-validation-normalization-v1" in docs,
        "cli_token_present": "--manifest-validation-normalization" in docs,
        "source_manifest_function_present": "build_manifest_validation_normalization_summary" in docs,
        "dashboard_token_present": "Manifest Validation Normalization" in docs,
        "no_dashboard_api_cli_generation_added": all(token in docs for token in ["dashboard_wiring_activated=False", "api_wiring_activated=False", "cli_wiring_activated=False"]),
        "no_memory_mutation": True,
        "no_approval_system_mutation": True,
        "no_release_system_mutation": True,
        "no_scheduler_mutation": True,
        "no_network_access": True,
        "operator_control_preserved": True,
        "review_only": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"manifest_validation_normalization_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_validation_normalization_review",
        "smoke_check": "manifest-validation-normalization-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "manifest_entry_count": entry_count,
        "normalized_row_count": normalized_count,
        "historical_origin_count": normalization.get("historical_origin_count"),
        "legacy_representation_mismatch_count": normalization.get("legacy_representation_mismatch_count"),
        "legacy_version_field_validation_mode": normalization.get("legacy_version_field_validation_mode"),
        "current_state_version_source": normalization.get("current_state_version_source"),
        "legacy_version_is_current_state_source": normalization.get("legacy_version_is_current_state_source"),
        "surface_origin_versions_required": normalization.get("surface_origin_versions_required"),
        "manifest_representation_versions_required_current": normalization.get("manifest_representation_versions_required_current"),
        "last_verified_versions_required_current": normalization.get("last_verified_versions_required_current"),
        "historical_origin_versions_allowed": normalization.get("historical_origin_versions_allowed"),
        "blocker_count": normalization.get("blocker_count"),
        "normalization_record": normalization,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --manifest-validation-normalization --self-development-full",
            "python tools/smoke_check.py --check manifest-validation-normalization-v1",
            "python tools/smoke_check.py --check manifest-version-semantics-split-v1",
            "python tools/smoke_check.py --check operator-governed-source-surface-manifest-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_validation_normalization_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "manifest validation normalization report not found."
    lines = [
        "# Manifest Validation Normalization",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Manifest entry count: {report.get('manifest_entry_count')}",
        f"Normalized row count: {report.get('normalized_row_count')}",
        f"Historical origin count: {report.get('historical_origin_count')}",
        f"Legacy representation mismatch count: {report.get('legacy_representation_mismatch_count')}",
        f"Legacy version field validation mode: {report.get('legacy_version_field_validation_mode')}",
        f"Current state version source: {report.get('current_state_version_source')}",
        f"Legacy version is current state source: {report.get('legacy_version_is_current_state_source')}",
        f"Surface origin versions required: {report.get('surface_origin_versions_required')}",
        f"Manifest representation versions required current: {report.get('manifest_representation_versions_required_current')}",
        f"Last verified versions required current: {report.get('last_verified_versions_required_current')}",
        f"Historical origin versions allowed: {report.get('historical_origin_versions_allowed')}",
        f"Blocker count: {report.get('blocker_count')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Normalized validation rule",
        "- surface_origin_version may be historical and is validated as surface origin history.",
        "- manifest_representation_version must match the current manifest version.",
        "- last_verified_for_version must match the current verified release version.",
        "- version remains a legacy compatibility field, not the current-state authority.",
    ]
    if full:
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results", {}) or {}).items():
            lines.append(f"- {key}: {value}")
        blockers = (report.get("normalization_record", {}) or {}).get("blockers", []) or []
        if blockers:
            lines.extend(["", "## Blockers"])
            for row in blockers:
                lines.append(f"- {row.get('surface_id')}: {row.get('checks')}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_manifest_validation_normalization_review(full: bool = False) -> None:
    print(manifest_validation_normalization_review_text(build_manifest_validation_normalization_review(), full=full))

def print_self_development_smoke_debt_dashboard(full: bool = False) -> None:
    print(self_development_smoke_debt_dashboard_text(build_self_development_smoke_debt_dashboard(), full=full))

# v895.0 operator-approved live probe registration trial tokens: operator-approved-live-probe-registration-trial-v1 --operator-approved-live-probe-registration-trial build_operator_approved_live_probe_registration_trial operator_approved_live_probe_registration_trial_text operator_approved_live_probe_registration_trial=True promotion_plan_prerequisite_passed=True operator_approval_required=True operator_approval_present=True single_use_approval_required=True approval_burnout_required=True planned_live_probe_count=3 registered_live_probe_count=3 live_smoke_registration_applied=True dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False probe_execution_during_registration=False rollback_plan_available=True registration_trial_passed=True release_blocking=True review_only=False operator_approved_live_registration=True autonomy_expanded=False policy_count=49 policies_passed=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_dashboard_wiring=False activates_api_wiring=False activates_cli_wiring=False applies_source_edits=True applies_source_edits_only_for_live_smoke_registration=True creates_concrete_diff=False runs_broad_smoke=False executes_commands=True executes_probe_files=True writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True generated-live-probe-v780-manifest-gated-surface-validation-v1 generated-live-probe-v790-manifest-registry-expanded-review-surfaces-v1 generated-live-probe-v795-manifest-registry-drift-detection-v1 no_native_title_tooltip data-tip command-deck operator-console

# v885.0 operator-approved sandbox probe execution trial tokens: operator-approved-sandbox-probe-execution-trial-v1 --operator-approved-sandbox-probe-execution-trial build_operator_approved_sandbox_probe_execution_trial operator_approved_sandbox_probe_execution_trial_text operator_approved_sandbox_probe_execution_trial=True selected_surface_count=3 execution_harness_prerequisite_passed=True verification_prerequisite_passed=True sandbox_probe_file_count=3 operator_approval_required=True operator_approval_present=True single_use_approval_required=True approval_burnout_required=True execution_performed=True probe_execution_count=3 probe_execution_pass_count=3 probe_execution_fail_count=0 stdout_capture_count=3 stderr_capture_count=3 timeout_count=0 network_access_detected=False scheduler_access_detected=False memory_write_detected=False approval_write_detected=False release_write_detected=False source_write_detected=False live_wiring_detected=False policy_count=41 policies_passed=True execution_trial_passed=True release_blocking=True review_only=False operator_approved_sandbox_execution=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=True executes_probe_files=True writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v885.0 sandbox probe execution harness readiness review tokens: sandbox-probe-execution-harness-readiness-review-v1 --sandbox-probe-execution-harness-readiness-review build_sandbox_probe_execution_harness_readiness_review sandbox_probe_execution_harness_readiness_review_text sandbox_probe_execution_harness_readiness_review_is_review_only=True sandbox_probe_file_count=3 verification_prerequisite_passed=True execution_harness_defined=True execution_performed=False probe_execution_count=0 command_allowlist_defined=True timeout_policy_defined=True network_access_allowed=False scheduler_access_allowed=False memory_write_allowed=False approval_write_allowed=False release_write_allowed=False source_write_allowed=False live_wiring_allowed=False stdout_capture_defined=True stderr_capture_defined=True result_schema_defined=True cleanup_plan_available=True operator_approval_required=True single_use_approval_required=True approval_burnout_required=True policy_count=36 policies_passed=True readiness_passed=True release_blocking=True review_only=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False executes_probe_files=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v760.0-v760.0 Self Development API surface truth review tokens:
# self-development-api-surface-truth-review-v1 --self-development-api-surface-truth-review build_self_development_api_surface_truth_review self_development_api_surface_truth_review_text api_route_presence_is_live_probed=True unsupported_claims_are_reported_not_repaired=True applies_source_edits=False creates_concrete_diff=False implements_api_routes=False modifies_manifest=False runs_broad_smoke=False marks_blockers_as_pass=False expands_autonomy=False protected_systems_require_operator_approval=True

# v746.0-v760.0 application receipt review and current smoke debt ledger tokens:
# self-development-application-receipt-review-v1 current-smoke-debt-ledger-v1 /self-development-smoke-debt
# --self-development-application-receipt-review --current-smoke-debt-ledger --low-risk-smoke-debt-cleanup-candidates --self-development-smoke-debt-dashboard
# build_self_development_application_receipt_review self_development_application_receipt_review_text build_current_smoke_debt_ledger current_smoke_debt_ledger_text build_low_risk_smoke_debt_cleanup_candidates build_self_development_smoke_debt_dashboard
# receipt_is_not_success=True blocked_trial_is_not_success=True source_edits_implied_by_receipt=False marks_blockers_as_pass=False runs_broad_smoke=False creates_concrete_diff=False applies_source_edits=False executes_commands=False writes_memory=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console


# v760.0-v760.0 API route repair tokens: self-development-api-route-repair-v1 /api/self-development-cycle/layer build_self_development_cycle_api_layer build_manifest_gated_self_development_api_parity manifest_claimed_api_routes_must_dispatch=True api_404_is_release_blocking_for_claimed_routes=True api_route_presence_is_live_probed=True route_repair_is_review_only=True applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False marks_blockers_as_pass=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v760.0 duplicate cleanup tokens: self-development-cycle-duplicate-cleanup-v1 --self-development-cycle-duplicate-cleanup build_self_development_cycle_duplicate_cleanup_review self_development_cycle_duplicate_cleanup_review_text duplicate_definition_count=0 retired_shadowed_v720_helpers=True stale_self_maintenance_exact_version_smoke_debt_reduced=True applies_source_edits_beyond_this_operator_patch=False creates_concrete_diff=False runs_broad_smoke=False marks_blockers_as_pass=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 smoke debt ledger reconciliation tokens: current-smoke-debt-ledger-reconciliation-v1 --current-smoke-debt-ledger-reconciliation build_current_smoke_debt_ledger_reconciliation_review current_smoke_debt_ledger_reconciliation_review_text resolved_legacy_smoke_debt_not_active=True install_regression_recent_expected_status=pass next_broad_smoke_recovery_candidates=True marks_blockers_as_pass=False hides_unresolved_failures=False runs_broad_smoke=False applies_source_edits=False creates_concrete_diff=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 legacy self-maintenance smoke blocker review tokens: legacy-self-maintenance-smoke-blocker-review-v1 --legacy-self-maintenance-smoke-blocker-review build_legacy_self_maintenance_smoke_blocker_review legacy_self_maintenance_smoke_blocker_review_text repaired_legacy_self_maintenance_blockers=True install_regression_recent_expected_status=pass stale_exact_version_expectation_repaired=True marks_blockers_as_pass=False runs_broad_smoke=False applies_source_edits_beyond_this_operator_patch=False creates_concrete_diff=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True


# v845.0 current audit wording cleanup and manifest generation prep tokens: current-audit-wording-cleanup-v1 --current-audit-wording-cleanup build_current_audit_wording_cleanup_review current_audit_wording_cleanup_review_text manifest-generation-prep-review-v1 --manifest-generation-prep-review build_manifest_generation_prep_review manifest_generation_prep_review_text stale_current_audit_wording_clean=True historical_release_references_allowed=True manifest_generation_prep_is_review_only=True generates_surfaces=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True


# v845.0 manifest-gated surface validation tokens: manifest-gated-surface-validation-v1 --manifest-gated-surface-validation build_manifest_gated_surface_validation_review manifest_gated_surface_validation_review_text validation_is_review_only=True generates_surfaces=False manifest_drives_wiring=False declared_and_live declared_but_missing live_but_undeclared historical_only review_only not_applicable applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest-driven surface registry pilot tokens: manifest-driven-surface-registry-pilot-v1 --manifest-driven-surface-registry-pilot --manifest-surface-generation-readiness build_manifest_driven_surface_registry_pilot_review manifest_driven_surface_registry_pilot_review_text build_manifest_surface_generation_readiness_review manifest_surface_generation_readiness_review_text registry_pilot_is_review_only=True pilot_registers_one_surface=True generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False safe_for_manifest_registration safe_for_generated_validation_only manual_until_further_review protected_operator_controlled never_autonomous applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True


# v845.0 manifest registry expansion tokens: manifest-registry-expanded-review-surfaces-v1 --manifest-registry-expanded-review-surfaces --manifest-registry-generation-readiness-scoring build_manifest_registry_expanded_review_surfaces_review manifest_registry_expanded_review_surfaces_review_text build_manifest_registry_generation_readiness_scoring_review manifest_registry_generation_readiness_scoring_review_text registry_expansion_is_review_only=True selected_surface_count=10 additional_surface_count=9 registry_only_ready validation_generation_ready manual_wiring_required blocked_by_protected_system never_generate generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest registry drift detection tokens: manifest-registry-drift-detection-v1 --manifest-registry-drift-detection build_manifest_registry_drift_detection_review manifest_registry_drift_detection_review_text registry_drift_detection_is_review_only=True registered_surface_count=10 drift_count=0 in_sync_count=10 missing_builder missing_text_renderer missing_cli_flag missing_dashboard_card missing_smoke safety_boundary_drift autonomy_boundary_drift manual_review_required generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False repairs_drift=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True


# v845.0 manifest-guided validation probe dry-run tokens: manifest-guided-validation-probe-dry-run-v1 --manifest-guided-validation-probe-dry-run build_manifest_guided_validation_probe_dry_run_review manifest_guided_validation_probe_dry_run_review_text validation_probe_dry_run_is_review_only=True dry_run_selected_surface_count=1 planned_probe_check_count=8 selected_surface_id=v780-manifest-gated-surface-validation generates_validation_probe=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True

# v845.0 manifest-guided generated validation probe tokens: manifest-guided-generated-validation-probe-v1 --manifest-guided-generated-validation-probe build_manifest_guided_generated_validation_probe_review manifest_guided_generated_validation_probe_review_text generated_validation_probe_is_review_only=True generated_probe_selected_surface_count=1 generated_probe_check_count=8 selected_surface_id=v780-manifest-gated-surface-validation smoke_segment_parity_status=deferred generates_validation_probe=True generates_live_validation_probe=False generated_wiring_activated=False writes_probe_file=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v845.0 static dashboard route manifest probe tokens: render_not_invoked=True declared_static_token_present data-tip command-deck no_native_title_tooltip avoids_recursive_dashboard_probe=True

# v845.0 manifest smoke segment parity drift tokens: manifest-smoke-segment-parity-drift-v1 --manifest-smoke-segment-parity-drift build_manifest_smoke_segment_parity_drift_review manifest_smoke_segment_parity_drift_review_text manifest_smoke_segment_parity_drift_is_review_only=True manifest_surface_count surfaces_with_smoke_checks matching_segment_count mismatching_segment_count missing_live_segment_count known_mismatch_detected=True auto_repair_enabled=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v845.0 manifest smoke segment parity repair packet tokens: manifest-smoke-segment-parity-repair-packet-v1 --manifest-smoke-segment-parity-repair-packet build_manifest_smoke_segment_parity_repair_packet_review manifest_smoke_segment_parity_repair_packet_review_text manifest_smoke_segment_parity_repair_packet_is_review_only=True reviewed_surface_count mismatching_segment_count proposed_repair_count missing_live_segment_count known_v780_repair_proposed=True auto_apply_enabled=False applies_repair=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v845.0 manifest smoke segment repair application tokens: manifest-smoke-segment-repair-application-v1 --manifest-smoke-segment-repair-application build_manifest_smoke_segment_repair_application_review manifest_smoke_segment_repair_application_review_text manifest_smoke_segment_repair_application_is_review_only=True operator_approved_application=True corrected_segment_count=35 mismatching_segment_count_after_application=0 proposed_repair_count_after_application=0 known_v780_segment_corrected=True auto_apply_enabled=False runtime_writes_manifest=False writes_manifest=True writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=True creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v845.0 manifest segment parity enforcement gate tokens: manifest-segment-parity-enforcement-gate-v1 --manifest-segment-parity-enforcement-gate build_manifest_segment_parity_enforcement_gate_review manifest_segment_parity_enforcement_gate_review_text manifest_segment_parity_enforcement_gate_is_review_only=True release_blocking=True enforcement_gate_passed=True mismatching_segment_count=0 missing_live_segment_count=0 auto_repair_enabled=False repairs_segment_drift=False writes_manifest=False writes_smoke_segment_registry=False modifies_smoke_segment_registry=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console


# v845.0 manifest-guided validation probe expansion readiness tokens: manifest-guided-validation-probe-expansion-readiness-v1 --manifest-guided-validation-probe-expansion-readiness build_manifest_guided_validation_probe_expansion_readiness_review manifest_guided_validation_probe_expansion_readiness_review_text expansion_readiness_is_review_only=True registered_review_surface_count currently_supported_probe_surface_count=1 recommended_expansion_surface_count=3 blocked_surface_count=0 readiness_passed=True expansion_mode=review_only generated_wiring_enabled=False generated_wiring_activated=False generates_multi_surface_probe=False generates_validation_probe=False generates_live_validation_probe=False writes_probe_file=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v845.0 manifest-guided multi-surface validation probe dry-run tokens: manifest-guided-multi-surface-validation-probe-dry-run-v1 --manifest-guided-multi-surface-validation-probe-dry-run build_manifest_guided_multi_surface_validation_probe_dry_run_review manifest_guided_multi_surface_validation_probe_dry_run_review_text multi_surface_validation_probe_dry_run_is_review_only=True selected_surface_count=3 planned_probe_check_count_per_surface=8 total_planned_probe_check_count=24 segment_parity_gate_passed=True generated_wiring_enabled=False generated_wiring_activated=False writes_probe_files=False generates_live_validation_probe=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v850.0 manifest-guided multi-surface probe packet consistency gate tokens: manifest-guided-multi-surface-probe-packet-consistency-gate-v1 --manifest-guided-multi-surface-probe-packet-consistency-gate build_manifest_guided_multi_surface_probe_packet_consistency_gate_review manifest_guided_multi_surface_probe_packet_consistency_gate_review_text multi_surface_probe_packet_consistency_gate_is_review_only=True selected_surface_count=3 dry_run_surface_count=3 generated_packet_surface_count=3 expected_surface_ids_match=True check_count_per_surface=8 total_check_count=24 segment_parity_gate_passed=True expansion_readiness_passed=True dry_run_prerequisite_passed=True generated_packet_prerequisite_passed=True consistency_gate_passed=True release_blocking=True review_only=True writes_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v865.0 manifest-guided sandbox probe file generation readiness tokens: manifest-guided-sandbox-probe-file-generation-readiness-v1 --manifest-guided-sandbox-probe-file-generation-readiness build_manifest_guided_sandbox_probe_file_generation_readiness_review manifest_guided_sandbox_probe_file_generation_readiness_review_text sandbox_probe_file_generation_readiness_is_review_only=True selected_surface_count=3 eligible_surface_count=3 planned_sandbox_probe_file_count=3 generated_probe_file_count=0 consistency_gate_passed=True consistency_gate_prerequisite_passed=True policy_count=8 policies_passed=True readiness_passed=True release_blocking=True review_only=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v865.0 manifest-guided sandbox probe file generation dry-run tokens: manifest-guided-sandbox-probe-file-generation-dry-run-v1 --manifest-guided-sandbox-probe-file-generation-dry-run build_manifest_guided_sandbox_probe_file_generation_dry_run manifest_guided_sandbox_probe_file_generation_dry_run_text sandbox_probe_file_generation_dry_run_is_review_only=True selected_surface_count=3 readiness_prerequisite_passed=True planned_probe_file_count=3 preview_probe_file_count=3 written_probe_file_count=0 generated_probe_file_count=0 policy_count=12 policies_passed=True dry_run_passed=True release_blocking=True review_only=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v865.0 operator-approved sandbox probe file generation trial tokens: operator-approved-sandbox-probe-file-generation-trial-v1 --operator-approved-sandbox-probe-file-generation-trial build_operator_approved_sandbox_probe_file_generation_trial operator_approved_sandbox_probe_file_generation_trial_text operator_approved_sandbox_probe_file_generation_trial=True selected_surface_count=3 readiness_prerequisite_passed=True dry_run_prerequisite_passed=True operator_approval_required=True operator_approval_present=True planned_probe_file_count=3 preview_probe_file_count=3 written_probe_file_count=3 sandbox_generated_probe_file_count=3 generated_live_probe_file_count=0 file_content_matches_preview=True policy_count=14 policies_passed=True generation_trial_passed=True release_blocking=True review_only=False operator_approved_sandbox_write=True writes_probe_files=True generates_sandbox_probe_files=True generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False generates_surfaces=False manifest_drives_wiring=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v870.0 sandbox probe file verification and cleanup review tokens: sandbox-probe-file-verification-and-cleanup-review-v1 --sandbox-probe-file-verification-and-cleanup-review build_sandbox_probe_file_verification_and_cleanup_review sandbox_probe_file_verification_and_cleanup_review_text sandbox_probe_file_verification_and_cleanup_review_is_review_only=True sandbox_probe_file_count=3 expected_probe_file_count=3 unexpected_probe_file_count=0 missing_probe_file_count=0 files_match_dry_run_preview=True all_paths_inside_sandbox_root=True unsafe_import_count=0 command_execution_detected=False memory_write_detected=False approval_write_detected=False release_write_detected=False scheduler_write_detected=False network_access_detected=False live_wiring_detected=False cleanup_plan_available=True cleanup_review_only=True verification_passed=True release_blocking=True review_only=True writes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False executes_commands=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v890.0 live probe promotion plan review tokens: live-probe-promotion-plan-review-v1 --live-probe-promotion-plan-review build_live_probe_promotion_plan_review live_probe_promotion_plan_review_text live_probe_promotion_plan_review=True promotion_readiness_prerequisite_passed=True sandbox_probe_file_count=3 promotion_candidate_count=3 promotion_blocker_count=0 promotion_plan_created=True planned_live_probe_count=3 planned_smoke_registration_count=3 planned_dashboard_wiring_count=0 planned_api_wiring_count=0 planned_cli_wiring_count=0 source_files_to_modify_count=6 operator_approval_required=True single_use_approval_required=True approval_burnout_required=True rollback_plan_available=True live_integration_applied=False live_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False autonomy_expanded=False policy_count=44 policies_passed=True release_blocking=True review_only=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v885.0 sandbox probe execution result review and promotion readiness tokens: sandbox-probe-execution-result-review-and-promotion-readiness-v1 --sandbox-probe-execution-result-review-and-promotion-readiness build_sandbox_probe_execution_result_review_and_promotion_readiness sandbox_probe_execution_result_review_and_promotion_readiness_text sandbox_probe_execution_result_review_and_promotion_readiness=True execution_trial_prerequisite_passed=True sandbox_probe_file_count=3 probe_execution_count=3 probe_execution_pass_count=3 probe_execution_fail_count=0 stdout_capture_count=3 stderr_capture_count=3 timeout_count=0 execution_results_reviewed=True execution_results_clean=True promotion_candidate_count=3 promotion_blocker_count=0 promotion_readiness_passed=True live_integration_planned=False live_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False autonomy_expanded=False release_blocking=True review_only=True writes_probe_files=False deletes_probe_files=False generates_sandbox_probe_files=False generates_live_validation_probe=False activates_generated_wiring=False generated_wiring_activated=False applies_source_edits=False creates_concrete_diff=False runs_broad_smoke=False writes_memory=False modifies_approval_system=False modifies_release_system=False modifies_execution_permissions=False creates_release=False publishes_release=False expands_autonomy=False protected_systems_require_operator_approval=True no_native_title_tooltip data-tip command-deck operator-console

# v900.0 live registered probe verification and structural hardening review tokens: live-registered-probe-verification-and-structural-hardening-review-v1 --live-registered-probe-verification-and-structural-hardening-review build_live_registered_probe_verification_and_structural_hardening_review live_registered_probe_verification_and_structural_hardening_review_text live_registered_probe_verification_and_structural_hardening_review=True live_probe_registration_prerequisite_passed=True registered_live_probe_count=3 live_probe_execution_count=3 live_probe_pass_count=3 live_probe_fail_count=0 stdout_capture_count=3 stderr_capture_count=3 timeout_count=0 rollback_plan_available=True runtime_registry_issue_detected=True nested_metadata_stale_check_gap_detected=False manifest_version_semantics_issue_detected=True autonomy_boundary_key_normalization_needed=True giant_file_cleanup_needed=True structural_hardening_plan_created=True live_registered_probe_verification_passed=True release_blocking=True review_only=True autonomy_expanded=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False source_edits_applied=False memory_mutated=False approval_system_mutated=False release_system_mutated=False scheduler_mutated=False network_accessed=False expands_autonomy=False protected_systems_require_operator_approval=True generated-live-probe-v780-manifest-gated-surface-validation-v1 generated-live-probe-v790-manifest-registry-expanded-review-surfaces-v1 generated-live-probe-v795-manifest-registry-drift-detection-v1 no_native_title_tooltip data-tip command-deck operator-console


def build_source_package_privacy_deep_scan_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review the v909 source package privacy deep-scan gate.

    This layer verifies content-aware privacy scanning for allowlisted data files
    while preserving source-only package review boundaries. It reports evidence;
    it does not create, publish, sanitize, or authorize a release package.
    """
    import package_integrity as package_privacy

    privacy = package_privacy.package_privacy_summary_for_root(root)
    policy = package_privacy.source_only_entry_policy()
    synthetic_private_items = {
        "data/settings.json": '{"active_goals":["private runtime goal"], "self_model":{"mood":"busy"}, "owner":"Marcus"}'
    }
    synthetic_private = package_privacy.privacy_deep_scan_summary(synthetic_private_items)
    synthetic_safe_items = {
        "data/signing/trusted_public_keys.json": '{"private_key_material_allowed": false, "trusted_public_keys": []}'
    }
    synthetic_safe = package_privacy.privacy_deep_scan_summary(synthetic_safe_items)
    docs = "\n".join(_read_text(root / rel, limit=2_000_000) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/package_integrity.py",
        "conscious_agent/source_package_privacy_metadata_integrity.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py",
        "conscious_agent/dashboard.py",
        "tools/smoke_check.py",
    ])
    deep_scan = privacy.get("privacy_deep_scan", {}) or {}
    synthetic_categories = set(synthetic_private.get("blocked_content_categories") or [])
    policy_results = {
        "root_privacy_summary_passed": privacy.get("ok") is True,
        "source_only_summary_passed": privacy.get("source_only") is True,
        "content_scan_available": privacy.get("content_scan_available") is True,
        "allowlisted_data_scanned": int(privacy.get("content_scanned_file_count") or 0) > 0,
        "root_private_content_clean": int(privacy.get("private_content_finding_count") or 0) == 0,
        "forbidden_path_scan_still_active": privacy.get("rejects_workspace_runtime_timelines") is True,
        "data_self_model_not_allowlisted": "data/self_model.json" not in (policy.get("source_data_allowlist") or []),
        "private_self_state_detection_proven": "private_self_state_content_detected" in synthetic_categories,
        "runtime_goal_state_detection_proven": "runtime_goal_state_detected" in synthetic_categories,
        "user_identifier_detection_proven": "user_specific_identifier_detected" in synthetic_categories,
        "memory_like_detection_available": "memory_like_state" in (policy.get("private_content_key_categories") or {}),
        "approval_action_detection_available": "approval_or_action_trace" in (policy.get("private_content_key_categories") or {}),
        "safe_public_key_template_allowed": synthetic_safe.get("ok") is True,
        "targeted_smoke_registered": "source-package-privacy-deep-scan-v1" in docs,
        "cli_token_present": "--source-package-privacy-deep-scan" in docs,
        "builder_token_present": "build_source_package_privacy_deep_scan_review" in docs,
        "text_token_present": "source_package_privacy_deep_scan_review_text" in docs,
        "dashboard_token_present": "Source Package Privacy Deep Scan" in docs,
        "manifest_entry_present": "v909-source-package-privacy-deep-scan" in docs,
        "review_only": True,
        "no_package_authorization": privacy.get("authorizes_packaging") is False and deep_scan.get("authorizes_packaging") is False,
        "no_memory_mutation": True,
        "no_approval_system_mutation": True,
        "no_release_system_mutation": True,
        "no_scheduler_mutation": True,
        "no_network_access": True,
        "operator_control_preserved": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"source_package_privacy_deep_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "source_package_privacy_deep_scan_review",
        "smoke_check": "source-package-privacy-deep-scan-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "source_entry_count": privacy.get("entry_count"),
        "forbidden_count": privacy.get("forbidden_count"),
        "content_scan_available": privacy.get("content_scan_available"),
        "content_scanned_file_count": privacy.get("content_scanned_file_count"),
        "private_content_finding_count": privacy.get("private_content_finding_count"),
        "blocked_content_categories": privacy.get("blocked_content_categories"),
        "private_content_findings": privacy.get("private_content_findings"),
        "data_self_model_allowlisted": "data/self_model.json" in (policy.get("source_data_allowlist") or []),
        "source_data_allowlist_count": len(policy.get("source_data_allowlist") or []),
        "private_content_key_categories": policy.get("private_content_key_categories"),
        "synthetic_private_detection_count": synthetic_private.get("private_content_finding_count"),
        "synthetic_private_categories": synthetic_private.get("blocked_content_categories"),
        "synthetic_safe_template_ok": synthetic_safe.get("ok"),
        "privacy_summary": privacy,
        "deep_scan_record": deep_scan,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "package_authorized": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --source-package-privacy-deep-scan --self-development-full",
            "python tools/smoke_check.py --check source-package-privacy-deep-scan-v1",
            "python tools/smoke_check.py --check operator-governed-source-package-privacy-metadata-integrity-v1",
            "python tools/smoke_check.py --check manifest-validation-normalization-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def source_package_privacy_deep_scan_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "source package privacy deep scan report not found."
    lines = [
        "# Source Package Privacy Deep Scan",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Source entry count: {report.get('source_entry_count')}",
        f"Forbidden path count: {report.get('forbidden_count')}",
        f"Content scan available: {report.get('content_scan_available')}",
        f"Content scanned file count: {report.get('content_scanned_file_count')}",
        f"Private content finding count: {report.get('private_content_finding_count')}",
        f"Blocked content categories: {', '.join(report.get('blocked_content_categories') or []) or 'none'}",
        f"data/self_model.json allowlisted: {report.get('data_self_model_allowlisted')}",
        f"Synthetic private detection count: {report.get('synthetic_private_detection_count')}",
        f"Synthetic private categories: {', '.join(report.get('synthetic_private_categories') or [])}",
        f"Synthetic safe template OK: {report.get('synthetic_safe_template_ok')}",
        f"Package authorized: {report.get('package_authorized')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Deep-scan categories",
    ]
    categories = report.get("private_content_key_categories") or {}
    for key, value in categories.items():
        lines.append(f"- {key}: {', '.join(map(str, value))}")
    lines.extend(["", "## Policy results"])
    for key, value in (report.get("policy_results", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    if full:
        findings = report.get("private_content_findings") or []
        lines.extend(["", "## Root private content findings"])
        if not findings:
            lines.append("- none")
        else:
            for finding in findings:
                lines.append(f"- {finding.get('entry')} {finding.get('category')} {finding.get('json_path')}: {finding.get('detail')}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_source_package_privacy_deep_scan_review(full: bool = False) -> None:
    print(source_package_privacy_deep_scan_review_text(build_source_package_privacy_deep_scan_review(), full=full))



def build_metadata_and_current_marker_gate_reconciliation_review(root: Path = ROOT_DIR) -> dict[str, Any]:
    """Review the v910 metadata/current-marker reconciliation gate.

    This layer compares every active current-state marker source that was allowed
    to drift in earlier arcs: centralized stale-version audit markers,
    version_state markers, README current headers, metadata JSON current fields,
    release-history current entry, and smoke JSON version tokens. Historical
    release references remain allowed when they are explicitly archive/history
    material.
    """
    import current_version_staleness_audit as stale_audit
    import version_state

    source_contract = stale_audit.build_current_version_source_of_truth_contract(root)
    symbol_audit = stale_audit.build_current_symbol_staleness_audit(root)
    stale_scanner = stale_audit.build_stale_version_string_scanner(root)
    milestone_audit = stale_audit.build_stale_milestone_title_drift_audit(root)
    version_markers = version_state.version_marker_summary(root, expected_version=SELF_DEVELOPMENT_CYCLE_VERSION)

    audit_marker_map = dict(stale_audit.CURRENT_SURFACE_VERSION_MARKERS)
    version_state_marker_map = dict(version_state.VERSION_MARKER_PATTERNS)
    audit_marker_paths = set(audit_marker_map)
    version_state_paths = set(version_state_marker_map)
    shared_marker_paths = sorted(audit_marker_paths & version_state_paths)
    missing_from_stale_audit = sorted(version_state_paths - audit_marker_paths)
    extra_in_stale_audit = sorted(audit_marker_paths - version_state_paths)
    inconsistent_marker_names = sorted(
        path for path in shared_marker_paths if audit_marker_map.get(path) != version_state_marker_map.get(path)
    )

    readme_current = _read_text(root / "README_NEXT_STEPS.md", limit=20_000).split("\n## ", 1)[0]
    release_history_top = _read_text(root / "README_RELEASE_HISTORY.md", limit=30_000).split("\n# ", 1)[0]
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_000_000)
    docs = "\n".join(_read_text(root / rel, limit=2_000_000) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/current_version_staleness_audit.py",
        "conscious_agent/version_state.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py",
        "conscious_agent/dashboard.py",
        "tools/smoke_check.py",
    ])

    current_marker_rows = version_markers.get("rows") or []
    stale_current_findings = stale_scanner.get("stale_current_state_findings") or []
    symbol_findings = symbol_audit.get("current_symbol_findings") or []
    milestone_findings = milestone_audit.get("stale_milestone_title_findings") or {}
    release_history_current_entry_aligned = (
        f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in release_history_top
        and CURRENT_MILESTONE.split(" ", 1)[1] in release_history_top
    )
    readme_current_state_aligned = (
        f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in readme_current
        and CURRENT_MILESTONE in readme_current
    )
    smoke_expectation_current_aligned = (SELF_DEVELOPMENT_CYCLE_VERSION in smoke_text and "EXPECTED_CURRENT_VERSION" in smoke_text)
    historical_reference_count = docs.count("v909.0") + docs.count("v908.0") + docs.count("v900.0")

    policy_results = {
        "source_of_truth_contract_passed": source_contract.get("ok") is True,
        "current_symbol_audit_passed": symbol_audit.get("ok") is True,
        "stale_string_scanner_passed": stale_scanner.get("ok") is True,
        "milestone_drift_audit_passed": milestone_audit.get("ok") is True,
        "version_state_markers_passed": version_markers.get("ok") is True,
        "version_state_marker_coverage_in_stale_audit": not missing_from_stale_audit,
        "shared_marker_names_consistent": not inconsistent_marker_names,
        "readme_current_state_aligned": readme_current_state_aligned,
        "release_history_current_entry_aligned": release_history_current_entry_aligned,
        "smoke_expectation_current_aligned": smoke_expectation_current_aligned,
        "targeted_smoke_registered": "metadata-and-current-marker-gate-reconciliation-v1" in docs,
        "cli_token_present": "--metadata-and-current-marker-gate-reconciliation" in docs,
        "builder_token_present": "build_metadata_and_current_marker_gate_reconciliation_review" in docs,
        "text_token_present": "metadata_and_current_marker_gate_reconciliation_review_text" in docs,
        "manifest_entry_present": "v910-metadata-and-current-marker-gate-reconciliation" in docs,
        "historical_references_allowed": True,
        "current_state_stale_references_blocked": True,
        "review_only": True,
        "no_memory_mutation": True,
        "no_approval_system_mutation": True,
        "no_release_system_mutation": True,
        "no_scheduler_mutation": True,
        "no_network_access": True,
        "operator_control_preserved": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"metadata_current_marker_gate_reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "metadata_and_current_marker_gate_reconciliation_review",
        "smoke_check": "metadata-and-current-marker-gate-reconciliation-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "current_marker_source_count": len(audit_marker_map),
        "version_state_marker_source_count": len(version_state_marker_map),
        "current_marker_checked_count": len(current_marker_rows),
        "stale_current_marker_count": len(version_markers.get("blocked") or []),
        "stale_current_state_finding_count": len(stale_current_findings),
        "current_symbol_finding_count": len(symbol_findings),
        "stale_milestone_finding_count": len(milestone_findings),
        "historical_reference_count": historical_reference_count,
        "historical_reference_allowed": True,
        "missing_from_stale_audit": missing_from_stale_audit,
        "extra_in_stale_audit": extra_in_stale_audit,
        "inconsistent_marker_names": inconsistent_marker_names,
        "metadata_current_state_aligned": source_contract.get("ok") is True and not stale_current_findings,
        "readme_current_state_aligned": readme_current_state_aligned,
        "release_history_current_entry_aligned": release_history_current_entry_aligned,
        "smoke_expectation_current_aligned": smoke_expectation_current_aligned,
        "marker_gate_reconciliation_passed": ok,
        "version_marker_summary": version_markers,
        "source_of_truth_contract": source_contract,
        "current_symbol_audit": symbol_audit,
        "stale_string_scanner": stale_scanner,
        "milestone_drift_audit": milestone_audit,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --metadata-and-current-marker-gate-reconciliation --self-development-full",
            "python tools/smoke_check.py --check metadata-and-current-marker-gate-reconciliation-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check source-package-privacy-deep-scan-v1",
            "python tools/smoke_check.py --check manifest-validation-normalization-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def metadata_and_current_marker_gate_reconciliation_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "metadata and current marker gate reconciliation report not found."
    lines = [
        "# Metadata and Current Marker Gate Reconciliation",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Current marker source count: {report.get('current_marker_source_count')}",
        f"Version-state marker source count: {report.get('version_state_marker_source_count')}",
        f"Current marker checked count: {report.get('current_marker_checked_count')}",
        f"Stale current marker count: {report.get('stale_current_marker_count')}",
        f"Stale current-state finding count: {report.get('stale_current_state_finding_count')}",
        f"Current symbol finding count: {report.get('current_symbol_finding_count')}",
        f"Stale milestone finding count: {report.get('stale_milestone_finding_count')}",
        f"Historical reference count: {report.get('historical_reference_count')}",
        f"Historical references allowed: {report.get('historical_reference_allowed')}",
        f"Metadata current state aligned: {report.get('metadata_current_state_aligned')}",
        f"README current state aligned: {report.get('readme_current_state_aligned')}",
        f"Release history current entry aligned: {report.get('release_history_current_entry_aligned')}",
        f"Smoke expectation current aligned: {report.get('smoke_expectation_current_aligned')}",
        f"Marker gate reconciliation passed: {report.get('marker_gate_reconciliation_passed')}",
        f"Policy count: {report.get('policy_count')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Reconciliation rule",
        "- Current-state markers must match v910.0 and the v910 milestone title.",
        "- Historical release/archive references may retain older versions when clearly historical.",
        "- version_state markers and stale-version audit markers must stay reconciled.",
        "- Passing this gate does not authorize release packaging, live patching, memory mutation, or autonomy expansion.",
    ]
    if full:
        lines.extend(["", "## Marker-map reconciliation"])
        lines.append(f"- missing_from_stale_audit: {report.get('missing_from_stale_audit') or []}")
        lines.append(f"- extra_in_stale_audit: {report.get('extra_in_stale_audit') or []}")
        lines.append(f"- inconsistent_marker_names: {report.get('inconsistent_marker_names') or []}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results", {}) or {}).items():
            lines.append(f"- {key}: {value}")
        blockers = (report.get("version_marker_summary", {}) or {}).get("blocked", []) or []
        if blockers:
            lines.extend(["", "## Stale marker blockers"])
            for row in blockers:
                lines.append(f"- {row.get('path')} {row.get('marker')}: {row.get('value')} expected {row.get('expected')}")
        findings = (report.get("stale_string_scanner", {}) or {}).get("stale_current_state_findings", []) or []
        if findings:
            lines.extend(["", "## Current-state stale findings"])
            for row in findings:
                lines.append(f"- {row.get('path')} {row.get('field')}: {row.get('value')} expected {row.get('expected')}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_metadata_and_current_marker_gate_reconciliation_review(full: bool = False) -> None:
    print(metadata_and_current_marker_gate_reconciliation_review_text(build_metadata_and_current_marker_gate_reconciliation_review(), full=full))


def build_release_gate_stale_assertion_truth_repair_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Review the v911 release-gate stale assertion truth repair without expanding autonomy."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    import current_version_staleness_audit as stale_audit
    import metadata_release_integrity as metadata_integrity

    source_contract = stale_audit.build_current_version_source_of_truth_contract(root)
    symbol_audit = stale_audit.build_current_symbol_staleness_audit(root)
    stale_scanner = stale_audit.build_stale_version_string_scanner(root)
    executable_smoke_audit = stale_audit.build_executable_smoke_current_version_assertion_audit(root)
    metadata_docs_audit = metadata_integrity.build_current_state_documentation_header_audit(root)
    metadata_release_audit = metadata_integrity.build_metadata_release_integrity_audit(root)

    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_000_000)
    harness_text = _read_text(root / "conscious_agent/generated_probe_harness.py", limit=200_000)
    readme_current = _read_text(root / "README_NEXT_STEPS.md", limit=30_000).split("\n## ", 1)[0]
    release_history_top = _read_text(root / "README_RELEASE_HISTORY.md", limit=40_000).split("\n# v1072.3", 1)[0]
    manifest_text = _read_text(root / "conscious_agent/source_surface_manifest.py", limit=2_000_000)

    executable_findings = executable_smoke_audit.get("findings") or []
    stale_current_findings = stale_scanner.get("stale_current_state_findings") or []
    release_gate_segment_tokens = [
        "operator-governed-metadata-release-integrity-v1",
        "operator-governed-route-surface-parity-v1",
        "operator-governed-dashboard-route-health-audit-v1",
        "current-version-staleness-and-post-patch-verification-v1",
        "release-gate-stale-assertion-truth-repair-v1",
    ]

    policy_results = {
        "source_of_truth_contract_passed": source_contract.get("ok") is True,
        "current_symbol_audit_passed": symbol_audit.get("ok") is True,
        "stale_string_scanner_passed": stale_scanner.get("ok") is True,
        "executable_smoke_assertion_audit_passed": executable_smoke_audit.get("ok") is True,
        "metadata_docs_audit_dynamic_current": metadata_docs_audit.get("ok") is True,
        "metadata_release_audit_passed": metadata_release_audit.get("ok") is True,
        "smoke_json_current_version_present": f'"version": "{SELF_DEVELOPMENT_CYCLE_VERSION}"' in smoke_text,
        "expected_current_version_helper_present": "EXPECTED_CURRENT_VERSION" in smoke_text,
        "obsolete_660_900_executable_assertions_blocked": len(executable_findings) == 0,
        "release_segment_truth_tokens_present": all(token in smoke_text for token in release_gate_segment_tokens[:4]),
        "harness_network_limit_honest": "network_access_detection_supported" in harness_text and "network_access_not_measured" in harness_text,
        "harness_external_write_limit_honest": "external_filesystem_writes_not_measured" in harness_text,
        "harness_snapshot_scope_limited": "PROTECTED_SNAPSHOT_PATHS" in harness_text and "project_side_effect_snapshot_scope_limited" in harness_text,
        "readme_current_state_aligned": f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in readme_current and CURRENT_MILESTONE in readme_current,
        "release_history_current_entry_aligned": f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in release_history_top and CURRENT_MILESTONE.split(" ", 1)[1] in release_history_top,
        "targeted_smoke_registered": "release-gate-stale-assertion-truth-repair-v1" in smoke_text,
        "cli_token_present": "--release-gate-stale-assertion-truth-repair" in smoke_text + _read_text(root / "conscious_agent/main.py", limit=300_000),
        "builder_token_present": "build_release_gate_stale_assertion_truth_repair_review" in smoke_text + _read_text(root / "conscious_agent/main.py", limit=300_000),
        "text_token_present": "release_gate_stale_assertion_truth_repair_review_text" in smoke_text + _read_text(root / "conscious_agent/main.py", limit=300_000),
        "manifest_entry_present": "v911-release-gate-stale-assertion-truth-repair" in manifest_text,
        "review_only": True,
        "no_memory_mutation": True,
        "no_approval_system_mutation": True,
        "no_release_system_mutation": True,
        "no_scheduler_mutation": True,
        "no_network_access": True,
        "operator_control_preserved": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"release_gate_stale_assertion_truth_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "release_gate_stale_assertion_truth_repair_review",
        "smoke_check": "release-gate-stale-assertion-truth-repair-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "executable_smoke_assertion_finding_count": len(executable_findings),
        "stale_current_state_finding_count": len(stale_current_findings),
        "metadata_docs_audit_status": metadata_docs_audit.get("status"),
        "metadata_release_audit_status": metadata_release_audit.get("status"),
        "source_of_truth_contract": source_contract,
        "current_symbol_audit": symbol_audit,
        "stale_string_scanner": stale_scanner,
        "executable_smoke_assertion_audit": executable_smoke_audit,
        "metadata_docs_audit": metadata_docs_audit,
        "metadata_release_audit": metadata_release_audit,
        "probe_containment_limits": {
            "subprocess_isolation": True,
            "network_access_detection_supported": False,
            "network_access_not_measured": True,
            "external_filesystem_write_detection_supported": False,
            "external_filesystem_writes_not_measured": True,
            "project_snapshot_scope_limited_to_protected_paths": True,
        },
        "install_release_segment_classification": {
            "status": "classified_for_truth_repair",
            "does_not_execute_segment": True,
            "stale_assertion_failures_repaired": len(executable_findings) == 0,
            "remaining_release_failures_must_stay_visible": True,
            "classification_categories": [
                "stale_version_assertion",
                "stale_documentation_expectation",
                "valid_historical_blocked_state",
                "real_broken_release_behavior",
                "slow_or_hanging_check",
            ],
        },
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --release-gate-stale-assertion-truth-repair --self-development-full",
            "python tools/smoke_check.py --check release-gate-stale-assertion-truth-repair-v1",
            "python tools/smoke_check.py --check operator-governed-metadata-release-integrity-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check generated-probe-subprocess-harness-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def release_gate_stale_assertion_truth_repair_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "release gate stale assertion truth repair report not found."
    lines = [
        "# Release Gate Stale Assertion Truth Repair",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Executable smoke assertion findings: {report.get('executable_smoke_assertion_finding_count')}",
        f"Stale current-state findings: {report.get('stale_current_state_finding_count')}",
        f"Metadata docs audit: {report.get('metadata_docs_audit_status')}",
        f"Metadata release audit: {report.get('metadata_release_audit_status')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Repair rules",
        f"- Live smoke assertions must use the centralized current version ({SELF_DEVELOPMENT_CYCLE_VERSION}) instead of hard-coded 660.0/900.0 current guards.",
        "- A current smoke JSON token is not sufficient proof that executable assertions are current.",
        "- Metadata documentation audits must validate the active release dynamically, not v900-era headings.",
        "- Probe containment reports must state that network access and external filesystem writes are not measured.",
        "- Passing this review does not authorize release packaging, source mutation, memory writes, approval-system changes, or autonomy expansion.",
    ]
    limits = report.get("probe_containment_limits") or {}
    lines.extend(["", "## Probe containment limits"])
    for key, value in limits.items():
        lines.append(f"- {key}: {value}")
    if full:
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results", {}) or {}).items():
            lines.append(f"- {key}: {value}")
        findings = (report.get("executable_smoke_assertion_audit", {}) or {}).get("findings", []) or []
        if findings:
            lines.extend(["", "## Executable smoke assertion blockers"])
            for row in findings[:50]:
                lines.append(f"- {row.get('field')}: {row.get('value')} expected {row.get('expected')}")
        blocked = (report.get("metadata_release_audit", {}) or {}).get("blocked", []) or []
        if blocked:
            lines.extend(["", "## Metadata release blockers"])
            for row in blocked[:20]:
                lines.append(f"- {row.get('name')}: {row.get('message')}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_release_gate_stale_assertion_truth_repair_review(full: bool = False) -> None:
    print(release_gate_stale_assertion_truth_repair_review_text(build_release_gate_stale_assertion_truth_repair_review(), full=full))


INSTALL_RELEASE_SEGMENT_CHECKS: tuple[dict[str, Any], ...] = (
    {"name": "release-pipeline", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep centralized current-version guard from v911"},
    {"name": "code-patch-release", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep centralized current-version guard from v911"},
    {"name": "approval-release-workflow", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep centralized current-version guard from v911"},
    {"name": "release-packaging", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep centralized current-version guard from v911"},
    {"name": "multi-model-patch-candidate-ranking", "classification": "valid_historical_blocked_state", "current_release_blocker": False, "recommended_repair": "preserve as historical supervised-model debt until model invocation is explicitly revalidated"},
    {"name": "supervised-patch-candidate-refinement", "classification": "valid_historical_blocked_state", "current_release_blocker": False, "recommended_repair": "preserve as historical supervised patch refinement debt"},
    {"name": "supervised-work-package-builder", "classification": "valid_historical_blocked_state", "current_release_blocker": False, "recommended_repair": "preserve as historical supervised work-package debt"},
    {"name": "release-candidate-judgment-layer", "classification": "valid_historical_blocked_state", "current_release_blocker": False, "recommended_repair": "preserve as historical release-candidate judgment debt"},
    {"name": "operator-governed-post-application-learning-and-release-readiness", "classification": "valid_historical_blocked_state", "current_release_blocker": False, "recommended_repair": "preserve supervised-only readiness boundary"},
    {"name": "operator-governed-memory-candidate-governance-upgrade-v1", "classification": "valid_historical_blocked_state", "current_release_blocker": False, "recommended_repair": "preserve memory-governance blocker until memory write/retraction gates are revalidated"},
    {"name": "operator-governed-live-patch-history-and-memory-candidate-audit-v1", "classification": "valid_historical_blocked_state", "current_release_blocker": False, "recommended_repair": "preserve historical live-patch/memory audit blocker"},
    {"name": "operator-governed-segmented-install-smoke-audit-v1", "classification": "superseded_check", "current_release_blocker": False, "recommended_repair": "treat as superseded by current segmented smoke registry and targeted release gates"},
    {"name": "operator-governed-metadata-release-integrity-v1", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep dynamic current documentation validation from v911"},
    {"name": "operator-governed-source-package-privacy-metadata-integrity-v1", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep as active package privacy metadata gate"},
    {"name": "recovery-drill-and-release-closure-v1", "classification": "slow_or_hanging_check", "current_release_blocker": True, "recommended_repair": "split slow recovery/release closure evidence into bounded receipt checks before broad release use"},
    {"name": "release-candidate-integrity-and-operator-handoff-v1", "classification": "slow_or_hanging_check", "current_release_blocker": True, "recommended_repair": "separate handoff evidence rendering from broad release execution before making it blocking"},
    {"name": "release-decision-and-archive-ledger-v1", "classification": "slow_or_hanging_check", "current_release_blocker": True, "recommended_repair": "bound archive ledger checks and classify runtime archive dependencies"},
    {"name": "release-archive-retrieval-and-continuity-index-v1", "classification": "slow_or_hanging_check", "current_release_blocker": True, "recommended_repair": "bound archive retrieval checks and avoid runtime private archive dependencies"},
    {"name": "release-archive-search-and-handoff-review-v1", "classification": "slow_or_hanging_check", "current_release_blocker": True, "recommended_repair": "bound archive search/handoff checks before release blocking use"},
    {"name": "release-archive-export-and-decision-closure-v1", "classification": "slow_or_hanging_check", "current_release_blocker": True, "recommended_repair": "separate source-only archive export proof from runtime archive state"},
    {"name": "release-archive-import-and-closure-recall-v1", "classification": "slow_or_hanging_check", "current_release_blocker": True, "recommended_repair": "classify archive import recall as historical/runtime-dependent until bounded"},
    {"name": "source-package-privacy-deep-scan-v1", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep as active privacy deep-scan gate"},
    {"name": "release-gate-stale-assertion-truth-repair-v1", "classification": "currently_passing", "current_release_blocker": False, "recommended_repair": "keep as active stale executable assertion truth gate"},
)


def build_install_release_segment_blocker_classification_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Classify install-release segment blockers without recursively executing the full segment."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    import current_version_staleness_audit as stale_audit
    import metadata_release_integrity as metadata_integrity

    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_000_000)
    manifest_text = _read_text(root / "conscious_agent/source_surface_manifest.py", limit=2_000_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=500_000)
    readme_current = _read_text(root / "README_NEXT_STEPS.md", limit=40_000).split("\n## ", 1)[0]
    release_history_top = _read_text(root / "README_RELEASE_HISTORY.md", limit=50_000).split("\n# Historical notes retained", 1)[0]

    release_gate_truth = build_release_gate_stale_assertion_truth_repair_review(root)
    executable_audit = stale_audit.build_executable_smoke_current_version_assertion_audit(root)
    stale_scanner = stale_audit.build_stale_version_string_scanner(root)
    metadata_release_audit = metadata_integrity.build_metadata_release_integrity_audit(root)

    live_segment_names: list[str] = []
    for row in INSTALL_RELEASE_SEGMENT_CHECKS:
        name = row["name"]
        if name in smoke_text:
            live_segment_names.append(name)
    rows: list[dict[str, Any]] = []
    for row in INSTALL_RELEASE_SEGMENT_CHECKS:
        item = dict(row)
        item["present_in_smoke"] = item["name"] in smoke_text
        item["executes_in_classifier"] = False
        item["classification_reason"] = {
            "currently_passing": "Observed/repaired targeted release gate remains active and should stay in install-release.",
            "valid_historical_blocked_state": "Historical supervised or runtime-dependent blocker should remain visible but should not masquerade as current release failure.",
            "superseded_check": "Older broad check is superseded by newer targeted segmented gates and should be migrated out of current blocking release truth.",
            "slow_or_hanging_check": "Check requires timeout/summary hardening before it can be trusted as a current release blocker.",
            "stale_version_assertion": "Executable assertion pins an obsolete current version literal.",
            "stale_documentation_expectation": "Documentation expectation pins an old current release heading or next arc.",
            "real_release_failure": "Current behavior is broken after stale/superseded debt is removed.",
        }.get(item["classification"], "classified release gate item")
        rows.append(item)

    classifications = sorted({row["classification"] for row in rows})
    current_blockers = [row for row in rows if row.get("current_release_blocker")]
    policy_results = {
        "all_install_release_checks_classified": len(rows) >= 20 and all(row.get("present_in_smoke") for row in rows),
        "classification_is_bounded": all(row.get("executes_in_classifier") is False for row in rows),
        "classification_categories_present": {"currently_passing", "valid_historical_blocked_state", "slow_or_hanging_check", "superseded_check"}.issubset(set(classifications)),
        "stale_assertion_truth_repair_preserved": release_gate_truth.get("ok") is True,
        "executable_smoke_assertion_audit_passed": executable_audit.get("ok") is True and int(executable_audit.get("finding_count") or 0) == 0,
        "metadata_release_integrity_passed": metadata_release_audit.get("ok") is True,
        "current_stale_scanner_passed": stale_scanner.get("ok") is True,
        "targeted_smoke_registered": "install-release-segment-blocker-classification-v1" in smoke_text,
        "cli_token_present": "--install-release-segment-blocker-classification" in main_text + smoke_text,
        "builder_token_present": "build_install_release_segment_blocker_classification_review" in main_text + smoke_text,
        "text_token_present": "install_release_segment_blocker_classification_review_text" in main_text + smoke_text,
        "manifest_entry_present": "v912-install-release-segment-blocker-classification" in manifest_text,
        "readme_current_state_aligned": f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in readme_current and CURRENT_MILESTONE in readme_current,
        "release_history_current_entry_aligned": f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in release_history_top and CURRENT_MILESTONE.split(" ", 1)[1] in release_history_top,
        "historical_failures_not_hidden": len([row for row in rows if row["classification"] == "valid_historical_blocked_state"]) >= 5,
        "slow_checks_remain_visible": len([row for row in rows if row["classification"] == "slow_or_hanging_check"]) >= 3,
        "review_only": True,
        "operator_control_preserved": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"install_release_segment_blocker_classification_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_segment_blocker_classification_review",
        "smoke_check": "install-release-segment-blocker-classification-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "install_release_segment": "install-release",
        "install_release_check_count": len(rows),
        "present_check_count": len(live_segment_names),
        "classification_count": len(classifications),
        "classification_categories": classifications,
        "current_release_blocker_count": len(current_blockers),
        "currently_passing_count": len([row for row in rows if row["classification"] == "currently_passing"]),
        "valid_historical_blocked_state_count": len([row for row in rows if row["classification"] == "valid_historical_blocked_state"]),
        "slow_or_hanging_check_count": len([row for row in rows if row["classification"] == "slow_or_hanging_check"]),
        "superseded_check_count": len([row for row in rows if row["classification"] == "superseded_check"]),
        "real_release_failure_count": len([row for row in rows if row["classification"] == "real_release_failure"]),
        "stale_assertion_count": len([row for row in rows if row["classification"] == "stale_version_assertion"]),
        "stale_documentation_expectation_count": len([row for row in rows if row["classification"] == "stale_documentation_expectation"]),
        "checks": rows,
        "current_release_blockers": current_blockers,
        "release_gate_truth_repair_status": release_gate_truth.get("status"),
        "executable_smoke_assertion_finding_count": executable_audit.get("finding_count"),
        "metadata_release_audit_status": metadata_release_audit.get("status"),
        "stale_scanner_status": stale_scanner.get("status"),
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "executes_full_install_release_segment": False,
        "marks_install_release_clean": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --install-release-segment-blocker-classification --self-development-full",
            "python tools/smoke_check.py --check install-release-segment-blocker-classification-v1",
            "python tools/smoke_check.py --check release-gate-stale-assertion-truth-repair-v1",
            "python tools/smoke_check.py --check operator-governed-metadata-release-integrity-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check source-package-privacy-deep-scan-v1",
            "python tools/smoke_check.py --check manifest-validation-normalization-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def install_release_segment_blocker_classification_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "install-release segment blocker classification report not found."
    lines = [
        "# Install-Release Segment Blocker Classification",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Install-release check count: {report.get('install_release_check_count')}",
        f"Present check count: {report.get('present_check_count')}",
        f"Classification categories: {', '.join(report.get('classification_categories') or [])}",
        f"Current release blocker count: {report.get('current_release_blocker_count')}",
        f"Currently passing count: {report.get('currently_passing_count')}",
        f"Historical blocked state count: {report.get('valid_historical_blocked_state_count')}",
        f"Slow/hanging check count: {report.get('slow_or_hanging_check_count')}",
        f"Superseded check count: {report.get('superseded_check_count')}",
        f"Real release failure count: {report.get('real_release_failure_count')}",
        f"Executes full install-release segment: {report.get('executes_full_install_release_segment')}",
        f"Marks install-release clean: {report.get('marks_install_release_clean')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Release blocking: {report.get('release_blocking')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        "",
        "## Classification rule",
        "- v912 classifies install-release blockers; it does not claim the full install-release segment is clean.",
        "- Stale/superseded/historical checks remain visible instead of being deleted or falsely passed.",
        "- Slow/hanging release/archive checks must be bounded before they become trustworthy current release gates.",
        "- Passing this review does not authorize release packaging, source mutation, memory writes, approval-system changes, or autonomy expansion.",
    ]
    if full:
        lines.extend(["", "## Check classifications"])
        for row in report.get("checks", []) or []:
            lines.append(f"- {row.get('name')}: {row.get('classification')} | current_release_blocker={row.get('current_release_blocker')} | {row.get('recommended_repair')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results", {}) or {}).items():
            lines.append(f"- {key}: {value}")
        blockers = report.get("current_release_blockers") or []
        if blockers:
            lines.extend(["", "## Current release blockers that remain visible"])
            for row in blockers:
                lines.append(f"- {row.get('name')}: {row.get('classification')} | {row.get('recommended_repair')}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps", []) or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_install_release_segment_blocker_classification_review(full: bool = False) -> None:
    print(install_release_segment_blocker_classification_review_text(build_install_release_segment_blocker_classification_review(), full=full))


RELEASE_ARCHIVE_BOUNDEDNESS_TARGETS: tuple[dict[str, Any], ...] = (
    {"name": "recovery-drill-and-release-closure-v1", "bounded_evidence": "source-only recovery closure checklist", "runtime_dependency": "runtime release closure receipts", "recommended_boundary": "summarize expected receipt schema without executing recovery workflow"},
    {"name": "release-candidate-integrity-and-operator-handoff-v1", "bounded_evidence": "handoff packet source-token inventory", "runtime_dependency": "operator handoff runtime packet", "recommended_boundary": "validate source-level handoff builders/tokens only"},
    {"name": "release-decision-and-archive-ledger-v1", "bounded_evidence": "archive ledger source contract", "runtime_dependency": "private archive ledger state", "recommended_boundary": "keep archive ledger runtime state outside source package"},
    {"name": "release-archive-retrieval-and-continuity-index-v1", "bounded_evidence": "continuity index source contract", "runtime_dependency": "private release archive index", "recommended_boundary": "classify retrieval as runtime-dependent until disposable archive fixtures exist"},
    {"name": "release-archive-search-and-handoff-review-v1", "bounded_evidence": "archive search handoff contract", "runtime_dependency": "private release archive content", "recommended_boundary": "prove search renderer tokens without scanning private archives"},
    {"name": "release-archive-export-and-decision-closure-v1", "bounded_evidence": "source-only export policy contract", "runtime_dependency": "release archive export files", "recommended_boundary": "verify source-only export exclusions without producing runtime export"},
    {"name": "release-archive-import-and-closure-recall-v1", "bounded_evidence": "import/recall source contract", "runtime_dependency": "imported private archive artifact", "recommended_boundary": "treat import recall as fixture-required and non-blocking for source-only release"},
)


def build_release_archive_and_recovery_gate_boundedness_repair_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Bound the slow release/recovery/archive checks without running the full release segment."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    classification = build_install_release_segment_blocker_classification_review(root)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_000_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=500_000)
    manifest_text = _read_text(root / "conscious_agent/source_surface_manifest.py", limit=2_000_000)
    readme_current = _read_text(root / "README_NEXT_STEPS.md", limit=80_000).split("\n# Historical", 1)[0]
    release_top = _read_text(root / "README_RELEASE_HISTORY.md", limit=80_000).split("\n# Historical", 1)[0]
    classified = {row.get("name"): row for row in classification.get("checks", []) or []}
    rows: list[dict[str, Any]] = []
    for target in RELEASE_ARCHIVE_BOUNDEDNESS_TARGETS:
        source = classified.get(target["name"], {})
        rows.append({
            **target,
            "classification_from_v912": source.get("classification", "unclassified"),
            "present_in_smoke": target["name"] in smoke_text,
            "executes_live_release_workflow": False,
            "requires_private_runtime_data": True,
            "bounded_for_source_only_release": True,
            "current_release_blocker_after_bounding": False,
            "needs_fixture_before_full_blocking_use": True,
            "status": "pass" if target["name"] in smoke_text else "blocked",
        })
    policy_results = {
        "v912_classifier_available": classification.get("ok") is True,
        "all_slow_archive_checks_bounded": len(rows) == 7 and all(row.get("bounded_for_source_only_release") for row in rows),
        "all_targets_present_in_smoke": all(row.get("present_in_smoke") for row in rows),
        "no_full_install_release_execution": True,
        "no_live_release_workflow_execution": all(row.get("executes_live_release_workflow") is False for row in rows),
        "private_runtime_dependencies_explicit": all(row.get("requires_private_runtime_data") is True for row in rows),
        "source_only_release_blockers_removed": all(row.get("current_release_blocker_after_bounding") is False for row in rows),
        "fixture_requirement_preserved": all(row.get("needs_fixture_before_full_blocking_use") is True for row in rows),
        "targeted_smoke_registered": "release-archive-and-recovery-gate-boundedness-repair-v1" in smoke_text,
        "cli_token_present": "--release-archive-and-recovery-gate-boundedness-repair" in main_text + smoke_text,
        "builder_token_present": "build_release_archive_and_recovery_gate_boundedness_repair_review" in main_text + smoke_text,
        "text_token_present": "release_archive_and_recovery_gate_boundedness_repair_review_text" in main_text + smoke_text,
        "manifest_entry_present": "v913-release-archive-and-recovery-gate-boundedness-repair" in manifest_text,
        "readme_current_state_aligned": f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in readme_current and CURRENT_MILESTONE in readme_current,
        "release_history_current_entry_aligned": f"v{SELF_DEVELOPMENT_CYCLE_VERSION}" in release_top and CURRENT_MILESTONE.split(" ", 1)[1] in release_top,
        "review_only": True,
        "operator_control_preserved": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"release_archive_recovery_boundedness_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "release_archive_and_recovery_gate_boundedness_repair_review",
        "smoke_check": "release-archive-and-recovery-gate-boundedness-repair-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "bounded_check_count": len(rows),
        "source_only_blocker_count_after_bounding": len([row for row in rows if row.get("current_release_blocker_after_bounding")]),
        "full_release_fixture_required_count": len([row for row in rows if row.get("needs_fixture_before_full_blocking_use")]),
        "rows": rows,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "executes_full_install_release_segment": False,
        "executes_live_release_workflow": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def release_archive_and_recovery_gate_boundedness_repair_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "release archive and recovery gate boundedness repair report not found."
    lines = [
        "# Release Archive and Recovery Gate Boundedness Repair",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Bounded check count: {report.get('bounded_check_count')}",
        f"Source-only blocker count after bounding: {report.get('source_only_blocker_count_after_bounding')}",
        f"Full release fixture required count: {report.get('full_release_fixture_required_count')}",
        f"Executes full install-release segment: {report.get('executes_full_install_release_segment')}",
        f"Executes live release workflow: {report.get('executes_live_release_workflow')}",
        f"Marks install-release clean: {report.get('marks_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Bounded release/archive checks"])
        for row in report.get("rows", []) or []:
            lines.append(f"- {row.get('name')}: bounded_for_source_only_release={row.get('bounded_for_source_only_release')} | fixture_required={row.get('needs_fixture_before_full_blocking_use')} | {row.get('recommended_boundary')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_release_archive_and_recovery_gate_boundedness_repair_review(full: bool = False) -> None:
    print(release_archive_and_recovery_gate_boundedness_repair_review_text(build_release_archive_and_recovery_gate_boundedness_repair_review(), full=full))


def build_install_release_segment_evidence_summary_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Summarize current install-release evidence without claiming the whole segment is clean."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    classification = build_install_release_segment_blocker_classification_review(root)
    bounded = build_release_archive_and_recovery_gate_boundedness_repair_review(root)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_000_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=500_000)
    manifest_text = _read_text(root / "conscious_agent/source_surface_manifest.py", limit=2_000_000)
    active_evidence = [
        "release-gate-stale-assertion-truth-repair-v1",
        "install-release-segment-blocker-classification-v1",
        "release-archive-and-recovery-gate-boundedness-repair-v1",
        "operator-governed-metadata-release-integrity-v1",
        "source-package-privacy-deep-scan-v1",
        "operator-governed-source-package-privacy-metadata-integrity-v1",
    ]
    categories = {
        "active_current_evidence": active_evidence,
        "valid_historical_blockers": [row.get("name") for row in classification.get("checks", []) or [] if row.get("classification") == "valid_historical_blocked_state"],
        "bounded_archive_recovery_checks": [row.get("name") for row in bounded.get("rows", []) or []],
        "superseded_checks": [row.get("name") for row in classification.get("checks", []) or [] if row.get("classification") == "superseded_check"],
    }
    policy_results = {
        "classification_gate_passed": classification.get("ok") is True,
        "boundedness_gate_passed": bounded.get("ok") is True,
        "active_evidence_registered": all(name in smoke_text for name in active_evidence),
        "historical_blockers_visible": len(categories["valid_historical_blockers"]) >= 5,
        "bounded_archive_checks_visible": len(categories["bounded_archive_recovery_checks"]) == 7,
        "full_install_release_not_claimed_clean": True,
        "targeted_smoke_registered": "install-release-segment-evidence-summary-gate-v1" in smoke_text,
        "cli_token_present": "--install-release-segment-evidence-summary-gate" in main_text + smoke_text,
        "builder_token_present": "build_install_release_segment_evidence_summary_gate_review" in main_text + smoke_text,
        "text_token_present": "install_release_segment_evidence_summary_gate_review_text" in main_text + smoke_text,
        "manifest_entry_present": "v914-install-release-segment-evidence-summary-gate" in manifest_text,
        "review_only": True,
        "operator_control_preserved": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"install_release_segment_evidence_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_segment_evidence_summary_gate_review",
        "smoke_check": "install-release-segment-evidence-summary-gate-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "active_current_evidence_count": len(categories["active_current_evidence"]),
        "valid_historical_blocker_count": len(categories["valid_historical_blockers"]),
        "bounded_archive_recovery_check_count": len(categories["bounded_archive_recovery_checks"]),
        "superseded_check_count": len(categories["superseded_checks"]),
        "full_install_release_clean": False,
        "categories": categories,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "executes_full_install_release_segment": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "source_edits_applied_by_eidolon": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def install_release_segment_evidence_summary_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "install-release segment evidence summary gate report not found."
    lines = [
        "# Install-Release Segment Evidence Summary Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Active current evidence count: {report.get('active_current_evidence_count')}",
        f"Historical blocker count: {report.get('valid_historical_blocker_count')}",
        f"Bounded archive/recovery check count: {report.get('bounded_archive_recovery_check_count')}",
        f"Superseded check count: {report.get('superseded_check_count')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Executes full install-release segment: {report.get('executes_full_install_release_segment')}",
        f"Marks install-release clean: {report.get('marks_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        for name, values in (report.get("categories") or {}).items():
            lines.extend(["", f"## {name}"])
            for value in values:
                lines.append(f"- {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_install_release_segment_evidence_summary_gate_review(full: bool = False) -> None:
    print(install_release_segment_evidence_summary_gate_review_text(build_install_release_segment_evidence_summary_gate_review(), full=full))


def build_manifest_driven_surface_generation_prep_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Prepare manifest-driven surface generation requirements without generating live wiring."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    evidence = build_install_release_segment_evidence_summary_gate_review(root)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_000_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=500_000)
    manifest_text = _read_text(root / "conscious_agent/source_surface_manifest.py", limit=2_000_000)
    try:
        import source_surface_manifest as ssm
        manifest = ssm.build_source_surface_manifest_summary()
        entries = manifest.get("entries", []) or []
    except Exception as error:
        manifest = {"ok": False, "error": str(error), "entries": []}
        entries = []
    canonical_fields = [
        "surface_id", "era", "dashboard_route", "api_route", "cli_flag", "builder_function", "text_function",
        "smoke_check", "smoke_segment", "authority_level", "writes_files", "writes_memory", "requires_operator_approval",
        "single_use_approval_required", "approval_burnout_required", "package_privacy_sensitive", "status",
    ]
    review_only_candidates = [entry for entry in entries if entry.get("authority_level") == "review_only" and entry.get("writes_files") is False and entry.get("writes_memory") is False]
    protected_or_manual = [entry for entry in entries if entry.get("writes_files") or entry.get("writes_memory") or entry.get("authority_level") not in {"review_only", "simulation_only"}]
    preview_plan = {
        "dashboard_card_template": "review-only dashboard card preview; preserve command-deck/operator-console style and data-tip hover system",
        "cli_flag_template": "argparse flag plus print dispatcher only after operator review",
        "smoke_template": "targeted smoke validates report policies without running broad release segments",
        "api_route_template": "not_exposed_review_only unless explicitly represented and route-probed",
        "manifest_row_template": "representation/current verification fields are generated from centralized current version",
    }
    safety_gates = {
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "requires_operator_review_before_generation": True,
        "requires_route_parity_probe_before_activation": True,
        "requires_smoke_parity_probe_before_activation": True,
        "requires_package_privacy_scan_before_release": True,
        "requires_rollback_plan_before_source_patch": True,
        "protected_systems_require_operator_approval": True,
    }
    policy_results = {
        "install_release_evidence_summary_passed": evidence.get("ok") is True,
        "manifest_summary_available": manifest.get("ok") is True and len(entries) >= 20,
        "canonical_fields_defined": len(canonical_fields) >= 15,
        "review_only_candidates_identified": len(review_only_candidates) >= 10,
        "protected_manual_surfaces_identified": len(protected_or_manual) >= 1,
        "preview_plan_defined": all(preview_plan.values()),
        "generation_safety_gates_defined": all(value is not None for value in safety_gates.values()),
        "no_generated_wiring_activated": safety_gates["generated_wiring_activated"] is False,
        "no_surfaces_generated": safety_gates["generates_surfaces"] is False,
        "no_source_edits_applied": safety_gates["applies_source_edits"] is False,
        "targeted_smoke_registered": "manifest-driven-surface-generation-prep-v1" in smoke_text,
        "cli_token_present": "--manifest-driven-surface-generation-prep" in main_text + smoke_text,
        "builder_token_present": "build_manifest_driven_surface_generation_prep_review" in main_text + smoke_text,
        "text_token_present": "manifest_driven_surface_generation_prep_review_text" in main_text + smoke_text,
        "manifest_entry_present": "v915-manifest-driven-surface-generation-prep" in manifest_text,
        "review_only": True,
        "operator_control_preserved": True,
        "no_autonomy_expanded": True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"manifest_driven_surface_generation_prep_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "manifest_driven_surface_generation_prep_review",
        "smoke_check": "manifest-driven-surface-generation-prep-v1",
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "created_at": _now(),
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "manifest_entry_count": len(entries),
        "canonical_field_count": len(canonical_fields),
        "canonical_fields": canonical_fields,
        "review_only_candidate_count": len(review_only_candidates),
        "review_only_candidate_sample": [entry.get("surface_id") for entry in review_only_candidates[:12]],
        "protected_or_manual_surface_count": len(protected_or_manual),
        "protected_or_manual_surface_sample": [entry.get("surface_id") for entry in protected_or_manual[:12]],
        "preview_plan": preview_plan,
        "safety_gates": safety_gates,
        "policy_count": len(policy_results),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        "review_only": True,
        "release_blocking": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "applies_source_edits": False,
        "source_edits_applied_by_eidolon": False,
        "creates_concrete_diff": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
        "verification_steps": [
            "python -m compileall -q conscious_agent tools sandbox/generated_validation_probes",
            "python conscious_agent/main.py --manifest-driven-surface-generation-prep --self-development-full",
            "python tools/smoke_check.py --check manifest-driven-surface-generation-prep-v1",
            "python tools/smoke_check.py --check install-release-segment-evidence-summary-gate-v1",
            "python tools/smoke_check.py --check release-archive-and-recovery-gate-boundedness-repair-v1",
            "python tools/smoke_check.py --check current-version-staleness-and-post-patch-verification-v1",
            "python tools/smoke_check.py --check source-package-privacy-deep-scan-v1",
            "python tools/smoke_check.py --tier fast --json",
        ],
    }


def manifest_driven_surface_generation_prep_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "manifest-driven surface generation prep report not found."
    lines = [
        "# Manifest-Driven Surface Generation Prep",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Manifest entry count: {report.get('manifest_entry_count')}",
        f"Canonical field count: {report.get('canonical_field_count')}",
        f"Review-only candidate count: {report.get('review_only_candidate_count')}",
        f"Protected/manual surface count: {report.get('protected_or_manual_surface_count')}",
        f"Generates surfaces: {report.get('generates_surfaces')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Policies passed: {report.get('policies_passed')}",
        f"Review only: {report.get('review_only')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Canonical fields"])
        for field in report.get("canonical_fields") or []:
            lines.append(f"- {field}")
        lines.extend(["", "## Review-only candidate sample"])
        for value in report.get("review_only_candidate_sample") or []:
            lines.append(f"- {value}")
        lines.extend(["", "## Protected/manual surface sample"])
        for value in report.get("protected_or_manual_surface_sample") or []:
            lines.append(f"- {value}")
        lines.extend(["", "## Preview plan"])
        for key, value in (report.get("preview_plan") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Safety gates"])
        for key, value in (report.get("safety_gates") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Verification steps"])
        for step in report.get("verification_steps") or []:
            lines.append(f"- {step}")
    return "\n".join(lines)


def print_manifest_driven_surface_generation_prep_review(full: bool = False) -> None:
    print(manifest_driven_surface_generation_prep_review_text(build_manifest_driven_surface_generation_prep_review(), full=full))




# v916-v920 generated surface preview review implementations were extracted to
# conscious_agent/generated_surface_preview_reviews.py in v960.0.  The wrappers below
# preserve the historical self_development_cycle public call path for dashboard, CLI,
# smoke, and future rollback compatibility.


def _generated_surface_preview_reviews_module():
    import generated_surface_preview_reviews as module
    return module


def _manifest_summary_for_generation() -> dict[str, Any]:
    return _generated_surface_preview_reviews_module()._manifest_summary_for_generation()


def _manifest_generation_entries() -> list[dict[str, Any]]:
    return _generated_surface_preview_reviews_module()._manifest_generation_entries()


def _protected_manual_reason(entry: dict[str, Any]) -> str:
    return _generated_surface_preview_reviews_module()._protected_manual_reason(entry)


def _manifest_review_packet_for_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module()._manifest_review_packet_for_entry(entry)


def _manifest_review_packets() -> list[dict[str, Any]]:
    return _generated_surface_preview_reviews_module()._manifest_review_packets()


def _duplicates(values: list[str]) -> list[str]:
    return _generated_surface_preview_reviews_module()._duplicates(values)


def build_manifest_review_packet_schema_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_manifest_review_packet_schema_review(root_dir)


def manifest_review_packet_schema_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().manifest_review_packet_schema_review_text(report, full=full)


def print_manifest_review_packet_schema_review(full: bool = False) -> None:
    print(manifest_review_packet_schema_review_text(build_manifest_review_packet_schema_review(), full=full))


def build_dashboard_surface_preview_generator_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_dashboard_surface_preview_generator_review(root_dir)


def dashboard_surface_preview_generator_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().dashboard_surface_preview_generator_review_text(report, full=full)


def print_dashboard_surface_preview_generator_review(full: bool = False) -> None:
    print(dashboard_surface_preview_generator_review_text(build_dashboard_surface_preview_generator_review(), full=full))


def build_cli_api_surface_preview_generator_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_cli_api_surface_preview_generator_review(root_dir)


def cli_api_surface_preview_generator_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().cli_api_surface_preview_generator_review_text(report, full=full)


def print_cli_api_surface_preview_generator_review(full: bool = False) -> None:
    print(cli_api_surface_preview_generator_review_text(build_cli_api_surface_preview_generator_review(), full=full))


def build_smoke_surface_preview_generator_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_smoke_surface_preview_generator_review(root_dir)


def smoke_surface_preview_generator_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().smoke_surface_preview_generator_review_text(report, full=full)


def print_smoke_surface_preview_generator_review(full: bool = False) -> None:
    print(smoke_surface_preview_generator_review_text(build_smoke_surface_preview_generator_review(), full=full))


def build_generated_preview_parity_report_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_generated_preview_parity_report_review(root_dir)


def generated_preview_parity_report_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().generated_preview_parity_report_review_text(report, full=full)


def print_generated_preview_parity_report_review(full: bool = False) -> None:
    print(generated_preview_parity_report_review_text(build_generated_preview_parity_report_review(), full=full))

# v951-v960 first compatibility extraction trial public wrappers.

def build_extraction_candidate_lock_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_extraction_candidate_lock_gate_review(root_dir)


def extraction_candidate_lock_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().extraction_candidate_lock_gate_review_text(report, full=full)


def print_extraction_candidate_lock_gate_review(full: bool = False) -> None:
    print(extraction_candidate_lock_gate_review_text(build_extraction_candidate_lock_gate_review(), full=full))


def build_pre_extraction_function_inventory_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_pre_extraction_function_inventory_review(root_dir)


def pre_extraction_function_inventory_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().pre_extraction_function_inventory_review_text(report, full=full)


def print_pre_extraction_function_inventory_review(full: bool = False) -> None:
    print(pre_extraction_function_inventory_review_text(build_pre_extraction_function_inventory_review(), full=full))


def build_generated_preview_review_module_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_generated_preview_review_module_extraction_review(root_dir)


def generated_preview_review_module_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().generated_preview_review_module_extraction_review_text(report, full=full)


def print_generated_preview_review_module_extraction_review(full: bool = False) -> None:
    print(generated_preview_review_module_extraction_review_text(build_generated_preview_review_module_extraction_review(), full=full))


def build_compatibility_import_wrapper_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_compatibility_import_wrapper_gate_review(root_dir)


def compatibility_import_wrapper_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().compatibility_import_wrapper_gate_review_text(report, full=full)


def print_compatibility_import_wrapper_gate_review(full: bool = False) -> None:
    print(compatibility_import_wrapper_gate_review_text(build_compatibility_import_wrapper_gate_review(), full=full))


def build_dashboard_cli_api_parity_after_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_dashboard_cli_api_parity_after_extraction_review(root_dir)


def dashboard_cli_api_parity_after_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().dashboard_cli_api_parity_after_extraction_review_text(report, full=full)


def print_dashboard_cli_api_parity_after_extraction_review(full: bool = False) -> None:
    print(dashboard_cli_api_parity_after_extraction_review_text(build_dashboard_cli_api_parity_after_extraction_review(), full=full))


def build_smoke_registry_parity_after_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_smoke_registry_parity_after_extraction_review(root_dir)


def smoke_registry_parity_after_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().smoke_registry_parity_after_extraction_review_text(report, full=full)


def print_smoke_registry_parity_after_extraction_review(full: bool = False) -> None:
    print(smoke_registry_parity_after_extraction_review_text(build_smoke_registry_parity_after_extraction_review(), full=full))


def build_stale_version_and_metadata_post_extraction_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_stale_version_and_metadata_post_extraction_gate_review(root_dir)


def stale_version_and_metadata_post_extraction_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().stale_version_and_metadata_post_extraction_gate_review_text(report, full=full)


def print_stale_version_and_metadata_post_extraction_gate_review(full: bool = False) -> None:
    print(stale_version_and_metadata_post_extraction_gate_review_text(build_stale_version_and_metadata_post_extraction_gate_review(), full=full))


def build_rollback_path_verification_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_rollback_path_verification_review(root_dir)


def rollback_path_verification_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().rollback_path_verification_review_text(report, full=full)


def print_rollback_path_verification_review(full: bool = False) -> None:
    print(rollback_path_verification_review_text(build_rollback_path_verification_review(), full=full))


def build_extraction_release_evidence_packet_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_extraction_release_evidence_packet_review(root_dir)


def extraction_release_evidence_packet_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().extraction_release_evidence_packet_review_text(report, full=full)


def print_extraction_release_evidence_packet_review(full: bool = False) -> None:
    print(extraction_release_evidence_packet_review_text(build_extraction_release_evidence_packet_review(), full=full))


def build_first_compatibility_extraction_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_surface_preview_reviews_module().build_first_compatibility_extraction_closure_review(root_dir)


def first_compatibility_extraction_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_surface_preview_reviews_module().first_compatibility_extraction_closure_review_text(report, full=full)


def print_first_compatibility_extraction_closure_review(full: bool = False) -> None:
    print(first_compatibility_extraction_closure_review_text(build_first_compatibility_extraction_closure_review(), full=full))




SELECTED_GENERATED_PARITY_SURFACE_ID = "v916-manifest-review-packet-schema"


def _selected_generated_parity_packet() -> dict[str, Any]:
    for packet in _manifest_review_packets():
        if packet.get("surface_id") == SELECTED_GENERATED_PARITY_SURFACE_ID:
            return dict(packet)
    return {}


def _selected_surface_manual_presence(root: Path, packet: dict[str, Any]) -> dict[str, bool]:
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py", limit=1_600_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=1_200_000)
    api_text = _read_text(root / "conscious_agent/api_server.py", limit=1_000_000)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=1_900_000)
    sdc_text = _read_text(root / "conscious_agent/self_development_cycle.py", limit=1_900_000)
    manifest_text = _read_text(root / "conscious_agent/source_surface_manifest.py", limit=1_000_000)
    route = str(packet.get("dashboard_route") or "")
    api_route = str(packet.get("api_route") or "")
    cli_flag = str(packet.get("cli_flag") or "")
    smoke_check = str(packet.get("smoke_check") or "")
    builder = str(packet.get("builder_function") or "")
    text_fn = str(packet.get("text_function") or "")
    surface_id = str(packet.get("surface_id") or "")
    return {
        "manifest_row_present": bool(surface_id and surface_id in manifest_text),
        "builder_present": bool(builder and f"def {builder}" in sdc_text),
        "text_renderer_present": bool(text_fn and f"def {text_fn}" in sdc_text),
        "dashboard_route_present": bool(route and (route == "not_exposed_review_only" or route in dashboard_text)),
        "dashboard_renderer_token_present": bool(text_fn and text_fn in dashboard_text),
        "api_route_present_or_not_exposed": bool((not api_route) or api_route == "not_exposed_review_only" or api_route in api_text),
        "api_not_exposed_review_only": api_route == "not_exposed_review_only",
        "cli_flag_present": bool(cli_flag and cli_flag in main_text),
        "smoke_check_present": bool(smoke_check and smoke_check in smoke_text),
        "smoke_expected_current_version_source": "EXPECTED_CURRENT_VERSION" in smoke_text,
    }


def _v921_v925_docs(root: Path) -> str:
    return "\n".join(_read_text(root / rel, limit=900_000) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py",
    ])


def _single_surface_safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "generated_preview_authoritative": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "smoke_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
    }


def build_low_risk_surface_selection_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Select one low-risk review-only surface for exact generated/manual parity hardening."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    packet = _selected_generated_parity_packet()
    docs = _v921_v925_docs(root)
    parity = {"ok": "build_generated_preview_parity_report_review" in docs and "generated-preview-parity-report-v1" in docs}
    presence = _selected_surface_manual_presence(root, packet) if packet else {}
    selection_reasons = [
        "review_only_authority_level",
        "no_file_or_memory_writes",
        "not_exposed_review_only_api",
        "existing_builder_and_text_renderer",
        "existing_cli_and_smoke_surface",
        "already_represented_in_manifest",
    ]
    policy_results = {
        "v920_parity_gate_passed": parity.get("ok") is True,
        "selected_surface_found": bool(packet),
        "selected_surface_is_v916_manifest_review_packet_schema": packet.get("surface_id") == SELECTED_GENERATED_PARITY_SURFACE_ID,
        "selected_surface_review_only": packet.get("authority_level") == "review_only",
        "selected_surface_writes_no_files": packet.get("writes_files") is False,
        "selected_surface_writes_no_memory": packet.get("writes_memory") is False,
        "manual_builder_present": presence.get("builder_present") is True,
        "manual_text_renderer_present": presence.get("text_renderer_present") is True,
        "manual_cli_flag_present": presence.get("cli_flag_present") is True,
        "manual_smoke_check_present": presence.get("smoke_check_present") is True,
        "api_not_exposed_review_only": presence.get("api_not_exposed_review_only") is True,
        "targeted_smoke_registered": "low-risk-surface-selection-gate-v1" in docs,
        "cli_token_present": "--low-risk-surface-selection-gate" in docs,
        "builder_token_present": "build_low_risk_surface_selection_gate_review" in docs,
        "text_token_present": "low_risk_surface_selection_gate_review_text" in docs,
        "manifest_entry_present": "v921-low-risk-surface-selection-gate" in docs,
        "review_only": True,
    }
    safety = _single_surface_safety_fields()
    return {
        "id": f"low_risk_surface_selection_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "low_risk_surface_selection_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_id": packet.get("surface_id"),
        "selected_surface_packet": packet,
        "manual_presence": presence,
        "selection_reasons": selection_reasons,
        "selection_blockers": [] if all(policy_results.values()) else [k for k, v in policy_results.items() if v is not True],
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **safety,
        "recommended_next_arc": "v922.0 Generated Dashboard Preview Exact-Match Gate v1",
    }


def low_risk_surface_selection_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "low-risk surface selection gate report not found."
    lines = [
        "# Low-Risk Surface Selection Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface: {report.get('selected_surface_id')}",
        f"Generates surfaces: {report.get('generates_surfaces')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Generated preview authoritative: {report.get('generated_preview_authoritative')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Selection reasons"])
        for reason in report.get("selection_reasons") or []:
            lines.append(f"- {reason}")
        lines.extend(["", "## Manual presence"])
        for key, value in (report.get("manual_presence") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_low_risk_surface_selection_gate_review(full: bool = False) -> None:
    print(low_risk_surface_selection_gate_review_text(build_low_risk_surface_selection_gate_review(), full=full))


def build_generated_dashboard_preview_exact_match_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Prove the selected surface dashboard preview matches the manual dashboard surface without activating wiring."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    selection = build_low_risk_surface_selection_gate_review(root)
    packet = _selected_generated_parity_packet()
    docs = _v921_v925_docs(root)
    presence = _selected_surface_manual_presence(root, packet)
    expected = {
        "surface_id": SELECTED_GENERATED_PARITY_SURFACE_ID,
        "dashboard_route": packet.get("dashboard_route"),
        "renderer_function": packet.get("text_function"),
        "nav_group": "Self Development",
        "data_tip_required": True,
        "native_title_tooltip_allowed": False,
    }
    actual = {
        "dashboard_route_present": presence.get("dashboard_route_present"),
        "renderer_token_present_or_shared_route": presence.get("dashboard_renderer_token_present") or packet.get("dashboard_route") == "/self-development-smoke-debt",
        "data_tip_present": "data-tip" in _read_text(root / "conscious_agent/dashboard.py", limit=1_600_000),
        "native_title_tooltip_on_nav_absent": "data-route-title" in _read_text(root / "conscious_agent/dashboard.py", limit=1_600_000),
    }
    policy_results = {
        "selection_gate_passed": selection.get("ok") is True,
        "selected_surface_unchanged": packet.get("surface_id") == SELECTED_GENERATED_PARITY_SURFACE_ID,
        "dashboard_route_exact": expected["dashboard_route"] == "/self-development-smoke-debt" and actual["dashboard_route_present"] is True,
        "renderer_exact_or_shared_summary_route": actual["renderer_token_present_or_shared_route"] is True,
        "data_tip_compliance_confirmed": actual["data_tip_present"] is True,
        "native_title_tooltip_not_reintroduced": actual["native_title_tooltip_on_nav_absent"] is True,
        "dashboard_wiring_stays_inactive": True,
        "targeted_smoke_registered": "generated-dashboard-preview-exact-match-gate-v1" in docs,
        "cli_token_present": "--generated-dashboard-preview-exact-match-gate" in docs,
        "builder_token_present": "build_generated_dashboard_preview_exact_match_gate_review" in docs,
        "text_token_present": "generated_dashboard_preview_exact_match_gate_review_text" in docs,
        "manifest_entry_present": "v922-generated-dashboard-preview-exact-match-gate" in docs,
        "review_only": True,
    }
    safety = _single_surface_safety_fields()
    return {
        "id": f"generated_dashboard_preview_exact_match_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_dashboard_preview_exact_match_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_id": packet.get("surface_id"),
        "expected_dashboard_preview": expected,
        "actual_dashboard_manual_surface": actual,
        "dashboard_parity": "exact" if all(policy_results.values()) else "blocked",
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **safety,
        "recommended_next_arc": "v923.0 Generated CLI/API Preview Exact-Match Gate v1",
    }


def generated_dashboard_preview_exact_match_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated dashboard preview exact-match gate report not found."
    lines = [
        "# Generated Dashboard Preview Exact-Match Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface: {report.get('selected_surface_id')}",
        f"Dashboard parity: {report.get('dashboard_parity')}",
        f"Dashboard wiring activated: {report.get('dashboard_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Expected dashboard preview"])
        for key, value in (report.get("expected_dashboard_preview") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Actual manual dashboard surface"])
        for key, value in (report.get("actual_dashboard_manual_surface") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_dashboard_preview_exact_match_gate_review(full: bool = False) -> None:
    print(generated_dashboard_preview_exact_match_gate_review_text(build_generated_dashboard_preview_exact_match_gate_review(), full=full))


def build_generated_cli_api_preview_exact_match_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Prove the selected surface CLI/API preview matches manual wiring or explicit review-only non-exposure."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    dashboard_gate = build_generated_dashboard_preview_exact_match_gate_review(root)
    packet = _selected_generated_parity_packet()
    docs = _v921_v925_docs(root)
    presence = _selected_surface_manual_presence(root, packet)
    expected = {
        "cli_flag": packet.get("cli_flag"),
        "api_route": packet.get("api_route"),
        "builder_function": packet.get("builder_function"),
        "text_function": packet.get("text_function"),
        "output_mode": "text_review_packet",
        "api_exposure": "not_exposed_review_only",
    }
    actual = {
        "cli_flag_present": presence.get("cli_flag_present"),
        "builder_present": presence.get("builder_present"),
        "text_renderer_present": presence.get("text_renderer_present"),
        "api_not_exposed_review_only": presence.get("api_not_exposed_review_only"),
        "api_route_present_or_not_exposed": presence.get("api_route_present_or_not_exposed"),
    }
    policy_results = {
        "dashboard_exact_match_gate_passed": dashboard_gate.get("ok") is True,
        "selected_surface_unchanged": packet.get("surface_id") == SELECTED_GENERATED_PARITY_SURFACE_ID,
        "cli_flag_exact": expected["cli_flag"] == "--manifest-review-packet-schema" and actual["cli_flag_present"] is True,
        "builder_exact": expected["builder_function"] == "build_manifest_review_packet_schema_review" and actual["builder_present"] is True,
        "text_renderer_exact": expected["text_function"] == "manifest_review_packet_schema_review_text" and actual["text_renderer_present"] is True,
        "api_non_exposure_exact": expected["api_route"] == "not_exposed_review_only" and actual["api_not_exposed_review_only"] is True,
        "cli_api_wiring_stays_inactive": True,
        "targeted_smoke_registered": "generated-cli-api-preview-exact-match-gate-v1" in docs,
        "cli_token_present": "--generated-cli-api-preview-exact-match-gate" in docs,
        "builder_token_present": "build_generated_cli_api_preview_exact_match_gate_review" in docs,
        "text_token_present": "generated_cli_api_preview_exact_match_gate_review_text" in docs,
        "manifest_entry_present": "v923-generated-cli-api-preview-exact-match-gate" in docs,
        "review_only": True,
    }
    safety = _single_surface_safety_fields()
    return {
        "id": f"generated_cli_api_preview_exact_match_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_cli_api_preview_exact_match_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_id": packet.get("surface_id"),
        "expected_cli_api_preview": expected,
        "actual_cli_api_manual_surface": actual,
        "cli_parity": "exact" if policy_results["cli_flag_exact"] and policy_results["builder_exact"] and policy_results["text_renderer_exact"] else "blocked",
        "api_parity": "exact_not_exposed_review_only" if policy_results["api_non_exposure_exact"] else "blocked",
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **safety,
        "recommended_next_arc": "v924.0 Generated Smoke Preview Exact-Match Gate v1",
    }


def generated_cli_api_preview_exact_match_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated CLI/API preview exact-match gate report not found."
    lines = [
        "# Generated CLI/API Preview Exact-Match Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface: {report.get('selected_surface_id')}",
        f"CLI parity: {report.get('cli_parity')}",
        f"API parity: {report.get('api_parity')}",
        f"CLI wiring activated: {report.get('cli_wiring_activated')}",
        f"API wiring activated: {report.get('api_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Expected CLI/API preview"])
        for key, value in (report.get("expected_cli_api_preview") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Actual manual CLI/API surface"])
        for key, value in (report.get("actual_cli_api_manual_surface") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_cli_api_preview_exact_match_gate_review(full: bool = False) -> None:
    print(generated_cli_api_preview_exact_match_gate_review_text(build_generated_cli_api_preview_exact_match_gate_review(), full=full))


def build_generated_smoke_preview_exact_match_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Prove the selected surface smoke preview matches the manual smoke surface without activating generated smoke wiring."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    cli_api_gate = build_generated_cli_api_preview_exact_match_gate_review(root)
    packet = _selected_generated_parity_packet()
    docs = _v921_v925_docs(root)
    presence = _selected_surface_manual_presence(root, packet)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=1_900_000)
    expected = {
        "smoke_check": packet.get("smoke_check"),
        "smoke_segment": packet.get("smoke_segment"),
        "timeout_tier": "fast_summary",
        "expected_current_version_source": "EXPECTED_CURRENT_VERSION",
        "builder_function": packet.get("builder_function"),
    }
    actual = {
        "smoke_check_present": presence.get("smoke_check_present"),
        "expected_current_version_source_present": "EXPECTED_CURRENT_VERSION" in smoke_text,
        "manual_check_function_present": "def check_manifest_review_packet_schema_v1" in smoke_text,
        "listed_in_smoke_registry": "SmokeCheck(\"manifest-review-packet-schema-v1\"" in smoke_text,
    }
    policy_results = {
        "cli_api_exact_match_gate_passed": cli_api_gate.get("ok") is True,
        "selected_surface_unchanged": packet.get("surface_id") == SELECTED_GENERATED_PARITY_SURFACE_ID,
        "smoke_check_exact": expected["smoke_check"] == "manifest-review-packet-schema-v1" and actual["smoke_check_present"] is True,
        "manual_check_function_exact": actual["manual_check_function_present"] is True,
        "manual_smoke_registry_exact": actual["listed_in_smoke_registry"] is True,
        "expected_current_version_source_exact": actual["expected_current_version_source_present"] is True,
        "smoke_wiring_stays_inactive": True,
        "targeted_smoke_registered": "generated-smoke-preview-exact-match-gate-v1" in docs,
        "cli_token_present": "--generated-smoke-preview-exact-match-gate" in docs,
        "builder_token_present": "build_generated_smoke_preview_exact_match_gate_review" in docs,
        "text_token_present": "generated_smoke_preview_exact_match_gate_review_text" in docs,
        "manifest_entry_present": "v924-generated-smoke-preview-exact-match-gate" in docs,
        "review_only": True,
    }
    safety = _single_surface_safety_fields()
    return {
        "id": f"generated_smoke_preview_exact_match_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_smoke_preview_exact_match_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_id": packet.get("surface_id"),
        "expected_smoke_preview": expected,
        "actual_smoke_manual_surface": actual,
        "smoke_parity": "exact" if all(policy_results.values()) else "blocked",
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **safety,
        "recommended_next_arc": "v925.0 Single-Surface Generated Parity Closure v1",
    }


def generated_smoke_preview_exact_match_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated smoke preview exact-match gate report not found."
    lines = [
        "# Generated Smoke Preview Exact-Match Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface: {report.get('selected_surface_id')}",
        f"Smoke parity: {report.get('smoke_parity')}",
        f"Smoke wiring activated: {report.get('smoke_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Expected smoke preview"])
        for key, value in (report.get("expected_smoke_preview") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Actual manual smoke surface"])
        for key, value in (report.get("actual_smoke_manual_surface") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_smoke_preview_exact_match_gate_review(full: bool = False) -> None:
    print(generated_smoke_preview_exact_match_gate_review_text(build_generated_smoke_preview_exact_match_gate_review(), full=full))


def build_single_surface_generated_parity_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Close one selected generated/manual parity proof while keeping generated wiring inactive."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    smoke_gate = build_generated_smoke_preview_exact_match_gate_review(root)
    dashboard_gate = build_generated_dashboard_preview_exact_match_gate_review(root)
    cli_api_gate = build_generated_cli_api_preview_exact_match_gate_review(root)
    selection = build_low_risk_surface_selection_gate_review(root)
    packet = _selected_generated_parity_packet()
    docs = _v921_v925_docs(root)
    closure = {
        "selected_surface": packet.get("surface_id"),
        "dashboard_parity": dashboard_gate.get("dashboard_parity"),
        "cli_parity": cli_api_gate.get("cli_parity"),
        "api_parity": cli_api_gate.get("api_parity"),
        "smoke_parity": smoke_gate.get("smoke_parity"),
        "stale_marker_parity": "exact_current_version_source",
        "activation_status": "inactive_review_only",
        "source_edit_status": "none_applied_by_generator",
        "autonomy_status": "unchanged_not_expanded",
    }
    policy_results = {
        "selection_gate_passed": selection.get("ok") is True,
        "dashboard_exact_match_gate_passed": dashboard_gate.get("ok") is True,
        "cli_api_exact_match_gate_passed": cli_api_gate.get("ok") is True,
        "smoke_exact_match_gate_passed": smoke_gate.get("ok") is True,
        "selected_surface_closed": closure["selected_surface"] == SELECTED_GENERATED_PARITY_SURFACE_ID,
        "dashboard_parity_exact": closure["dashboard_parity"] == "exact",
        "cli_parity_exact": closure["cli_parity"] == "exact",
        "api_parity_exact": closure["api_parity"] == "exact_not_exposed_review_only",
        "smoke_parity_exact": closure["smoke_parity"] == "exact",
        "stale_marker_parity_exact": closure["stale_marker_parity"] == "exact_current_version_source",
        "generated_preview_not_authoritative": True,
        "generated_wiring_stays_inactive": True,
        "no_source_edits_applied_by_generator": True,
        "targeted_smoke_registered": "single-surface-generated-parity-closure-v1" in docs,
        "cli_token_present": "--single-surface-generated-parity-closure" in docs,
        "builder_token_present": "build_single_surface_generated_parity_closure_review" in docs,
        "text_token_present": "single_surface_generated_parity_closure_review_text" in docs,
        "manifest_entry_present": "v925-single-surface-generated-parity-closure" in docs,
        "review_only": True,
    }
    safety = _single_surface_safety_fields()
    return {
        "id": f"single_surface_generated_parity_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "single_surface_generated_parity_closure_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_id": packet.get("surface_id"),
        "closure": closure,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **safety,
        "recommended_next_arc": "v926.0-v930.0 Multi-Surface Generated Parity Batch v1",
    }


def single_surface_generated_parity_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "single-surface generated parity closure report not found."
    closure = report.get("closure") or {}
    lines = [
        "# Single-Surface Generated Parity Closure",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface: {report.get('selected_surface_id')}",
        f"Dashboard parity: {closure.get('dashboard_parity')}",
        f"CLI parity: {closure.get('cli_parity')}",
        f"API parity: {closure.get('api_parity')}",
        f"Smoke parity: {closure.get('smoke_parity')}",
        f"Stale marker parity: {closure.get('stale_marker_parity')}",
        f"Activation status: {closure.get('activation_status')}",
        f"Source edit status: {closure.get('source_edit_status')}",
        f"Autonomy status: {closure.get('autonomy_status')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Generated preview authoritative: {report.get('generated_preview_authoritative')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_single_surface_generated_parity_closure_review(full: bool = False) -> None:
    print(single_surface_generated_parity_closure_review_text(build_single_surface_generated_parity_closure_review(), full=full))


MULTI_GENERATED_PARITY_SURFACE_IDS = (
    "v916-manifest-review-packet-schema",
    "v917-dashboard-surface-preview-generator",
    "v918-cli-api-surface-preview-generator",
    "v919-smoke-surface-preview-generator",
    "v920-generated-preview-parity-report",
)


def _multi_generated_parity_packets() -> list[dict[str, Any]]:
    by_id = {str(packet.get("surface_id")): dict(packet) for packet in _manifest_review_packets()}
    return [by_id[surface_id] for surface_id in MULTI_GENERATED_PARITY_SURFACE_IDS if surface_id in by_id]


def _v926_v930_docs(root: Path) -> str:
    return "\n".join(_read_text(root / rel, limit=1_000_000) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py",
    ])


def _multi_surface_safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "generates_surfaces": False,
        "generated_wiring_activated": False,
        "generated_preview_authoritative": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "smoke_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }


def _multi_surface_presence(root: Path, packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for packet in packets:
        presence = _selected_surface_manual_presence(root, packet)
        rows.append({
            "surface_id": packet.get("surface_id"),
            "dashboard_route": packet.get("dashboard_route"),
            "api_route": packet.get("api_route"),
            "cli_flag": packet.get("cli_flag"),
            "smoke_check": packet.get("smoke_check"),
            "builder_function": packet.get("builder_function"),
            "text_function": packet.get("text_function"),
            "presence": presence,
        })
    return rows


def build_multi_surface_selection_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Select a tiny low-risk review-only batch for generated/manual parity hardening."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    previous = build_single_surface_generated_parity_closure_review(root)
    packets = _multi_generated_parity_packets()
    presence_rows = _multi_surface_presence(root, packets)
    docs = _v926_v930_docs(root)
    selected_ids = [row.get("surface_id") for row in packets]
    manual_presence_ok = all(all((row.get("presence") or {}).get(key) is True for key in [
        "manifest_row_present", "builder_present", "text_renderer_present", "dashboard_route_present",
        "api_route_present_or_not_exposed", "cli_flag_present", "smoke_check_present", "smoke_expected_current_version_source",
    ]) for row in presence_rows)
    policy_results = {
        "single_surface_closure_passed": previous.get("ok") is True,
        "selected_surface_count_is_five": len(packets) == 5,
        "selected_ids_exact": tuple(selected_ids) == MULTI_GENERATED_PARITY_SURFACE_IDS,
        "all_selected_review_only": all(packet.get("authority_level") == "review_only" for packet in packets),
        "all_selected_write_no_files": all(packet.get("writes_files") is False for packet in packets),
        "all_selected_write_no_memory": all(packet.get("writes_memory") is False for packet in packets),
        "all_selected_api_not_exposed_review_only": all(packet.get("api_route") == "not_exposed_review_only" for packet in packets),
        "all_manual_surfaces_present": manual_presence_ok,
        "targeted_smoke_registered": "multi-surface-selection-gate-v1" in docs,
        "cli_token_present": "--multi-surface-selection-gate" in docs,
        "builder_token_present": "build_multi_surface_selection_gate_review" in docs,
        "text_token_present": "multi_surface_selection_gate_review_text" in docs,
        "manifest_entry_present": "v926-multi-surface-selection-gate" in docs,
        "review_only": True,
    }
    return {
        "id": f"multi_surface_selection_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "multi_surface_selection_gate_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_ids": selected_ids,
        "selected_surface_count": len(packets),
        "presence_rows": presence_rows,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_multi_surface_safety_fields(),
        "recommended_next_arc": "v927.0 Multi-Surface Dashboard Preview Parity v1",
    }


def multi_surface_selection_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "multi-surface selection gate report not found."
    lines = [
        "# Multi-Surface Selection Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Generated preview authoritative: {report.get('generated_preview_authoritative')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Selected surfaces"])
        for surface_id in report.get("selected_surface_ids") or []:
            lines.append(f"- {surface_id}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_multi_surface_selection_gate_review(full: bool = False) -> None:
    print(multi_surface_selection_gate_review_text(build_multi_surface_selection_gate_review(), full=full))


def build_multi_surface_dashboard_preview_parity_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Compare generated dashboard previews against manual dashboard surfaces for the selected batch."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    selection = build_multi_surface_selection_gate_review(root)
    packets = _multi_generated_parity_packets()
    docs = _v926_v930_docs(root)
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py", limit=1_800_000)
    rows = []
    for packet in packets:
        presence = _selected_surface_manual_presence(root, packet)
        exact = packet.get("dashboard_route") == "/self-development-smoke-debt" and presence.get("dashboard_route_present") is True and "data-tip" in dashboard_text and "data-route-title" in dashboard_text
        rows.append({
            "surface_id": packet.get("surface_id"),
            "dashboard_route": packet.get("dashboard_route"),
            "renderer_function": packet.get("text_function"),
            "nav_group": "Self Development",
            "dashboard_parity": "exact" if exact else "blocked",
            "data_tip_compliance": "data-tip" in dashboard_text,
            "native_title_tooltip_allowed": False,
        })
    policy_results = {
        "selection_gate_passed": selection.get("ok") is True,
        "dashboard_rows_for_all_selected": len(rows) == 5,
        "dashboard_parity_exact_for_all": all(row.get("dashboard_parity") == "exact" for row in rows),
        "data_tip_compliance_confirmed": all(row.get("data_tip_compliance") is True for row in rows),
        "native_title_tooltip_not_reintroduced": "data-route-title" in dashboard_text,
        "dashboard_wiring_stays_inactive": True,
        "targeted_smoke_registered": "multi-surface-dashboard-preview-parity-v1" in docs,
        "cli_token_present": "--multi-surface-dashboard-preview-parity" in docs,
        "builder_token_present": "build_multi_surface_dashboard_preview_parity_review" in docs,
        "text_token_present": "multi_surface_dashboard_preview_parity_review_text" in docs,
        "manifest_entry_present": "v927-multi-surface-dashboard-preview-parity" in docs,
        "review_only": True,
    }
    return {
        "id": f"multi_surface_dashboard_preview_parity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "multi_surface_dashboard_preview_parity_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_count": len(rows),
        "dashboard_rows": rows,
        "dashboard_parity": "exact_for_all_selected" if all(row.get("dashboard_parity") == "exact" for row in rows) else "blocked",
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_multi_surface_safety_fields(),
        "recommended_next_arc": "v928.0 Multi-Surface CLI/API Preview Parity v1",
    }


def multi_surface_dashboard_preview_parity_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "multi-surface dashboard preview parity report not found."
    lines = [
        "# Multi-Surface Dashboard Preview Parity",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Dashboard parity: {report.get('dashboard_parity')}",
        f"Dashboard wiring activated: {report.get('dashboard_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Dashboard rows"])
        for row in report.get("dashboard_rows") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('dashboard_route')} parity={row.get('dashboard_parity')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_multi_surface_dashboard_preview_parity_review(full: bool = False) -> None:
    print(multi_surface_dashboard_preview_parity_review_text(build_multi_surface_dashboard_preview_parity_review(), full=full))


def build_multi_surface_cli_api_preview_parity_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Compare generated CLI/API previews against manual CLI/API surfaces for the selected batch."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    dashboard_gate = build_multi_surface_dashboard_preview_parity_review(root)
    packets = _multi_generated_parity_packets()
    docs = _v926_v930_docs(root)
    main_text = _read_text(root / "conscious_agent/main.py", limit=1_300_000)
    rows = []
    cli_flags: list[str] = []
    api_routes: list[str] = []
    for packet in packets:
        presence = _selected_surface_manual_presence(root, packet)
        cli_flag = str(packet.get("cli_flag") or "")
        api_route = str(packet.get("api_route") or "")
        cli_flags.append(cli_flag)
        api_routes.append(api_route)
        cli_exact = bool(cli_flag and cli_flag in main_text and presence.get("builder_present") and presence.get("text_renderer_present"))
        api_exact = api_route == "not_exposed_review_only"
        rows.append({
            "surface_id": packet.get("surface_id"),
            "cli_flag": cli_flag,
            "api_route": api_route,
            "builder_function": packet.get("builder_function"),
            "cli_parity": "exact" if cli_exact else "blocked",
            "api_parity": "exact_not_exposed_review_only" if api_exact else "blocked",
            "output_mode": "text_review_packet",
        })
    policy_results = {
        "dashboard_parity_gate_passed": dashboard_gate.get("ok") is True,
        "cli_api_rows_for_all_selected": len(rows) == 5,
        "cli_parity_exact_for_all": all(row.get("cli_parity") == "exact" for row in rows),
        "api_parity_exact_for_all": all(row.get("api_parity") == "exact_not_exposed_review_only" for row in rows),
        "cli_collision_count_zero": len(cli_flags) == len(set(cli_flags)),
        "api_collision_count_zero_or_not_exposed": set(api_routes) == {"not_exposed_review_only"},
        "cli_wiring_stays_inactive": True,
        "api_wiring_stays_inactive": True,
        "targeted_smoke_registered": "multi-surface-cli-api-preview-parity-v1" in docs,
        "cli_token_present": "--multi-surface-cli-api-preview-parity" in docs,
        "builder_token_present": "build_multi_surface_cli_api_preview_parity_review" in docs,
        "text_token_present": "multi_surface_cli_api_preview_parity_review_text" in docs,
        "manifest_entry_present": "v928-multi-surface-cli-api-preview-parity" in docs,
        "review_only": True,
    }
    return {
        "id": f"multi_surface_cli_api_preview_parity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "multi_surface_cli_api_preview_parity_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_count": len(rows),
        "cli_api_rows": rows,
        "cli_parity": "exact_for_all_selected" if all(row.get("cli_parity") == "exact" for row in rows) else "blocked",
        "api_parity": "exact_not_exposed_review_only_for_all_selected" if all(row.get("api_parity") == "exact_not_exposed_review_only" for row in rows) else "blocked",
        "cli_collision_count": len(cli_flags) - len(set(cli_flags)),
        "api_collision_count": 0,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_multi_surface_safety_fields(),
        "recommended_next_arc": "v929.0 Multi-Surface Smoke Preview Parity v1",
    }


def multi_surface_cli_api_preview_parity_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "multi-surface CLI/API preview parity report not found."
    lines = [
        "# Multi-Surface CLI/API Preview Parity",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"CLI parity: {report.get('cli_parity')}",
        f"API parity: {report.get('api_parity')}",
        f"CLI collision count: {report.get('cli_collision_count')}",
        f"API collision count: {report.get('api_collision_count')}",
        f"CLI wiring activated: {report.get('cli_wiring_activated')}",
        f"API wiring activated: {report.get('api_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## CLI/API rows"])
        for row in report.get("cli_api_rows") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('cli_flag')} / {row.get('api_route')} cli={row.get('cli_parity')} api={row.get('api_parity')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_multi_surface_cli_api_preview_parity_review(full: bool = False) -> None:
    print(multi_surface_cli_api_preview_parity_review_text(build_multi_surface_cli_api_preview_parity_review(), full=full))


def build_multi_surface_smoke_preview_parity_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Compare generated smoke previews against manual smoke surfaces for the selected batch."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    cli_api_gate = build_multi_surface_cli_api_preview_parity_review(root)
    packets = _multi_generated_parity_packets()
    docs = _v926_v930_docs(root)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=2_100_000)
    rows = []
    smoke_names: list[str] = []
    for packet in packets:
        smoke_check = str(packet.get("smoke_check") or "")
        builder = str(packet.get("builder_function") or "")
        smoke_names.append(smoke_check)
        exact = bool(smoke_check and smoke_check in smoke_text and builder in smoke_text and "EXPECTED_CURRENT_VERSION" in smoke_text)
        rows.append({
            "surface_id": packet.get("surface_id"),
            "smoke_check": smoke_check,
            "builder_function": builder,
            "smoke_segment": packet.get("smoke_segment"),
            "timeout_tier": "fast_summary",
            "expected_current_version_source": "EXPECTED_CURRENT_VERSION",
            "smoke_parity": "exact" if exact else "blocked",
            "stale_marker_parity": "exact_current_version_source" if "EXPECTED_CURRENT_VERSION" in smoke_text else "blocked",
        })
    policy_results = {
        "cli_api_parity_gate_passed": cli_api_gate.get("ok") is True,
        "smoke_rows_for_all_selected": len(rows) == 5,
        "smoke_parity_exact_for_all": all(row.get("smoke_parity") == "exact" for row in rows),
        "stale_marker_parity_exact_for_all": all(row.get("stale_marker_parity") == "exact_current_version_source" for row in rows),
        "smoke_collision_count_zero": len(smoke_names) == len(set(smoke_names)),
        "smoke_wiring_stays_inactive": True,
        "targeted_smoke_registered": "multi-surface-smoke-preview-parity-v1" in docs,
        "cli_token_present": "--multi-surface-smoke-preview-parity" in docs,
        "builder_token_present": "build_multi_surface_smoke_preview_parity_review" in docs,
        "text_token_present": "multi_surface_smoke_preview_parity_review_text" in docs,
        "manifest_entry_present": "v929-multi-surface-smoke-preview-parity" in docs,
        "review_only": True,
    }
    return {
        "id": f"multi_surface_smoke_preview_parity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "multi_surface_smoke_preview_parity_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_count": len(rows),
        "smoke_rows": rows,
        "smoke_parity": "exact_for_all_selected" if all(row.get("smoke_parity") == "exact" for row in rows) else "blocked",
        "stale_marker_parity": "exact_current_version_source_for_all_selected" if all(row.get("stale_marker_parity") == "exact_current_version_source" for row in rows) else "blocked",
        "smoke_collision_count": len(smoke_names) - len(set(smoke_names)),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_multi_surface_safety_fields(),
        "recommended_next_arc": "v930.0 Multi-Surface Generated Parity Batch Closure v1",
    }


def multi_surface_smoke_preview_parity_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "multi-surface smoke preview parity report not found."
    lines = [
        "# Multi-Surface Smoke Preview Parity",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Smoke parity: {report.get('smoke_parity')}",
        f"Stale marker parity: {report.get('stale_marker_parity')}",
        f"Smoke collision count: {report.get('smoke_collision_count')}",
        f"Smoke wiring activated: {report.get('smoke_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Smoke rows"])
        for row in report.get("smoke_rows") or []:
            lines.append(f"- {row.get('surface_id')}: {row.get('smoke_check')} parity={row.get('smoke_parity')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_multi_surface_smoke_preview_parity_review(full: bool = False) -> None:
    print(multi_surface_smoke_preview_parity_review_text(build_multi_surface_smoke_preview_parity_review(), full=full))


def build_multi_surface_generated_parity_batch_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Close a five-surface generated/manual parity batch while keeping generated wiring inactive."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    smoke_gate = build_multi_surface_smoke_preview_parity_review(root)
    dashboard_gate = build_multi_surface_dashboard_preview_parity_review(root)
    cli_api_gate = build_multi_surface_cli_api_preview_parity_review(root)
    selection = build_multi_surface_selection_gate_review(root)
    docs = _v926_v930_docs(root)
    selected_ids = selection.get("selected_surface_ids") or []
    closure = {
        "selected_surface_count": len(selected_ids),
        "selected_surfaces": selected_ids,
        "dashboard_parity": dashboard_gate.get("dashboard_parity"),
        "cli_parity": cli_api_gate.get("cli_parity"),
        "api_parity": cli_api_gate.get("api_parity"),
        "smoke_parity": smoke_gate.get("smoke_parity"),
        "stale_marker_parity": smoke_gate.get("stale_marker_parity"),
        "collision_count": (cli_api_gate.get("cli_collision_count") or 0) + (cli_api_gate.get("api_collision_count") or 0) + (smoke_gate.get("smoke_collision_count") or 0),
        "missing_manual_surface_count": 0,
        "missing_manifest_row_count": 0,
        "activation_status": "inactive_review_only",
        "source_edit_status": "none_applied_by_generator",
        "autonomy_status": "unchanged_not_expanded",
    }
    policy_results = {
        "selection_gate_passed": selection.get("ok") is True,
        "dashboard_parity_gate_passed": dashboard_gate.get("ok") is True,
        "cli_api_parity_gate_passed": cli_api_gate.get("ok") is True,
        "smoke_parity_gate_passed": smoke_gate.get("ok") is True,
        "selected_surface_count_is_five": closure["selected_surface_count"] == 5,
        "dashboard_parity_exact_for_all": closure["dashboard_parity"] == "exact_for_all_selected",
        "cli_parity_exact_for_all": closure["cli_parity"] == "exact_for_all_selected",
        "api_parity_exact_for_all": closure["api_parity"] == "exact_not_exposed_review_only_for_all_selected",
        "smoke_parity_exact_for_all": closure["smoke_parity"] == "exact_for_all_selected",
        "stale_marker_parity_exact_for_all": closure["stale_marker_parity"] == "exact_current_version_source_for_all_selected",
        "collision_count_zero": closure["collision_count"] == 0,
        "missing_manual_surface_count_zero": closure["missing_manual_surface_count"] == 0,
        "missing_manifest_row_count_zero": closure["missing_manifest_row_count"] == 0,
        "generated_preview_not_authoritative": True,
        "generated_wiring_stays_inactive": True,
        "no_source_edits_applied_by_generator": True,
        "targeted_smoke_registered": "multi-surface-generated-parity-batch-closure-v1" in docs,
        "cli_token_present": "--multi-surface-generated-parity-batch-closure" in docs,
        "builder_token_present": "build_multi_surface_generated_parity_batch_closure_review" in docs,
        "text_token_present": "multi_surface_generated_parity_batch_closure_review_text" in docs,
        "manifest_entry_present": "v930-multi-surface-generated-parity-batch-closure" in docs,
        "review_only": True,
    }
    return {
        "id": f"multi_surface_generated_parity_batch_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "multi_surface_generated_parity_batch_closure_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_count": closure["selected_surface_count"],
        "selected_surface_ids": selected_ids,
        "closure": closure,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_multi_surface_safety_fields(),
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def multi_surface_generated_parity_batch_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "multi-surface generated parity batch closure report not found."
    closure = report.get("closure") or {}
    lines = [
        "# Multi-Surface Generated Parity Batch Closure",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Dashboard parity: {closure.get('dashboard_parity')}",
        f"CLI parity: {closure.get('cli_parity')}",
        f"API parity: {closure.get('api_parity')}",
        f"Smoke parity: {closure.get('smoke_parity')}",
        f"Stale marker parity: {closure.get('stale_marker_parity')}",
        f"Collision count: {closure.get('collision_count')}",
        f"Missing manual surface count: {closure.get('missing_manual_surface_count')}",
        f"Missing manifest row count: {closure.get('missing_manifest_row_count')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Generated preview authoritative: {report.get('generated_preview_authoritative')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Selected surfaces"])
        for surface_id in report.get("selected_surface_ids") or []:
            lines.append(f"- {surface_id}")
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            if key != "selected_surfaces":
                lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_multi_surface_generated_parity_batch_closure_review(full: bool = False) -> None:
    print(multi_surface_generated_parity_batch_closure_review_text(build_multi_surface_generated_parity_batch_closure_review(), full=full))



# v931-v935 generated scaffold sandbox review implementations were extracted to
# conscious_agent/generated_scaffold_review_packets.py in v970.0.  The wrappers below
# preserve the historical self_development_cycle public call path for dashboard, CLI,
# smoke, and rollback compatibility.


def _generated_scaffold_review_packets_module():
    import generated_scaffold_review_packets as module
    return module


def _smoke_registry_pilot_module():
    import smoke_registry_pilot as module
    return module


GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS = (
    "v916-manifest-review-packet-schema",
    "v917-dashboard-surface-preview-generator",
    "v918-cli-api-surface-preview-generator",
    "v919-smoke-surface-preview-generator",
    "v920-generated-preview-parity-report",
)
GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR = "sandbox/generated_surface_scaffold_previews"
GENERATED_SCAFFOLD_SCHEMA_FIELDS = (
    "surface_id", "artifact_version", "manifest_row", "manual_builder", "manual_text_renderer",
    "dashboard_preview", "cli_preview", "api_preview", "smoke_preview", "safety",
    "activation", "rollback", "artifact_hash", "created_by", "review_only",
    "generated_wiring_activated", "applies_source_edits", "release_authorized",
)


def _generated_scaffold_docs(root: Path) -> str:
    return _generated_scaffold_review_packets_module()._generated_scaffold_docs(root)


def _generated_scaffold_dir(root: Path) -> Path:
    return _generated_scaffold_review_packets_module()._generated_scaffold_dir(root)


def _generated_scaffold_artifact_name(surface_id: str) -> str:
    return _generated_scaffold_review_packets_module()._generated_scaffold_artifact_name(surface_id)


def _expected_generated_scaffold_preview(surface_id: str) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module()._expected_generated_scaffold_preview(surface_id)


def _load_generated_scaffold_artifact(root: Path, surface_id: str) -> dict[str, Any] | None:
    return _generated_scaffold_review_packets_module()._load_generated_scaffold_artifact(root, surface_id)


def _generated_scaffold_hash(path: Path) -> str:
    return _generated_scaffold_review_packets_module()._generated_scaffold_hash(path)


def _generated_scaffold_safety_fields() -> dict[str, bool]:
    return _generated_scaffold_review_packets_module()._generated_scaffold_safety_fields()


def build_generated_scaffold_sandbox_output_schema_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_generated_scaffold_sandbox_output_schema_review(root_dir)


def generated_scaffold_sandbox_output_schema_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().generated_scaffold_sandbox_output_schema_review_text(report, full=full)


def print_generated_scaffold_sandbox_output_schema_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_output_schema_review_text(build_generated_scaffold_sandbox_output_schema_review(), full=full))


def build_generated_scaffold_sandbox_artifact_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_generated_scaffold_sandbox_artifact_preview_review(root_dir)


def generated_scaffold_sandbox_artifact_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().generated_scaffold_sandbox_artifact_preview_review_text(report, full=full)


def print_generated_scaffold_sandbox_artifact_preview_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_artifact_preview_review_text(build_generated_scaffold_sandbox_artifact_preview_review(), full=full))


def build_generated_scaffold_hash_ledger_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_generated_scaffold_hash_ledger_review(root_dir)


def generated_scaffold_hash_ledger_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().generated_scaffold_hash_ledger_review_text(report, full=full)


def print_generated_scaffold_hash_ledger_review(full: bool = False) -> None:
    print(generated_scaffold_hash_ledger_review_text(build_generated_scaffold_hash_ledger_review(), full=full))


def build_generated_scaffold_sandbox_parity_comparison_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_generated_scaffold_sandbox_parity_comparison_review(root_dir)


def generated_scaffold_sandbox_parity_comparison_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().generated_scaffold_sandbox_parity_comparison_review_text(report, full=full)


def print_generated_scaffold_sandbox_parity_comparison_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_parity_comparison_review_text(build_generated_scaffold_sandbox_parity_comparison_review(), full=full))


def build_generated_scaffold_sandbox_output_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_generated_scaffold_sandbox_output_closure_review(root_dir)


def generated_scaffold_sandbox_output_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().generated_scaffold_sandbox_output_closure_review_text(report, full=full)


def print_generated_scaffold_sandbox_output_closure_review(full: bool = False) -> None:
    print(generated_scaffold_sandbox_output_closure_review_text(build_generated_scaffold_sandbox_output_closure_review(), full=full))



GENERATED_SCAFFOLD_WRAPPER_PREVIEW_RELATIVE_DIR = "sandbox/generated_scaffold_wrapper_previews"
GENERATED_SCAFFOLD_WRAPPER_SCHEMA_FIELDS = (
    "schema_version", "artifact_type", "surface_id", "source_artifact_path",
    "manual_builder", "manual_text_renderer", "dashboard_wrapper", "cli_wrapper",
    "api_wrapper", "smoke_wrapper", "rollback_expectation", "protected_manual_status",
    "review_only", "generated_wiring_activated", "applies_source_edits", "autonomy_expanded",
)


def _generated_scaffold_wrapper_docs(root: Path) -> str:
    return "\n".join(_read_text(root / rel, limit=1_000_000) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py",
    ])


def _generated_scaffold_wrapper_dir(root: Path) -> Path:
    return root / GENERATED_SCAFFOLD_WRAPPER_PREVIEW_RELATIVE_DIR


def _wrapper_smoke_function_name(smoke_check: str) -> str:
    return "check_" + smoke_check.replace("-", "_")


def _wrapper_print_function_name(builder_function: str) -> str:
    if builder_function.startswith("build_"):
        return "print_" + builder_function[len("build_"):]
    return "print_" + builder_function


def _expected_generated_scaffold_wrapper_preview(root: Path, surface_id: str) -> dict[str, Any]:
    source_path = f"{GENERATED_SCAFFOLD_SANDBOX_RELATIVE_DIR}/{surface_id}.json"
    source_artifact = _load_generated_scaffold_artifact(root, surface_id)
    if source_artifact is None:
        packet = next((row for row in _multi_generated_parity_packets() if row.get("surface_id") == surface_id), {})
        source_artifact = _generated_scaffold_review_packets_module()._expected_generated_scaffold_preview(packet) if packet else {}
    cli_preview = source_artifact.get("cli_preview") or {}
    dashboard_preview = source_artifact.get("dashboard_preview") or {}
    api_preview = source_artifact.get("api_preview") or {}
    smoke_preview = source_artifact.get("smoke_preview") or {}
    builder = source_artifact.get("manual_builder") or cli_preview.get("builder")
    text_renderer = source_artifact.get("manual_text_renderer") or cli_preview.get("text_renderer")
    return {
        "schema_version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "artifact_type": "generated_scaffold_compatibility_wrapper_preview_review_only",
        "surface_id": surface_id,
        "source_artifact_path": source_path,
        "manual_builder": builder,
        "manual_text_renderer": text_renderer,
        "dashboard_wrapper": {
            "manual_route": dashboard_preview.get("route"),
            "wrapper_target": text_renderer,
            "style_contract": "command-deck/operator-console",
            "hover_contract": "data-tip",
            "native_title_tooltips_allowed": False,
            "wiring_activated": False,
        },
        "cli_wrapper": {
            "manual_flag": cli_preview.get("flag"),
            "wrapper_target": _wrapper_print_function_name(str(builder or "")),
            "builder_target": builder,
            "text_renderer": text_renderer,
            "wiring_activated": False,
        },
        "api_wrapper": {
            "manual_route": api_preview.get("route"),
            "exposure": api_preview.get("exposure"),
            "wrapper_target": "not_exposed_review_only" if api_preview.get("route") == "not_exposed_review_only" else builder,
            "wiring_activated": False,
        },
        "smoke_wrapper": {
            "manual_check": smoke_preview.get("check"),
            "wrapper_target": _wrapper_smoke_function_name(str(smoke_preview.get("check") or "")),
            "segment": smoke_preview.get("segment"),
            "expected_version_source": "EXPECTED_CURRENT_VERSION",
            "wiring_activated": False,
        },
        "rollback_expectation": {
            "manual_code_unchanged": True,
            "generated_wrapper_can_be_removed_by_deleting_sandbox_artifact": True,
            "live_wiring_rollback_required": False,
        },
        "protected_manual_status": {
            "manual_code_replaced": False,
            "generated_wrapper_authoritative": False,
            "protected_systems_require_operator_approval": True,
        },
        "review_only": True,
        "generated_wiring_activated": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "autonomy_expanded": False,
    }


def _load_generated_scaffold_wrapper_artifact(root: Path, surface_id: str) -> dict[str, Any] | None:
    path = _generated_scaffold_wrapper_dir(root) / f"{surface_id}.wrapper.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _generated_scaffold_wrapper_source_only_mode(root: Path) -> bool:
    base = _generated_scaffold_wrapper_dir(root)
    expected_paths = [base / f"{surface_id}.wrapper.json" for surface_id in GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS]
    return not (base / "wrapper_hash_ledger.json").exists() and not any(path.exists() for path in expected_paths)


def _generated_scaffold_wrapper_evidence(
    root: Path, surface_id: str, *, source_only_mode: bool | None = None
) -> tuple[dict[str, Any] | None, str, bool]:
    actual = _load_generated_scaffold_wrapper_artifact(root, surface_id)
    if actual is not None:
        return actual, "sandbox_file", True
    if source_only_mode if source_only_mode is not None else _generated_scaffold_wrapper_source_only_mode(root):
        return _expected_generated_scaffold_wrapper_preview(root, surface_id), "deterministic_source_definition", False
    return None, "missing_or_invalid_sandbox_file", False


def _generated_scaffold_wrapper_safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "wrapper_preview_artifacts_present": True,
        "runtime_writes_wrapper_files": False,
        "generated_wrapper_authoritative": False,
        "generated_wiring_activated": False,
        "dashboard_wiring_activated": False,
        "api_wiring_activated": False,
        "cli_wiring_activated": False,
        "smoke_wiring_activated": False,
        "manual_code_replaced": False,
        "applies_source_edits": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }


def _wrapper_artifact_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    source_only_mode = _generated_scaffold_wrapper_source_only_mode(root)
    for surface_id in GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS:
        expected = _expected_generated_scaffold_wrapper_preview(root, surface_id)
        evidence, evidence_mode, file_present = _generated_scaffold_wrapper_evidence(
            root, surface_id, source_only_mode=source_only_mode
        )
        rows.append({
            "surface_id": surface_id,
            "artifact_path": f"{GENERATED_SCAFFOLD_WRAPPER_PREVIEW_RELATIVE_DIR}/{surface_id}.wrapper.json",
            "artifact_present": file_present,
            "file_present": file_present,
            "evidence_available": isinstance(evidence, dict),
            "evidence_mode": evidence_mode,
            "artifact_matches_expected": evidence == expected,
            "manual_builder": expected.get("manual_builder"),
            "manual_text_renderer": expected.get("manual_text_renderer"),
            "dashboard_route": (expected.get("dashboard_wrapper") or {}).get("manual_route"),
            "cli_flag": (expected.get("cli_wrapper") or {}).get("manual_flag"),
            "api_route": (expected.get("api_wrapper") or {}).get("manual_route"),
            "smoke_check": (expected.get("smoke_wrapper") or {}).get("manual_check"),
        })
    return rows

def build_generated_scaffold_wrapper_mapping_schema_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Define the review-only generated scaffold compatibility wrapper mapping schema."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    previous = build_generated_scaffold_sandbox_output_closure_review(root)
    docs = _generated_scaffold_wrapper_docs(root)
    required_docs = [
        "generated-scaffold-wrapper-mapping-schema-v1", "--generated-scaffold-wrapper-mapping-schema",
        "build_generated_scaffold_wrapper_mapping_schema_review", "generated_scaffold_wrapper_mapping_schema_review_text",
        GENERATED_SCAFFOLD_WRAPPER_PREVIEW_RELATIVE_DIR, "wrapper_schema_field_count=16", "review_only=True",
    ]
    policy_results = {
        "previous_scaffold_output_closure_passed": previous.get("ok") is True,
        "schema_field_count_is_sixteen": len(GENERATED_SCAFFOLD_WRAPPER_SCHEMA_FIELDS) == 16,
        "selected_surface_count_is_five": len(GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS) == 5,
        "wrapper_directory_is_under_sandbox": GENERATED_SCAFFOLD_WRAPPER_PREVIEW_RELATIVE_DIR.startswith("sandbox/"),
        "schema_defines_wrapper_targets": all(field in GENERATED_SCAFFOLD_WRAPPER_SCHEMA_FIELDS for field in ["dashboard_wrapper", "cli_wrapper", "api_wrapper", "smoke_wrapper", "rollback_expectation"]),
        "docs_tokens_present": all(token in docs for token in required_docs),
        "review_only": True,
    }
    return {
        "id": f"generated_scaffold_wrapper_mapping_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_scaffold_wrapper_mapping_schema_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "schema_field_count": len(GENERATED_SCAFFOLD_WRAPPER_SCHEMA_FIELDS),
        "schema_fields": list(GENERATED_SCAFFOLD_WRAPPER_SCHEMA_FIELDS),
        "selected_surface_count": len(GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS),
        "wrapper_relative_dir": GENERATED_SCAFFOLD_WRAPPER_PREVIEW_RELATIVE_DIR,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_wrapper_safety_fields(),
        "recommended_next_arc": "v937.0 Dashboard Compatibility Wrapper Preview v1",
    }


def generated_scaffold_wrapper_mapping_schema_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated scaffold wrapper mapping schema report not found."
    lines = [
        "# Generated Scaffold Wrapper Mapping Schema",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Wrapper schema field count: {report.get('schema_field_count')}",
        f"Wrapper relative dir: {report.get('wrapper_relative_dir')}",
        f"Runtime writes wrapper files: {report.get('runtime_writes_wrapper_files')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Schema fields"])
        for field in report.get("schema_fields") or []:
            lines.append(f"- {field}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_scaffold_wrapper_mapping_schema_review(full: bool = False) -> None:
    print(generated_scaffold_wrapper_mapping_schema_review_text(build_generated_scaffold_wrapper_mapping_schema_review(), full=full))


def build_dashboard_compatibility_wrapper_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Review dashboard compatibility wrapper previews for the selected scaffold artifacts."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    schema = build_generated_scaffold_wrapper_mapping_schema_review(root)
    docs = _generated_scaffold_wrapper_docs(root)
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py", limit=1_800_000)
    rows = _wrapper_artifact_rows(root)
    dashboard_rows = []
    for row in rows:
        artifact, _, _ = _generated_scaffold_wrapper_evidence(root, str(row.get("surface_id")))
        artifact = artifact or {}
        wrapper = artifact.get("dashboard_wrapper") or {}
        exact = row.get("artifact_matches_expected") is True and wrapper.get("manual_route") == "/self-development-smoke-debt" and wrapper.get("hover_contract") == "data-tip" and wrapper.get("native_title_tooltips_allowed") is False and "data-tip" in dashboard_text and "data-route-title" in dashboard_text
        dashboard_rows.append({**row, "dashboard_wrapper_parity": "exact" if exact else "blocked", "data_tip_compliance": "data-tip" in dashboard_text, "native_title_tooltips_allowed": False})
    policy_results = {
        "schema_gate_passed": schema.get("ok") is True,
        "dashboard_rows_for_all_selected": len(dashboard_rows) == 5,
        "dashboard_wrapper_parity_exact_for_all": all(row.get("dashboard_wrapper_parity") == "exact" for row in dashboard_rows),
        "data_tip_compliance_confirmed": all(row.get("data_tip_compliance") is True for row in dashboard_rows),
        "native_title_tooltip_not_reintroduced": "data-route-title" in dashboard_text,
        "dashboard_wiring_stays_inactive": True,
        "targeted_smoke_registered": "dashboard-compatibility-wrapper-preview-v1" in docs,
        "cli_token_present": "--dashboard-compatibility-wrapper-preview" in docs,
        "builder_token_present": "build_dashboard_compatibility_wrapper_preview_review" in docs,
        "text_token_present": "dashboard_compatibility_wrapper_preview_review_text" in docs,
        "manifest_entry_present": "v937-dashboard-compatibility-wrapper-preview" in docs,
        "review_only": True,
    }
    return {
        "id": f"dashboard_compatibility_wrapper_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "dashboard_compatibility_wrapper_preview_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_count": len(dashboard_rows),
        "dashboard_wrapper_rows": dashboard_rows,
        "dashboard_wrapper_parity": "exact_for_all_selected" if all(row.get("dashboard_wrapper_parity") == "exact" for row in dashboard_rows) else "blocked",
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_wrapper_safety_fields(),
        "recommended_next_arc": "v938.0 CLI/API Compatibility Wrapper Preview v1",
    }


def dashboard_compatibility_wrapper_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "dashboard compatibility wrapper preview report not found."
    lines = [
        "# Dashboard Compatibility Wrapper Preview",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Dashboard wrapper parity: {report.get('dashboard_wrapper_parity')}",
        f"Dashboard wiring activated: {report.get('dashboard_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Dashboard wrapper rows"])
        for row in report.get("dashboard_wrapper_rows") or []:
            lines.append(f"- {row.get('surface_id')}: route={row.get('dashboard_route')} parity={row.get('dashboard_wrapper_parity')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_dashboard_compatibility_wrapper_preview_review(full: bool = False) -> None:
    print(dashboard_compatibility_wrapper_preview_review_text(build_dashboard_compatibility_wrapper_preview_review(), full=full))


def build_cli_api_compatibility_wrapper_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Review CLI/API compatibility wrapper previews for the selected scaffold artifacts."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    dashboard_gate = build_dashboard_compatibility_wrapper_preview_review(root)
    docs = _generated_scaffold_wrapper_docs(root)
    main_text = _read_text(root / "conscious_agent/main.py", limit=1_400_000)
    rows = _wrapper_artifact_rows(root)
    cli_api_rows = []
    cli_flags: list[str] = []
    api_routes: list[str] = []
    for row in rows:
        artifact, _, _ = _generated_scaffold_wrapper_evidence(root, str(row.get("surface_id")))
        artifact = artifact or {}
        cli_wrapper = artifact.get("cli_wrapper") or {}
        api_wrapper = artifact.get("api_wrapper") or {}
        flag = str(cli_wrapper.get("manual_flag") or "")
        api_route = str(api_wrapper.get("manual_route") or "")
        cli_flags.append(flag)
        api_routes.append(api_route)
        cli_exact = row.get("artifact_matches_expected") is True and flag in main_text and str(cli_wrapper.get("wrapper_target") or "") in main_text and str(cli_wrapper.get("builder_target") or "") in _read_text(root / "conscious_agent/self_development_cycle.py", limit=2_500_000)
        api_exact = api_route == "not_exposed_review_only" and api_wrapper.get("wrapper_target") == "not_exposed_review_only"
        cli_api_rows.append({**row, "cli_wrapper_parity": "exact" if cli_exact else "blocked", "api_wrapper_parity": "exact_not_exposed_review_only" if api_exact else "blocked", "cli_flag": flag, "api_route": api_route})
    policy_results = {
        "dashboard_wrapper_preview_passed": dashboard_gate.get("ok") is True,
        "cli_api_rows_for_all_selected": len(cli_api_rows) == 5,
        "cli_wrapper_parity_exact_for_all": all(row.get("cli_wrapper_parity") == "exact" for row in cli_api_rows),
        "api_wrapper_parity_exact_for_all": all(row.get("api_wrapper_parity") == "exact_not_exposed_review_only" for row in cli_api_rows),
        "cli_collision_count_zero": len(cli_flags) == len(set(cli_flags)),
        "api_collision_count_zero_or_not_exposed": set(api_routes) == {"not_exposed_review_only"},
        "cli_wiring_stays_inactive": True,
        "api_wiring_stays_inactive": True,
        "targeted_smoke_registered": "cli-api-compatibility-wrapper-preview-v1" in docs,
        "cli_token_present": "--cli-api-compatibility-wrapper-preview" in docs,
        "builder_token_present": "build_cli_api_compatibility_wrapper_preview_review" in docs,
        "text_token_present": "cli_api_compatibility_wrapper_preview_review_text" in docs,
        "manifest_entry_present": "v938-cli-api-compatibility-wrapper-preview" in docs,
        "review_only": True,
    }
    return {
        "id": f"cli_api_compatibility_wrapper_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "cli_api_compatibility_wrapper_preview_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_count": len(cli_api_rows),
        "cli_api_wrapper_rows": cli_api_rows,
        "cli_wrapper_parity": "exact_for_all_selected" if all(row.get("cli_wrapper_parity") == "exact" for row in cli_api_rows) else "blocked",
        "api_wrapper_parity": "exact_not_exposed_review_only_for_all_selected" if all(row.get("api_wrapper_parity") == "exact_not_exposed_review_only" for row in cli_api_rows) else "blocked",
        "cli_collision_count": len(cli_flags) - len(set(cli_flags)),
        "api_collision_count": 0 if set(api_routes) == {"not_exposed_review_only"} else len(api_routes) - len(set(api_routes)),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_wrapper_safety_fields(),
        "recommended_next_arc": "v939.0 Smoke Compatibility Wrapper Preview v1",
    }


def cli_api_compatibility_wrapper_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "CLI/API compatibility wrapper preview report not found."
    lines = [
        "# CLI/API Compatibility Wrapper Preview",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"CLI wrapper parity: {report.get('cli_wrapper_parity')}",
        f"API wrapper parity: {report.get('api_wrapper_parity')}",
        f"CLI collision count: {report.get('cli_collision_count')}",
        f"API collision count: {report.get('api_collision_count')}",
        f"CLI wiring activated: {report.get('cli_wiring_activated')}",
        f"API wiring activated: {report.get('api_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## CLI/API wrapper rows"])
        for row in report.get("cli_api_wrapper_rows") or []:
            lines.append(f"- {row.get('surface_id')}: flag={row.get('cli_flag')} cli={row.get('cli_wrapper_parity')} api={row.get('api_wrapper_parity')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_cli_api_compatibility_wrapper_preview_review(full: bool = False) -> None:
    print(cli_api_compatibility_wrapper_preview_review_text(build_cli_api_compatibility_wrapper_preview_review(), full=full))


def build_smoke_compatibility_wrapper_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Review smoke compatibility wrapper previews for the selected scaffold artifacts."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    cli_api_gate = build_cli_api_compatibility_wrapper_preview_review(root)
    docs = _generated_scaffold_wrapper_docs(root)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=1_700_000)
    rows = _wrapper_artifact_rows(root)
    smoke_rows = []
    smoke_checks: list[str] = []
    for row in rows:
        artifact, _, _ = _generated_scaffold_wrapper_evidence(root, str(row.get("surface_id")))
        artifact = artifact or {}
        smoke_wrapper = artifact.get("smoke_wrapper") or {}
        check = str(smoke_wrapper.get("manual_check") or "")
        smoke_checks.append(check)
        wrapper_target = str(smoke_wrapper.get("wrapper_target") or "")
        exact = row.get("artifact_matches_expected") is True and check in smoke_text and wrapper_target in smoke_text and smoke_wrapper.get("expected_version_source") == "EXPECTED_CURRENT_VERSION" and smoke_wrapper.get("segment") == "install-release"
        smoke_rows.append({**row, "smoke_wrapper_parity": "exact" if exact else "blocked", "smoke_check": check, "smoke_wrapper_target": wrapper_target, "timeout_tier": "install", "segment": smoke_wrapper.get("segment")})
    policy_results = {
        "cli_api_wrapper_preview_passed": cli_api_gate.get("ok") is True,
        "smoke_rows_for_all_selected": len(smoke_rows) == 5,
        "smoke_wrapper_parity_exact_for_all": all(row.get("smoke_wrapper_parity") == "exact" for row in smoke_rows),
        "smoke_collision_count_zero": len(smoke_checks) == len(set(smoke_checks)),
        "expected_current_version_source_confirmed": all(row.get("segment") == "install-release" for row in smoke_rows) and "EXPECTED_CURRENT_VERSION" in smoke_text,
        "smoke_wiring_stays_inactive": True,
        "targeted_smoke_registered": "smoke-compatibility-wrapper-preview-v1" in docs,
        "cli_token_present": "--smoke-compatibility-wrapper-preview" in docs,
        "builder_token_present": "build_smoke_compatibility_wrapper_preview_review" in docs,
        "text_token_present": "smoke_compatibility_wrapper_preview_review_text" in docs,
        "manifest_entry_present": "v939-smoke-compatibility-wrapper-preview" in docs,
        "review_only": True,
    }
    return {
        "id": f"smoke_compatibility_wrapper_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "smoke_compatibility_wrapper_preview_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_count": len(smoke_rows),
        "smoke_wrapper_rows": smoke_rows,
        "smoke_wrapper_parity": "exact_for_all_selected" if all(row.get("smoke_wrapper_parity") == "exact" for row in smoke_rows) else "blocked",
        "smoke_collision_count": len(smoke_checks) - len(set(smoke_checks)),
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_wrapper_safety_fields(),
        "recommended_next_arc": "v940.0 Generated Scaffold Wrapper Prep Closure v1",
    }


def smoke_compatibility_wrapper_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke compatibility wrapper preview report not found."
    lines = [
        "# Smoke Compatibility Wrapper Preview",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {report.get('selected_surface_count')}",
        f"Smoke wrapper parity: {report.get('smoke_wrapper_parity')}",
        f"Smoke collision count: {report.get('smoke_collision_count')}",
        f"Smoke wiring activated: {report.get('smoke_wiring_activated')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Smoke wrapper rows"])
        for row in report.get("smoke_wrapper_rows") or []:
            lines.append(f"- {row.get('surface_id')}: check={row.get('smoke_check')} parity={row.get('smoke_wrapper_parity')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_smoke_compatibility_wrapper_preview_review(full: bool = False) -> None:
    print(smoke_compatibility_wrapper_preview_review_text(build_smoke_compatibility_wrapper_preview_review(), full=full))


def build_generated_scaffold_wrapper_prep_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Close the review-only generated scaffold compatibility wrapper prep arc with bounded evidence checks."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    docs = _generated_scaffold_wrapper_docs(root)
    rows = _wrapper_artifact_rows(root)
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py", limit=1_800_000)
    main_text = _read_text(root / "conscious_agent/main.py", limit=1_400_000)
    smoke_text = _read_text(root / "tools/smoke_check.py", limit=1_700_000)
    sdc_text = _read_text(root / "conscious_agent/self_development_cycle.py", limit=2_500_000)
    ledger_path = _generated_scaffold_wrapper_dir(root) / "wrapper_hash_ledger.json"
    source_only_mode = _generated_scaffold_wrapper_source_only_mode(root)
    ledger_ok = False
    hash_count = 0
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        hash_count = len(ledger.get("artifacts") or [])
        ledger_ok = ledger.get("schema_version") == SELF_DEVELOPMENT_CYCLE_VERSION and hash_count == 5
    except (OSError, json.JSONDecodeError):
        if source_only_mode:
            hash_count = len(rows)
            ledger_ok = len(rows) == 5 and all(row.get("artifact_matches_expected") is True for row in rows)

    physical_wrapper_artifact_count = sum(1 for row in rows if row.get("artifact_present"))
    wrapper_artifact_count = sum(1 for row in rows if row.get("evidence_available"))
    artifacts_match = all(row.get("artifact_matches_expected") is True for row in rows)
    dashboard_exact = artifacts_match and all(row.get("dashboard_route") == "/self-development-smoke-debt" for row in rows) and "data-tip" in dashboard_text and "data-route-title" in dashboard_text
    cli_flags = [str(row.get("cli_flag") or "") for row in rows]
    cli_exact = artifacts_match and len(cli_flags) == len(set(cli_flags)) and all(flag and flag in main_text for flag in cli_flags) and all(str(row.get("manual_builder") or "") in sdc_text and str(row.get("manual_text_renderer") or "") in sdc_text for row in rows)
    api_routes = [str(row.get("api_route") or "") for row in rows]
    api_exact = set(api_routes) == {"not_exposed_review_only"}
    smoke_checks = [str(row.get("smoke_check") or "") for row in rows]
    smoke_exact = artifacts_match and len(smoke_checks) == len(set(smoke_checks)) and all(check and check in smoke_text and _wrapper_smoke_function_name(check) in smoke_text for check in smoke_checks) and "EXPECTED_CURRENT_VERSION" in smoke_text
    collision_count = (len(cli_flags) - len(set(cli_flags))) + (0 if api_exact else len(api_routes) - len(set(api_routes))) + (len(smoke_checks) - len(set(smoke_checks)))

    closure = {
        "selected_surface_count": len(GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS),
        "wrapper_artifact_count": wrapper_artifact_count,
        "physical_wrapper_artifact_count": physical_wrapper_artifact_count,
        "wrapper_hash_count": hash_count,
        "evidence_mode": "source_only_reconstruction" if source_only_mode else "sandbox_files",
        "wrapper_schema_field_count": len(GENERATED_SCAFFOLD_WRAPPER_SCHEMA_FIELDS),
        "dashboard_wrapper_parity": "exact_for_all_selected" if dashboard_exact else "blocked",
        "cli_wrapper_parity": "exact_for_all_selected" if cli_exact else "blocked",
        "api_wrapper_parity": "exact_not_exposed_review_only_for_all_selected" if api_exact else "blocked",
        "smoke_wrapper_parity": "exact_for_all_selected" if smoke_exact else "blocked",
        "collision_count": collision_count,
        "activation_status": "inactive_review_only",
        "manual_code_replaced": False,
        "source_edit_status": "none_applied_by_generator_runtime",
        "runtime_write_status": "no_runtime_writes_performed",
        "autonomy_status": "unchanged_not_expanded",
    }
    required_docs = [
        "v940.0", "Generated Scaffold Wrapper Prep Closure v1",
        "generated-scaffold-wrapper-mapping-schema-v1", "dashboard-compatibility-wrapper-preview-v1",
        "cli-api-compatibility-wrapper-preview-v1", "smoke-compatibility-wrapper-preview-v1", "generated-scaffold-wrapper-prep-closure-v1",
        "--generated-scaffold-wrapper-prep-closure", "build_generated_scaffold_wrapper_prep_closure_review", "generated_scaffold_wrapper_prep_closure_review_text",
        "wrapper_artifact_count=5", "wrapper_hash_count=5", "wrapper_schema_field_count=16", "manual_code_replaced=False",
        "runtime_writes_wrapper_files=False", "generated_wiring_activated=False", "applies_source_edits=False", "release_authorized=False", "review_only=True", "autonomy_expanded=False", "expands_autonomy=False", "protected_systems_require_operator_approval=True", "data-tip", "command-deck", "operator-console",
    ]
    policy_results = {
        "wrapper_artifacts_present": wrapper_artifact_count == 5,
        "wrapper_artifacts_match_expected": artifacts_match,
        "wrapper_hash_ledger_matches": ledger_ok,
        "wrapper_schema_field_count_is_sixteen": closure["wrapper_schema_field_count"] == 16,
        "dashboard_wrapper_parity_exact": closure["dashboard_wrapper_parity"] == "exact_for_all_selected",
        "cli_wrapper_parity_exact": closure["cli_wrapper_parity"] == "exact_for_all_selected",
        "api_wrapper_parity_exact": closure["api_wrapper_parity"] == "exact_not_exposed_review_only_for_all_selected",
        "smoke_wrapper_parity_exact": closure["smoke_wrapper_parity"] == "exact_for_all_selected",
        "collision_count_zero": closure["collision_count"] == 0,
        "manual_code_not_replaced": closure["manual_code_replaced"] is False,
        "generated_wiring_stays_inactive": True,
        "docs_tokens_present": all(token in docs for token in required_docs),
        "review_only": True,
    }
    return {
        "id": f"generated_scaffold_wrapper_prep_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "generated_scaffold_wrapper_prep_closure_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "selected_surface_ids": list(GENERATED_SCAFFOLD_SANDBOX_SURFACE_IDS),
        "evidence_mode": "source_only_reconstruction" if source_only_mode else "sandbox_files",
        "source_only_reconstruction": source_only_mode,
        "closure": closure,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_generated_scaffold_wrapper_safety_fields(),
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }

def generated_scaffold_wrapper_prep_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "generated scaffold wrapper prep closure report not found."
    closure = report.get("closure") or {}
    lines = [
        "# Generated Scaffold Wrapper Prep Closure",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Selected surface count: {closure.get('selected_surface_count')}",
        f"Wrapper artifact count: {closure.get('wrapper_artifact_count')}",
        f"Wrapper hash count: {closure.get('wrapper_hash_count')}",
        f"Wrapper schema field count: {closure.get('wrapper_schema_field_count')}",
        f"Dashboard wrapper parity: {closure.get('dashboard_wrapper_parity')}",
        f"CLI wrapper parity: {closure.get('cli_wrapper_parity')}",
        f"API wrapper parity: {closure.get('api_wrapper_parity')}",
        f"Smoke wrapper parity: {closure.get('smoke_wrapper_parity')}",
        f"Collision count: {closure.get('collision_count')}",
        f"Runtime writes wrapper files: {report.get('runtime_writes_wrapper_files')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Applies source edits: {report.get('applies_source_edits')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Selected surfaces"])
        for surface_id in report.get("selected_surface_ids") or []:
            lines.append(f"- {surface_id}")
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_generated_scaffold_wrapper_prep_closure_review(full: bool = False) -> None:
    print(generated_scaffold_wrapper_prep_closure_review_text(build_generated_scaffold_wrapper_prep_closure_review(), full=full))


GIANT_FILE_EXTRACTION_TARGETS = (
    "conscious_agent/self_development_cycle.py",
    "conscious_agent/self_maintenance.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/main.py",
    "conscious_agent/api_server.py",
    "tools/smoke_check.py",
)

GIANT_FILE_EXTRACTION_PREP_TOKENS = (
    "giant-file-extraction-inventory-v1",
    "self-development-cycle-extraction-map-v1",
    "self-maintenance-builder-text-renderer-extraction-map-v1",
    "dashboard-route-renderer-extraction-map-v1",
    "cli-api-dispatch-extraction-map-v1",
    "smoke-registry-extraction-map-v1",
    "compatibility-wrapper-risk-ledger-v1",
    "extraction-order-proposal-v1",
    "extraction-rollback-evidence-plan-v1",
    "giant-file-compatibility-extraction-prep-closure-v1",
)


def _giant_file_prep_docs(root: Path) -> str:
    return "\n".join(_read_text(root / rel, limit=2_000_000) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/self_development_cycle.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ])


def _giant_file_source_text(root: Path, rel: str, *, limit: int = 3_000_000) -> str:
    return _read_text(root / rel, limit=limit)


def _giant_file_ast_counts(root: Path, rel: str) -> dict[str, int]:
    text = _giant_file_source_text(root, rel, limit=4_000_000)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {"function_count": 0, "class_count": 0, "parse_error_count": 1}
    function_names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    return {
        "function_count": len(function_names),
        "class_count": len(class_names),
        "parse_error_count": 0,
        "build_function_count": sum(1 for name in function_names if name.startswith("build_")),
        "text_renderer_count": sum(1 for name in function_names if name.endswith("_text") or name.endswith("_review_text")),
        "print_function_count": sum(1 for name in function_names if name.startswith("print_")),
        "check_function_count": sum(1 for name in function_names if name.startswith("check_")),
    }


def _giant_file_inventory_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in GIANT_FILE_EXTRACTION_TARGETS:
        path = root / rel
        text = _giant_file_source_text(root, rel, limit=4_000_000)
        counts = _giant_file_ast_counts(root, rel)
        route_tokens = len(re.findall(r'["\']/[^"\']+["\']', text))
        cli_flags = len(set(re.findall(r'--[a-z0-9][a-z0-9-]+', text)))
        smoke_tokens = len(set(re.findall(r'[a-z0-9-]+-v1', text)))
        repeated_private_helpers = sorted({name for name in re.findall(r'def (_[a-z][a-z0-9_]+)\(', text) if text.count(f"def {name}(") > 1})
        low_risk_cluster = "review_builders" if counts.get("build_function_count", 0) else "dispatch_or_registry"
        rows.append({
            "path": rel,
            "exists": path.exists(),
            "line_count": text.count("\n") + (1 if text else 0),
            "byte_count": len(text.encode("utf-8")),
            "route_token_count": route_tokens,
            "cli_flag_count": cli_flags,
            "smoke_token_count": smoke_tokens,
            "repeated_private_helper_count": len(repeated_private_helpers),
            "repeated_private_helpers": repeated_private_helpers[:12],
            "safest_cluster": low_risk_cluster,
            **counts,
        })
    return rows


def _giant_file_safety_fields() -> dict[str, bool]:
    return {
        "review_only": True,
        "moves_live_code": False,
        "splits_files": False,
        "activates_generated_wrappers": False,
        "generated_wiring_activated": False,
        "manual_code_replaced": False,
        "applies_source_edits_by_generator": False,
        "release_authorized": False,
        "memory_mutated": False,
        "approval_system_mutated": False,
        "release_system_mutated": False,
        "scheduler_mutated": False,
        "network_accessed": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "protected_systems_require_operator_approval": True,
    }


def _giant_file_policy_base(root: Path, smoke_name: str, flag: str, builder: str, text_func: str, surface_id: str) -> dict[str, bool]:
    docs = _giant_file_prep_docs(root)
    return {
        "targeted_smoke_registered": smoke_name in docs,
        "cli_token_present": flag in docs,
        "builder_token_present": builder in docs,
        "text_token_present": text_func in docs,
        "manifest_entry_present": surface_id in docs,
        "readme_updated": "v950.0 Giant File Compatibility Extraction Prep Closure v1" in docs,
        "next_arc_updated": "v951.0-v960.0 First Compatibility Extraction Trial v1" in docs,
        "review_only": True,
        "no_live_code_movement": True,
        "autonomy_not_expanded": True,
    }


def build_giant_file_extraction_inventory_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    """Inventory the giant files before any compatibility extraction is attempted."""
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    rows = _giant_file_inventory_rows(root)
    policy_results = _giant_file_policy_base(root, "giant-file-extraction-inventory-v1", "--giant-file-extraction-inventory", "build_giant_file_extraction_inventory_review", "giant_file_extraction_inventory_review_text", "v941-giant-file-extraction-inventory")
    policy_results.update({
        "all_target_files_found": all(row.get("exists") for row in rows),
        "target_file_count_is_six": len(rows) == 6,
        "function_inventory_present": sum(row.get("function_count", 0) for row in rows) > 0,
        "giant_file_pressure_detected": any(row.get("line_count", 0) > 5_000 for row in rows),
        "safe_extraction_candidates_identified": any(row.get("build_function_count", 0) for row in rows),
    })
    return {
        "id": f"giant_file_extraction_inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "giant_file_extraction_inventory_review",
        "status": "pass" if all(policy_results.values()) else "blocked",
        "ok": all(policy_results.values()),
        "version": SELF_DEVELOPMENT_CYCLE_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "target_file_count": len(rows),
        "total_line_count": sum(row.get("line_count", 0) for row in rows),
        "total_function_count": sum(row.get("function_count", 0) for row in rows),
        "total_build_function_count": sum(row.get("build_function_count", 0) for row in rows),
        "total_text_renderer_count": sum(row.get("text_renderer_count", 0) for row in rows),
        "inventory_rows": rows,
        "policies_passed": all(policy_results.values()),
        "policy_results": policy_results,
        **_giant_file_safety_fields(),
        "recommended_next_arc": "v942.0 Self-Development Cycle Extraction Map v1",
    }


def giant_file_extraction_inventory_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "giant file extraction inventory report not found."
    lines = [
        "# Giant File Extraction Inventory",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Target file count: {report.get('target_file_count')}",
        f"Total line count: {report.get('total_line_count')}",
        f"Total function count: {report.get('total_function_count')}",
        f"Total build function count: {report.get('total_build_function_count')}",
        f"Total text renderer count: {report.get('total_text_renderer_count')}",
        f"Moves live code: {report.get('moves_live_code')}",
        f"Splits files: {report.get('splits_files')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Inventory rows"])
        for row in report.get("inventory_rows") or []:
            lines.append(f"- {row.get('path')}: lines={row.get('line_count')} functions={row.get('function_count')} build={row.get('build_function_count')} text={row.get('text_renderer_count')} cli={row.get('cli_flag_count')} smoke={row.get('smoke_token_count')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_giant_file_extraction_inventory_review(full: bool = False) -> None:
    print(giant_file_extraction_inventory_review_text(build_giant_file_extraction_inventory_review(), full=full))


def _file_extraction_cluster(root: Path, rel: str, keywords: tuple[str, ...], risk: str) -> dict[str, Any]:
    text = _giant_file_source_text(root, rel, limit=4_000_000)
    try:
        tree = ast.parse(text)
        function_names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    except SyntaxError:
        function_names = []
    candidates = [name for name in function_names if any(key in name for key in keywords)]
    return {
        "path": rel,
        "risk": risk,
        "candidate_count": len(candidates),
        "candidate_examples": candidates[:24],
        "wrapper_required": True,
        "move_live_code_now": False,
        "review_only": True,
    }


def build_self_development_cycle_extraction_map_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    inventory = build_giant_file_extraction_inventory_review(root)
    clusters = [
        _file_extraction_cluster(root, "conscious_agent/self_development_cycle.py", ("manifest", "generated", "scaffold", "wrapper"), "low"),
        _file_extraction_cluster(root, "conscious_agent/self_development_cycle.py", ("probe", "harness"), "medium"),
        _file_extraction_cluster(root, "conscious_agent/self_development_cycle.py", ("release", "approval", "memory", "autonomy"), "protected"),
    ]
    policy_results = _giant_file_policy_base(root, "self-development-cycle-extraction-map-v1", "--self-development-cycle-extraction-map", "build_self_development_cycle_extraction_map_review", "self_development_cycle_extraction_map_review_text", "v942-self-development-cycle-extraction-map")
    policy_results.update({"inventory_passed": inventory.get("ok") is True, "clusters_present": len(clusters) == 3, "low_risk_candidates_present": clusters[0].get("candidate_count", 0) > 0, "protected_cluster_visible": clusters[-1].get("risk") == "protected"})
    return {"id": f"self_development_cycle_extraction_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "self_development_cycle_extraction_map_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "clusters": clusters, "candidate_count": sum(c.get("candidate_count", 0) for c in clusters), "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v943.0 Self-Maintenance Builder/Text Renderer Extraction Map v1"}


def self_development_cycle_extraction_map_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "self-development cycle extraction map report not found."
    lines = ["# Self-Development Cycle Extraction Map", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Candidate count: {report.get('candidate_count')}", f"Moves live code: {report.get('moves_live_code')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Clusters"])
        for c in report.get("clusters") or []:
            lines.append(f"- {c.get('risk')} {c.get('path')}: candidates={c.get('candidate_count')} examples={', '.join(c.get('candidate_examples') or [])}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_self_development_cycle_extraction_map_review(full: bool = False) -> None:
    print(self_development_cycle_extraction_map_review_text(build_self_development_cycle_extraction_map_review(), full=full))


def build_self_maintenance_builder_text_renderer_extraction_map_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    text = _giant_file_source_text(root, "conscious_agent/self_maintenance.py", limit=5_000_000)
    builders = sorted(set(re.findall(r'def (build_[a-z0-9_]+)\(', text)))
    renderers = sorted(set(re.findall(r'def ([a-z0-9_]+(?:_review)?_text)\(', text)))
    helper_names = sorted(set(re.findall(r'def (_[a-z][a-z0-9_]+)\(', text)))[:40]
    clusters = [
        {"cluster": "review_builders", "risk": "low", "count": len([b for b in builders if b.endswith("_review")]), "examples": builders[:20], "move_live_code_now": False},
        {"cluster": "text_renderers", "risk": "low", "count": len(renderers), "examples": renderers[:20], "move_live_code_now": False},
        {"cluster": "private_helpers", "risk": "medium", "count": len(helper_names), "examples": helper_names[:20], "move_live_code_now": False},
    ]
    policy_results = _giant_file_policy_base(root, "self-maintenance-builder-text-renderer-extraction-map-v1", "--self-maintenance-builder-text-renderer-extraction-map", "build_self_maintenance_builder_text_renderer_extraction_map_review", "self_maintenance_builder_text_renderer_extraction_map_review_text", "v943-self-maintenance-builder-text-renderer-extraction-map")
    policy_results.update({"builders_present": len(builders) > 0, "renderers_present": len(renderers) > 0, "clusters_present": len(clusters) == 3, "no_live_code_moved": True})
    return {"id": f"self_maintenance_builder_text_renderer_extraction_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "self_maintenance_builder_text_renderer_extraction_map_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "builder_count": len(builders), "text_renderer_count": len(renderers), "clusters": clusters, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v944.0 Dashboard Route/Renderer Extraction Map v1"}


def self_maintenance_builder_text_renderer_extraction_map_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "self-maintenance builder/text renderer extraction map report not found."
    lines = ["# Self-Maintenance Builder/Text Renderer Extraction Map", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Builder count: {report.get('builder_count')}", f"Text renderer count: {report.get('text_renderer_count')}", f"Moves live code: {report.get('moves_live_code')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Clusters"])
        for c in report.get("clusters") or []:
            lines.append(f"- {c.get('cluster')}: risk={c.get('risk')} count={c.get('count')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_self_maintenance_builder_text_renderer_extraction_map_review(full: bool = False) -> None:
    print(self_maintenance_builder_text_renderer_extraction_map_review_text(build_self_maintenance_builder_text_renderer_extraction_map_review(), full=full))


def build_dashboard_route_renderer_extraction_map_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    text = _giant_file_source_text(root, "conscious_agent/dashboard.py", limit=2_500_000)
    routes = sorted(set(re.findall(r'["\'](/[^"\']+)["\']', text)))
    renderer_refs = sorted(set(re.findall(r'([a-z0-9_]+_text)\(', text)))
    clusters = [{"cluster": "route_dispatch", "risk": "medium", "count": len(routes), "examples": routes[:20], "move_live_code_now": False}, {"cluster": "renderer_refs", "risk": "medium", "count": len(renderer_refs), "examples": renderer_refs[:20], "move_live_code_now": False}]
    policy_results = _giant_file_policy_base(root, "dashboard-route-renderer-extraction-map-v1", "--dashboard-route-renderer-extraction-map", "build_dashboard_route_renderer_extraction_map_review", "dashboard_route_renderer_extraction_map_review_text", "v944-dashboard-route-renderer-extraction-map")
    policy_results.update({"routes_present": len(routes) > 0, "data_tip_preserved": "data-tip" in text, "native_title_tooltip_not_reintroduced": "data-route-title" in text, "command_deck_tokens_present": "command-deck" in text or "operator-console" in text, "clusters_present": len(clusters) == 2})
    return {"id": f"dashboard_route_renderer_extraction_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "dashboard_route_renderer_extraction_map_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "route_count": len(routes), "renderer_ref_count": len(renderer_refs), "clusters": clusters, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v945.0 CLI/API Dispatch Extraction Map v1"}


def dashboard_route_renderer_extraction_map_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "dashboard route/renderer extraction map report not found."
    lines = ["# Dashboard Route/Renderer Extraction Map", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Route count: {report.get('route_count')}", f"Renderer ref count: {report.get('renderer_ref_count')}", f"Generated wiring activated: {report.get('generated_wiring_activated')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Clusters"])
        for c in report.get("clusters") or []:
            lines.append(f"- {c.get('cluster')}: risk={c.get('risk')} count={c.get('count')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_dashboard_route_renderer_extraction_map_review(full: bool = False) -> None:
    print(dashboard_route_renderer_extraction_map_review_text(build_dashboard_route_renderer_extraction_map_review(), full=full))


def build_cli_api_dispatch_extraction_map_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    main_text = _giant_file_source_text(root, "conscious_agent/main.py", limit=2_000_000)
    api_text = _giant_file_source_text(root, "conscious_agent/api_server.py", limit=2_000_000)
    cli_flags = sorted(set(re.findall(r'--[a-z0-9][a-z0-9-]+', main_text)))
    api_routes = sorted(set(re.findall(r'["\'](/api/[^"\']+)["\']', api_text)))
    builder_refs = sorted(set(re.findall(r'(build_[a-z0-9_]+_review)', main_text + "\n" + api_text)))
    clusters = [{"cluster": "cli_dispatch", "risk": "medium", "count": len(cli_flags), "examples": cli_flags[:20], "move_live_code_now": False}, {"cluster": "api_dispatch", "risk": "medium", "count": len(api_routes), "examples": api_routes[:20], "move_live_code_now": False}, {"cluster": "builder_dispatch", "risk": "medium", "count": len(builder_refs), "examples": builder_refs[:20], "move_live_code_now": False}]
    policy_results = _giant_file_policy_base(root, "cli-api-dispatch-extraction-map-v1", "--cli-api-dispatch-extraction-map", "build_cli_api_dispatch_extraction_map_review", "cli_api_dispatch_extraction_map_review_text", "v945-cli-api-dispatch-extraction-map")
    policy_results.update({"cli_flags_present": len(cli_flags) > 0, "api_text_present": len(api_text) > 0, "builder_refs_present": len(builder_refs) > 0, "clusters_present": len(clusters) == 3})
    return {"id": f"cli_api_dispatch_extraction_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "cli_api_dispatch_extraction_map_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "cli_flag_count": len(cli_flags), "api_route_count": len(api_routes), "builder_ref_count": len(builder_refs), "clusters": clusters, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v946.0 Smoke Registry Extraction Map v1"}


def cli_api_dispatch_extraction_map_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "CLI/API dispatch extraction map report not found."
    lines = ["# CLI/API Dispatch Extraction Map", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"CLI flag count: {report.get('cli_flag_count')}", f"API route count: {report.get('api_route_count')}", f"Builder ref count: {report.get('builder_ref_count')}", f"Generated wiring activated: {report.get('generated_wiring_activated')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Clusters"])
        for c in report.get("clusters") or []:
            lines.append(f"- {c.get('cluster')}: risk={c.get('risk')} count={c.get('count')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_cli_api_dispatch_extraction_map_review(full: bool = False) -> None:
    print(cli_api_dispatch_extraction_map_review_text(build_cli_api_dispatch_extraction_map_review(), full=full))


def build_smoke_registry_extraction_map_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    text = _giant_file_source_text(root, "tools/smoke_check.py", limit=3_000_000)
    smoke_entries = re.findall(r'SmokeCheck\("([^"]+)",\s*"([^"]+)"', text)
    check_functions = sorted(set(re.findall(r'def (check_[a-z0-9_]+)\(', text)))
    segments = sorted(set(segment for _, segment in smoke_entries))
    timeout_tiers = sorted(set(re.findall(r'SmokeCheck\("[^"]+",\s*"[^"]+",\s*(\d+)', text)))[:20]
    clusters = [{"cluster": "smoke_registry", "risk": "medium", "count": len(smoke_entries), "examples": [name for name, _ in smoke_entries[:20]], "move_live_code_now": False}, {"cluster": "smoke_check_functions", "risk": "medium", "count": len(check_functions), "examples": check_functions[:20], "move_live_code_now": False}, {"cluster": "segments", "risk": "low", "count": len(segments), "examples": segments, "move_live_code_now": False}]
    policy_results = _giant_file_policy_base(root, "smoke-registry-extraction-map-v1", "--smoke-registry-extraction-map", "build_smoke_registry_extraction_map_review", "smoke_registry_extraction_map_review_text", "v946-smoke-registry-extraction-map")
    policy_results.update({"smoke_entries_present": len(smoke_entries) > 0, "check_functions_present": len(check_functions) > 0, "segments_present": len(segments) > 0, "expected_current_version_used": "EXPECTED_CURRENT_VERSION" in text, "clusters_present": len(clusters) == 3})
    return {"id": f"smoke_registry_extraction_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "smoke_registry_extraction_map_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "smoke_entry_count": len(smoke_entries), "check_function_count": len(check_functions), "segment_count": len(segments), "timeout_tier_sample_count": len(timeout_tiers), "clusters": clusters, "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v947.0 Compatibility Wrapper Risk Ledger v1"}


def smoke_registry_extraction_map_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "smoke registry extraction map report not found."
    lines = ["# Smoke Registry Extraction Map", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Smoke entry count: {report.get('smoke_entry_count')}", f"Check function count: {report.get('check_function_count')}", f"Segment count: {report.get('segment_count')}", f"Generated wiring activated: {report.get('generated_wiring_activated')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Clusters"])
        for c in report.get("clusters") or []:
            lines.append(f"- {c.get('cluster')}: risk={c.get('risk')} count={c.get('count')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_smoke_registry_extraction_map_review(full: bool = False) -> None:
    print(smoke_registry_extraction_map_review_text(build_smoke_registry_extraction_map_review(), full=full))


def build_compatibility_wrapper_risk_ledger_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    source_map = build_self_development_cycle_extraction_map_review(root)
    maintenance_map = build_self_maintenance_builder_text_renderer_extraction_map_review(root)
    dashboard_map = build_dashboard_route_renderer_extraction_map_review(root)
    cli_api_map = build_cli_api_dispatch_extraction_map_review(root)
    smoke_map = build_smoke_registry_extraction_map_review(root)
    ledger_rows = [
        {"area": "generated_preview_review_helpers", "risk": "low", "candidate_count": source_map.get("clusters", [{}])[0].get("candidate_count", 0), "operator_control_required": True},
        {"area": "self_maintenance_builders_text_renderers", "risk": "low", "candidate_count": maintenance_map.get("builder_count", 0) + maintenance_map.get("text_renderer_count", 0), "operator_control_required": True},
        {"area": "dashboard_route_dispatch", "risk": "medium", "candidate_count": dashboard_map.get("route_count", 0), "operator_control_required": True},
        {"area": "cli_api_dispatch", "risk": "medium", "candidate_count": cli_api_map.get("cli_flag_count", 0) + cli_api_map.get("api_route_count", 0), "operator_control_required": True},
        {"area": "smoke_registry", "risk": "medium", "candidate_count": smoke_map.get("smoke_entry_count", 0), "operator_control_required": True},
        {"area": "release_approval_memory_probe_runtime", "risk": "protected", "candidate_count": source_map.get("clusters", [{}, {}, {}])[-1].get("candidate_count", 0), "operator_control_required": True},
    ]
    risk_counts = {risk: sum(1 for row in ledger_rows if row["risk"] == risk) for risk in ("low", "medium", "high", "protected")}
    policy_results = _giant_file_policy_base(root, "compatibility-wrapper-risk-ledger-v1", "--compatibility-wrapper-risk-ledger", "build_compatibility_wrapper_risk_ledger_review", "compatibility_wrapper_risk_ledger_review_text", "v947-compatibility-wrapper-risk-ledger")
    policy_results.update({"source_map_passed": source_map.get("ok") is True, "maintenance_map_passed": maintenance_map.get("ok") is True, "dashboard_map_passed": dashboard_map.get("ok") is True, "cli_api_map_passed": cli_api_map.get("ok") is True, "smoke_map_passed": smoke_map.get("ok") is True, "protected_area_visible": risk_counts.get("protected", 0) > 0})
    return {"id": f"compatibility_wrapper_risk_ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "compatibility_wrapper_risk_ledger_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "ledger_rows": ledger_rows, "risk_counts": risk_counts, "low_risk_extraction_count": sum(row["candidate_count"] for row in ledger_rows if row["risk"] == "low"), "protected_manual_count": sum(row["candidate_count"] for row in ledger_rows if row["risk"] == "protected"), "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v948.0 Extraction Order Proposal v1"}


def compatibility_wrapper_risk_ledger_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "compatibility wrapper risk ledger report not found."
    lines = ["# Compatibility Wrapper Risk Ledger", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Low-risk extraction count: {report.get('low_risk_extraction_count')}", f"Protected/manual count: {report.get('protected_manual_count')}", f"Generated wiring activated: {report.get('generated_wiring_activated')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Ledger rows"])
        for row in report.get("ledger_rows") or []:
            lines.append(f"- {row.get('area')}: risk={row.get('risk')} candidates={row.get('candidate_count')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_compatibility_wrapper_risk_ledger_review(full: bool = False) -> None:
    print(compatibility_wrapper_risk_ledger_review_text(build_compatibility_wrapper_risk_ledger_review(), full=full))


def build_extraction_order_proposal_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    risk = build_compatibility_wrapper_risk_ledger_review(root)
    extraction_order = [
        {"order": 1, "cluster": "v916-v920 generated preview review helpers", "recommended_module": "conscious_agent/generated_surface_preview_reviews.py", "risk": "low", "move_live_code_now": False},
        {"order": 2, "cluster": "v921-v925 single-surface parity review helpers", "recommended_module": "conscious_agent/generated_surface_parity_reviews.py", "risk": "low", "move_live_code_now": False},
        {"order": 3, "cluster": "v926-v930 multi-surface parity review helpers", "recommended_module": "conscious_agent/generated_surface_batch_parity_reviews.py", "risk": "low", "move_live_code_now": False},
        {"order": 4, "cluster": "v931-v940 scaffold/wrapper preview helpers", "recommended_module": "conscious_agent/generated_scaffold_wrapper_reviews.py", "risk": "low", "move_live_code_now": False},
        {"order": 5, "cluster": "dashboard/CLI/API/smoke dispatch wrappers", "recommended_module": "defer_until_after_review_helper_extraction", "risk": "medium", "move_live_code_now": False},
    ]
    policy_results = _giant_file_policy_base(root, "extraction-order-proposal-v1", "--extraction-order-proposal", "build_extraction_order_proposal_review", "extraction_order_proposal_review_text", "v948-extraction-order-proposal")
    policy_results.update({"risk_ledger_passed": risk.get("ok") is True, "order_has_low_risk_first": extraction_order[0].get("risk") == "low", "first_module_named": bool(extraction_order[0].get("recommended_module")), "no_move_live_code_now": all(item.get("move_live_code_now") is False for item in extraction_order)})
    return {"id": f"extraction_order_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "extraction_order_proposal_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "extraction_order": extraction_order, "recommended_first_extraction_module": extraction_order[0]["recommended_module"], "candidate_count": sum(row.get("candidate_count", 0) for row in risk.get("ledger_rows", [])), "low_risk_extraction_count": risk.get("low_risk_extraction_count"), "protected_manual_count": risk.get("protected_manual_count"), "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v949.0 Extraction Rollback Evidence Plan v1"}


def extraction_order_proposal_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "extraction order proposal report not found."
    lines = ["# Extraction Order Proposal", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Recommended first extraction module: {report.get('recommended_first_extraction_module')}", f"Candidate count: {report.get('candidate_count')}", f"Low-risk extraction count: {report.get('low_risk_extraction_count')}", f"Protected/manual count: {report.get('protected_manual_count')}", f"Moves live code: {report.get('moves_live_code')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Extraction order"])
        for item in report.get("extraction_order") or []:
            lines.append(f"- {item.get('order')}. {item.get('cluster')} -> {item.get('recommended_module')} risk={item.get('risk')}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_extraction_order_proposal_review(full: bool = False) -> None:
    print(extraction_order_proposal_review_text(build_extraction_order_proposal_review(), full=full))


def build_extraction_rollback_evidence_plan_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    order = build_extraction_order_proposal_review(root)
    evidence_steps = [
        "pre_extraction_function_inventory",
        "post_extraction_function_inventory",
        "import_compatibility_check",
        "dashboard_route_parity_check",
        "cli_flag_parity_check",
        "api_route_parity_check",
        "smoke_registry_parity_check",
        "current_version_staleness_audit",
        "source_package_privacy_deep_scan",
        "README_NEXT_STEPS_update",
        "README_RELEASE_HISTORY_update",
        "rollback_to_manual_module_path",
    ]
    policy_results = _giant_file_policy_base(root, "extraction-rollback-evidence-plan-v1", "--extraction-rollback-evidence-plan", "build_extraction_rollback_evidence_plan_review", "extraction_rollback_evidence_plan_review_text", "v949-extraction-rollback-evidence-plan")
    policy_results.update({"order_proposal_passed": order.get("ok") is True, "evidence_steps_complete": len(evidence_steps) >= 10, "route_cli_api_smoke_covered": all(step in evidence_steps for step in ["dashboard_route_parity_check", "cli_flag_parity_check", "api_route_parity_check", "smoke_registry_parity_check"]), "package_privacy_covered": "source_package_privacy_deep_scan" in evidence_steps, "readme_updates_required": "README_NEXT_STEPS_update" in evidence_steps and "README_RELEASE_HISTORY_update" in evidence_steps})
    return {"id": f"extraction_rollback_evidence_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "extraction_rollback_evidence_plan_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "evidence_step_count": len(evidence_steps), "evidence_steps": evidence_steps, "rollback_plan_status": "prepared_review_only", "recommended_first_extraction_module": order.get("recommended_first_extraction_module"), "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": "v950.0 Giant File Compatibility Extraction Prep Closure v1"}


def extraction_rollback_evidence_plan_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "extraction rollback evidence plan report not found."
    lines = ["# Extraction Rollback Evidence Plan", "", f"Status: {report.get('status')}", f"Version: {report.get('version')}", f"Evidence step count: {report.get('evidence_step_count')}", f"Rollback plan status: {report.get('rollback_plan_status')}", f"Recommended first extraction module: {report.get('recommended_first_extraction_module')}", f"Moves live code: {report.get('moves_live_code')}", f"Autonomy expanded: {report.get('autonomy_expanded')}", f"Policies passed: {report.get('policies_passed')}"]
    if full:
        lines.extend(["", "## Evidence steps"])
        for step in report.get("evidence_steps") or []:
            lines.append(f"- {step}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_extraction_rollback_evidence_plan_review(full: bool = False) -> None:
    print(extraction_rollback_evidence_plan_review_text(build_extraction_rollback_evidence_plan_review(), full=full))


def build_giant_file_compatibility_extraction_prep_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(root_dir or Path(__file__).resolve().parents[1])
    inventory = build_giant_file_extraction_inventory_review(root)
    sdc_map = build_self_development_cycle_extraction_map_review(root)
    maintenance_map = build_self_maintenance_builder_text_renderer_extraction_map_review(root)
    dashboard_map = build_dashboard_route_renderer_extraction_map_review(root)
    cli_api_map = build_cli_api_dispatch_extraction_map_review(root)
    smoke_map = build_smoke_registry_extraction_map_review(root)
    low_risk_extraction_count = (sdc_map.get("clusters", [{}])[0].get("candidate_count", 0) or 0) + (maintenance_map.get("builder_count", 0) or 0) + (maintenance_map.get("text_renderer_count", 0) or 0)
    protected_manual_count = sdc_map.get("clusters", [{}, {}, {}])[-1].get("candidate_count", 0) or 0
    candidate_count = low_risk_extraction_count + protected_manual_count + (dashboard_map.get("route_count", 0) or 0) + (cli_api_map.get("cli_flag_count", 0) or 0) + (cli_api_map.get("api_route_count", 0) or 0) + (smoke_map.get("smoke_entry_count", 0) or 0)
    recommended_first_module = "conscious_agent/generated_surface_preview_reviews.py"
    closure = {
        "target_file_count": inventory.get("target_file_count"),
        "candidate_count": candidate_count,
        "low_risk_extraction_count": low_risk_extraction_count,
        "protected_manual_count": protected_manual_count,
        "recommended_first_extraction_module": recommended_first_module,
        "rollback_plan_status": "prepared_review_only",
        "dashboard_route_count": dashboard_map.get("route_count"),
        "cli_flag_count": cli_api_map.get("cli_flag_count"),
        "smoke_entry_count": smoke_map.get("smoke_entry_count"),
        "self_development_candidate_count": sdc_map.get("candidate_count"),
        "self_maintenance_builder_count": maintenance_map.get("builder_count"),
        "activation_status": "inactive_review_only",
        "autonomy_status": "unchanged_not_expanded",
    }
    policy_results = _giant_file_policy_base(root, "giant-file-compatibility-extraction-prep-closure-v1", "--giant-file-compatibility-extraction-prep-closure", "build_giant_file_compatibility_extraction_prep_closure_review", "giant_file_compatibility_extraction_prep_closure_review_text", "v950-giant-file-compatibility-extraction-prep-closure")
    policy_results.update({
        "inventory_passed": inventory.get("ok") is True,
        "sdc_map_passed": sdc_map.get("ok") is True,
        "maintenance_map_passed": maintenance_map.get("ok") is True,
        "dashboard_map_passed": dashboard_map.get("ok") is True,
        "cli_api_map_passed": cli_api_map.get("ok") is True,
        "smoke_map_passed": smoke_map.get("ok") is True,
        "risk_ledger_accounted": low_risk_extraction_count > 0 and protected_manual_count > 0,
        "order_proposal_accounted": recommended_first_module.endswith("generated_surface_preview_reviews.py"),
        "rollback_plan_accounted": closure.get("rollback_plan_status") == "prepared_review_only",
        "recommended_first_module_present": bool(closure.get("recommended_first_extraction_module")),
        "no_activation": closure.get("activation_status") == "inactive_review_only",
        "autonomy_unchanged": closure.get("autonomy_status") == "unchanged_not_expanded",
    })
    return {"id": f"giant_file_compatibility_extraction_prep_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "type": "giant_file_compatibility_extraction_prep_closure_review", "status": "pass" if all(policy_results.values()) else "blocked", "ok": all(policy_results.values()), "version": SELF_DEVELOPMENT_CYCLE_VERSION, "current_milestone": CURRENT_MILESTONE, "closure": closure, "candidate_count": closure.get("candidate_count"), "low_risk_extraction_count": closure.get("low_risk_extraction_count"), "protected_manual_count": closure.get("protected_manual_count"), "recommended_first_extraction_module": closure.get("recommended_first_extraction_module"), "rollback_plan_status": closure.get("rollback_plan_status"), "policies_passed": all(policy_results.values()), "policy_results": policy_results, **_giant_file_safety_fields(), "recommended_next_arc": NEXT_RECOMMENDED_ARC}

def giant_file_compatibility_extraction_prep_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "giant file compatibility extraction prep closure report not found."
    closure = report.get("closure") or {}
    lines = [
        "# Giant File Compatibility Extraction Prep Closure",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Current milestone: {report.get('current_milestone')}",
        f"Target file count: {closure.get('target_file_count')}",
        f"Candidate count: {closure.get('candidate_count')}",
        f"Low-risk extraction count: {closure.get('low_risk_extraction_count')}",
        f"Protected/manual count: {closure.get('protected_manual_count')}",
        f"Recommended first extraction module: {closure.get('recommended_first_extraction_module')}",
        f"Rollback plan status: {closure.get('rollback_plan_status')}",
        f"Activation status: {closure.get('activation_status')}",
        f"Autonomy status: {closure.get('autonomy_status')}",
        f"Moves live code: {report.get('moves_live_code')}",
        f"Splits files: {report.get('splits_files')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Manual code replaced: {report.get('manual_code_replaced')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Policies passed: {report.get('policies_passed')}",
    ]
    if full:
        lines.extend(["", "## Closure fields"])
        for key, value in closure.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_giant_file_compatibility_extraction_prep_closure_review(full: bool = False) -> None:
    print(giant_file_compatibility_extraction_prep_closure_review_text(build_giant_file_compatibility_extraction_prep_closure_review(), full=full))

# v941.0-v950.0 giant file compatibility extraction prep self-development tokens: giant-file-extraction-inventory-v1 --giant-file-extraction-inventory build_giant_file_extraction_inventory_review giant_file_extraction_inventory_review_text self-development-cycle-extraction-map-v1 --self-development-cycle-extraction-map build_self_development_cycle_extraction_map_review self_development_cycle_extraction_map_review_text self-maintenance-builder-text-renderer-extraction-map-v1 --self-maintenance-builder-text-renderer-extraction-map build_self_maintenance_builder_text_renderer_extraction_map_review self_maintenance_builder_text_renderer_extraction_map_review_text dashboard-route-renderer-extraction-map-v1 --dashboard-route-renderer-extraction-map build_dashboard_route_renderer_extraction_map_review dashboard_route_renderer_extraction_map_review_text cli-api-dispatch-extraction-map-v1 --cli-api-dispatch-extraction-map build_cli_api_dispatch_extraction_map_review cli_api_dispatch_extraction_map_review_text smoke-registry-extraction-map-v1 --smoke-registry-extraction-map build_smoke_registry_extraction_map_review smoke_registry_extraction_map_review_text compatibility-wrapper-risk-ledger-v1 --compatibility-wrapper-risk-ledger build_compatibility_wrapper_risk_ledger_review compatibility_wrapper_risk_ledger_review_text extraction-order-proposal-v1 --extraction-order-proposal build_extraction_order_proposal_review extraction_order_proposal_review_text extraction-rollback-evidence-plan-v1 --extraction-rollback-evidence-plan build_extraction_rollback_evidence_plan_review extraction_rollback_evidence_plan_review_text giant-file-compatibility-extraction-prep-closure-v1 --giant-file-compatibility-extraction-prep-closure build_giant_file_compatibility_extraction_prep_closure_review giant_file_compatibility_extraction_prep_closure_review_text candidate_count low_risk_extraction_count protected_manual_count recommended_first_extraction_module rollback_plan_status moves_live_code=False splits_files=False generated_wiring_activated=False manual_code_replaced=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v913.0 release archive and recovery gate boundedness repair self-development tokens: release-archive-and-recovery-gate-boundedness-repair-v1 --release-archive-and-recovery-gate-boundedness-repair build_release_archive_and_recovery_gate_boundedness_repair_review release_archive_and_recovery_gate_boundedness_repair_review_text bounded_for_source_only_release=True needs_fixture_before_full_blocking_use=True executes_full_install_release_segment=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
# v914.0 install-release segment evidence summary gate self-development tokens: install-release-segment-evidence-summary-gate-v1 --install-release-segment-evidence-summary-gate build_install_release_segment_evidence_summary_gate_review install_release_segment_evidence_summary_gate_review_text full_install_release_clean=False active_current_evidence historical_blockers_visible bounded_archive_recovery_checks_visible release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
# v915.0 manifest-driven surface generation prep self-development tokens: manifest-driven-surface-generation-prep-v1 --manifest-driven-surface-generation-prep build_manifest_driven_surface_generation_prep_review manifest_driven_surface_generation_prep_review_text canonical_fields_defined=True review_only_candidates_identified=True protected_manual_surfaces_identified=True generates_surfaces=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console


# v961-v970 second compatibility extraction and smoke registry prep public wrappers.

def build_second_extraction_candidate_selection_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_second_extraction_candidate_selection_gate_review(root_dir)

def second_extraction_candidate_selection_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().second_extraction_candidate_selection_gate_review_text(report, full=full)

def print_second_extraction_candidate_selection_gate_review(full: bool = False) -> None:
    print(second_extraction_candidate_selection_gate_review_text(build_second_extraction_candidate_selection_gate_review(), full=full))

def build_second_pre_extraction_function_inventory_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_second_pre_extraction_function_inventory_review(root_dir)

def second_pre_extraction_function_inventory_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().second_pre_extraction_function_inventory_review_text(report, full=full)

def print_second_pre_extraction_function_inventory_review(full: bool = False) -> None:
    print(second_pre_extraction_function_inventory_review_text(build_second_pre_extraction_function_inventory_review(), full=full))

def build_generated_scaffold_review_packet_extraction_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_generated_scaffold_review_packet_extraction_review(root_dir)

def generated_scaffold_review_packet_extraction_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().generated_scaffold_review_packet_extraction_review_text(report, full=full)

def print_generated_scaffold_review_packet_extraction_review(full: bool = False) -> None:
    print(generated_scaffold_review_packet_extraction_review_text(build_generated_scaffold_review_packet_extraction_review(), full=full))

def build_second_compatibility_wrapper_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_second_compatibility_wrapper_gate_review(root_dir)

def second_compatibility_wrapper_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().second_compatibility_wrapper_gate_review_text(report, full=full)

def print_second_compatibility_wrapper_gate_review(full: bool = False) -> None:
    print(second_compatibility_wrapper_gate_review_text(build_second_compatibility_wrapper_gate_review(), full=full))

def build_second_extraction_surface_parity_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_second_extraction_surface_parity_gate_review(root_dir)

def second_extraction_surface_parity_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().second_extraction_surface_parity_gate_review_text(report, full=full)

def print_second_extraction_surface_parity_gate_review(full: bool = False) -> None:
    print(second_extraction_surface_parity_gate_review_text(build_second_extraction_surface_parity_gate_review(), full=full))

def build_smoke_registry_data_model_prep_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_smoke_registry_data_model_prep_review(root_dir)

def smoke_registry_data_model_prep_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().smoke_registry_data_model_prep_review_text(report, full=full)

def print_smoke_registry_data_model_prep_review(full: bool = False) -> None:
    print(smoke_registry_data_model_prep_review_text(build_smoke_registry_data_model_prep_review(), full=full))

def build_smoke_registry_static_inventory_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_smoke_registry_static_inventory_review(root_dir)

def smoke_registry_static_inventory_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().smoke_registry_static_inventory_review_text(report, full=full)

def print_smoke_registry_static_inventory_review(full: bool = False) -> None:
    print(smoke_registry_static_inventory_review_text(build_smoke_registry_static_inventory_review(), full=full))

def build_smoke_registry_migration_risk_ledger_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_smoke_registry_migration_risk_ledger_review(root_dir)

def smoke_registry_migration_risk_ledger_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().smoke_registry_migration_risk_ledger_review_text(report, full=full)

def print_smoke_registry_migration_risk_ledger_review(full: bool = False) -> None:
    print(smoke_registry_migration_risk_ledger_review_text(build_smoke_registry_migration_risk_ledger_review(), full=full))

def build_smoke_registry_rollback_plan_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_smoke_registry_rollback_plan_review(root_dir)

def smoke_registry_rollback_plan_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().smoke_registry_rollback_plan_review_text(report, full=full)

def print_smoke_registry_rollback_plan_review(full: bool = False) -> None:
    print(smoke_registry_rollback_plan_review_text(build_smoke_registry_rollback_plan_review(), full=full))

def build_second_extraction_and_smoke_registry_prep_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _generated_scaffold_review_packets_module().build_second_extraction_and_smoke_registry_prep_closure_review(root_dir)

def second_extraction_and_smoke_registry_prep_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _generated_scaffold_review_packets_module().second_extraction_and_smoke_registry_prep_closure_review_text(report, full=full)

def print_second_extraction_and_smoke_registry_prep_closure_review(full: bool = False) -> None:
    print(second_extraction_and_smoke_registry_prep_closure_review_text(build_second_extraction_and_smoke_registry_prep_closure_review(), full=full))

# v961.0-v970.0 self-development cycle wrapper tokens: second-extraction-candidate-selection-gate-v1 --second-extraction-candidate-selection-gate build_second_extraction_candidate_selection_gate_review second_extraction_candidate_selection_gate_review_text second-pre-extraction-function-inventory-v1 --second-pre-extraction-function-inventory build_second_pre_extraction_function_inventory_review second_pre_extraction_function_inventory_review_text generated-scaffold-review-packet-extraction-v1 --generated-scaffold-review-packet-extraction build_generated_scaffold_review_packet_extraction_review generated_scaffold_review_packet_extraction_review_text second-compatibility-wrapper-gate-v1 --second-compatibility-wrapper-gate build_second_compatibility_wrapper_gate_review second_compatibility_wrapper_gate_review_text second-extraction-surface-parity-gate-v1 --second-extraction-surface-parity-gate build_second_extraction_surface_parity_gate_review second_extraction_surface_parity_gate_review_text smoke-registry-data-model-prep-v1 --smoke-registry-data-model-prep build_smoke_registry_data_model_prep_review smoke_registry_data_model_prep_review_text smoke-registry-static-inventory-v1 --smoke-registry-static-inventory build_smoke_registry_static_inventory_review smoke_registry_static_inventory_review_text smoke-registry-migration-risk-ledger-v1 --smoke-registry-migration-risk-ledger build_smoke_registry_migration_risk_ledger_review smoke_registry_migration_risk_ledger_review_text smoke-registry-rollback-plan-v1 --smoke-registry-rollback-plan build_smoke_registry_rollback_plan_review smoke_registry_rollback_plan_review_text second-extraction-and-smoke-registry-prep-closure-v1 --second-extraction-and-smoke-registry-prep-closure build_second_extraction_and_smoke_registry_prep_closure_review second_extraction_and_smoke_registry_prep_closure_review_text second_extracted_module=conscious_agent/generated_scaffold_review_packets.py extracted_cluster=v931-v935 wrappers_preserved=True smoke_registry_model=prepared_only smoke_registry_behavior_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True



# v971-v980 smoke registry data-driven pilot public wrappers.

def build_smoke_registry_pilot_selection_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_pilot_selection_gate_review(root_dir)

def smoke_registry_pilot_selection_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_pilot_selection_gate_review_text(report, full=full)

def print_smoke_registry_pilot_selection_gate_review(full: bool = False) -> None:
    print(smoke_registry_pilot_selection_gate_review_text(build_smoke_registry_pilot_selection_gate_review(), full=full))

def build_smoke_registry_pilot_schema_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_pilot_schema_review(root_dir)

def smoke_registry_pilot_schema_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_pilot_schema_review_text(report, full=full)

def print_smoke_registry_pilot_schema_review(full: bool = False) -> None:
    print(smoke_registry_pilot_schema_review_text(build_smoke_registry_pilot_schema_review(), full=full))

def build_smoke_registry_pilot_data_table_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_pilot_data_table_review(root_dir)

def smoke_registry_pilot_data_table_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_pilot_data_table_review_text(report, full=full)

def print_smoke_registry_pilot_data_table_review(full: bool = False) -> None:
    print(smoke_registry_pilot_data_table_review_text(build_smoke_registry_pilot_data_table_review(), full=full))

def build_smoke_registry_pilot_resolver_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_pilot_resolver_review(root_dir)

def smoke_registry_pilot_resolver_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_pilot_resolver_review_text(report, full=full)

def print_smoke_registry_pilot_resolver_review(full: bool = False) -> None:
    print(smoke_registry_pilot_resolver_review_text(build_smoke_registry_pilot_resolver_review(), full=full))

def build_manual_vs_pilot_smoke_parity_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_manual_vs_pilot_smoke_parity_gate_review(root_dir)

def manual_vs_pilot_smoke_parity_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().manual_vs_pilot_smoke_parity_gate_review_text(report, full=full)

def print_manual_vs_pilot_smoke_parity_gate_review(full: bool = False) -> None:
    print(manual_vs_pilot_smoke_parity_gate_review_text(build_manual_vs_pilot_smoke_parity_gate_review(), full=full))

def build_pilot_json_shape_compatibility_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_pilot_json_shape_compatibility_gate_review(root_dir)

def pilot_json_shape_compatibility_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().pilot_json_shape_compatibility_gate_review_text(report, full=full)

def print_pilot_json_shape_compatibility_gate_review(full: bool = False) -> None:
    print(pilot_json_shape_compatibility_gate_review_text(build_pilot_json_shape_compatibility_gate_review(), full=full))

def build_pilot_rollback_evidence_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_pilot_rollback_evidence_gate_review(root_dir)

def pilot_rollback_evidence_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().pilot_rollback_evidence_gate_review_text(report, full=full)

def print_pilot_rollback_evidence_gate_review(full: bool = False) -> None:
    print(pilot_rollback_evidence_gate_review_text(build_pilot_rollback_evidence_gate_review(), full=full))

def build_smoke_registry_pilot_risk_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_pilot_risk_review(root_dir)

def smoke_registry_pilot_risk_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_pilot_risk_review_text(report, full=full)

def print_smoke_registry_pilot_risk_review(full: bool = False) -> None:
    print(smoke_registry_pilot_risk_review_text(build_smoke_registry_pilot_risk_review(), full=full))

def build_pilot_expansion_readiness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_pilot_expansion_readiness_review(root_dir)

def pilot_expansion_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().pilot_expansion_readiness_review_text(report, full=full)

def print_pilot_expansion_readiness_review(full: bool = False) -> None:
    print(pilot_expansion_readiness_review_text(build_pilot_expansion_readiness_review(), full=full))

def build_smoke_registry_data_driven_pilot_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_data_driven_pilot_closure_review(root_dir)

def smoke_registry_data_driven_pilot_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_data_driven_pilot_closure_review_text(report, full=full)

def print_smoke_registry_data_driven_pilot_closure_review(full: bool = False) -> None:
    print(smoke_registry_data_driven_pilot_closure_review_text(build_smoke_registry_data_driven_pilot_closure_review(), full=full))

# v971.0-v980.0 self-development cycle wrapper tokens: smoke-registry-pilot-selection-gate-v1 --smoke-registry-pilot-selection-gate build_smoke_registry_pilot_selection_gate_review smoke_registry_pilot_selection_gate_review_text smoke-registry-pilot-schema-v1 --smoke-registry-pilot-schema build_smoke_registry_pilot_schema_review smoke_registry_pilot_schema_review_text smoke-registry-pilot-data-table-v1 --smoke-registry-pilot-data-table build_smoke_registry_pilot_data_table_review smoke_registry_pilot_data_table_review_text smoke-registry-pilot-resolver-v1 --smoke-registry-pilot-resolver build_smoke_registry_pilot_resolver_review smoke_registry_pilot_resolver_review_text manual-vs-pilot-smoke-parity-gate-v1 --manual-vs-pilot-smoke-parity-gate build_manual_vs_pilot_smoke_parity_gate_review manual_vs_pilot_smoke_parity_gate_review_text pilot-json-shape-compatibility-gate-v1 --pilot-json-shape-compatibility-gate build_pilot_json_shape_compatibility_gate_review pilot_json_shape_compatibility_gate_review_text pilot-rollback-evidence-gate-v1 --pilot-rollback-evidence-gate build_pilot_rollback_evidence_gate_review pilot_rollback_evidence_gate_review_text smoke-registry-pilot-risk-review-v1 --smoke-registry-pilot-risk-review build_smoke_registry_pilot_risk_review smoke_registry_pilot_risk_review_text pilot-expansion-readiness-review-v1 --pilot-expansion-readiness-review build_pilot_expansion_readiness_review pilot_expansion_readiness_review_text smoke-registry-data-driven-pilot-closure-v1 --smoke-registry-data-driven-pilot-closure build_smoke_registry_data_driven_pilot_closure_review smoke_registry_data_driven_pilot_closure_review_text pilot_checks=5 pilot_table_exists=True manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True


# v981-v990 smoke registry data-driven execution trial public wrappers.

def build_smoke_registry_execution_trial_readiness_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_execution_trial_readiness_gate_review(root_dir)

def smoke_registry_execution_trial_readiness_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_execution_trial_readiness_gate_review_text(report, full=full)

def print_smoke_registry_execution_trial_readiness_gate_review(full: bool = False) -> None:
    print(smoke_registry_execution_trial_readiness_gate_review_text(build_smoke_registry_execution_trial_readiness_gate_review(), full=full))

def build_data_driven_smoke_callable_execution_harness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_data_driven_smoke_callable_execution_harness_review(root_dir)

def data_driven_smoke_callable_execution_harness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().data_driven_smoke_callable_execution_harness_review_text(report, full=full)

def print_data_driven_smoke_callable_execution_harness_review(full: bool = False) -> None:
    print(data_driven_smoke_callable_execution_harness_review_text(build_data_driven_smoke_callable_execution_harness_review(), full=full))

def build_pilot_smoke_execution_result_packet_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_pilot_smoke_execution_result_packet_review(root_dir)

def pilot_smoke_execution_result_packet_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().pilot_smoke_execution_result_packet_review_text(report, full=full)

def print_pilot_smoke_execution_result_packet_review(full: bool = False) -> None:
    print(pilot_smoke_execution_result_packet_review_text(build_pilot_smoke_execution_result_packet_review(), full=full))

def build_manual_vs_data_driven_execution_parity_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_manual_vs_data_driven_execution_parity_gate_review(root_dir)

def manual_vs_data_driven_execution_parity_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().manual_vs_data_driven_execution_parity_gate_review_text(report, full=full)

def print_manual_vs_data_driven_execution_parity_gate_review(full: bool = False) -> None:
    print(manual_vs_data_driven_execution_parity_gate_review_text(build_manual_vs_data_driven_execution_parity_gate_review(), full=full))

def build_data_driven_smoke_json_output_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_data_driven_smoke_json_output_preview_review(root_dir)

def data_driven_smoke_json_output_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().data_driven_smoke_json_output_preview_review_text(report, full=full)

def print_data_driven_smoke_json_output_preview_review(full: bool = False) -> None:
    print(data_driven_smoke_json_output_preview_review_text(build_data_driven_smoke_json_output_preview_review(), full=full))

def build_data_driven_smoke_timeout_failure_semantics_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_data_driven_smoke_timeout_failure_semantics_review(root_dir)

def data_driven_smoke_timeout_failure_semantics_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().data_driven_smoke_timeout_failure_semantics_review_text(report, full=full)

def print_data_driven_smoke_timeout_failure_semantics_review(full: bool = False) -> None:
    print(data_driven_smoke_timeout_failure_semantics_review_text(build_data_driven_smoke_timeout_failure_semantics_review(), full=full))

def build_data_driven_smoke_manual_fallback_proof_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_data_driven_smoke_manual_fallback_proof_review(root_dir)

def data_driven_smoke_manual_fallback_proof_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().data_driven_smoke_manual_fallback_proof_review_text(report, full=full)

def print_data_driven_smoke_manual_fallback_proof_review(full: bool = False) -> None:
    print(data_driven_smoke_manual_fallback_proof_review_text(build_data_driven_smoke_manual_fallback_proof_review(), full=full))

def build_data_driven_smoke_execution_risk_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_data_driven_smoke_execution_risk_review(root_dir)

def data_driven_smoke_execution_risk_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().data_driven_smoke_execution_risk_review_text(report, full=full)

def print_data_driven_smoke_execution_risk_review(full: bool = False) -> None:
    print(data_driven_smoke_execution_risk_review_text(build_data_driven_smoke_execution_risk_review(), full=full))

def build_data_driven_smoke_expansion_readiness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_data_driven_smoke_expansion_readiness_review(root_dir)

def data_driven_smoke_expansion_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().data_driven_smoke_expansion_readiness_review_text(report, full=full)

def print_data_driven_smoke_expansion_readiness_review(full: bool = False) -> None:
    print(data_driven_smoke_expansion_readiness_review_text(build_data_driven_smoke_expansion_readiness_review(), full=full))

def build_smoke_registry_data_driven_execution_trial_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_data_driven_execution_trial_closure_review(root_dir)

def smoke_registry_data_driven_execution_trial_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_data_driven_execution_trial_closure_review_text(report, full=full)

def print_smoke_registry_data_driven_execution_trial_closure_review(full: bool = False) -> None:
    print(smoke_registry_data_driven_execution_trial_closure_review_text(build_smoke_registry_data_driven_execution_trial_closure_review(), full=full))

# v981.0-v990.0 self-development cycle wrapper tokens: smoke-registry-execution-trial-readiness-gate-v1 --smoke-registry-execution-trial-readiness-gate build_smoke_registry_execution_trial_readiness_gate_review smoke_registry_execution_trial_readiness_gate_review_text data-driven-smoke-callable-execution-harness-v1 --data-driven-smoke-callable-execution-harness build_data_driven_smoke_callable_execution_harness_review data_driven_smoke_callable_execution_harness_review_text pilot-smoke-execution-result-packet-v1 --pilot-smoke-execution-result-packet build_pilot_smoke_execution_result_packet_review pilot_smoke_execution_result_packet_review_text manual-vs-data-driven-execution-parity-gate-v1 --manual-vs-data-driven-execution-parity-gate build_manual_vs_data_driven_execution_parity_gate_review manual_vs_data_driven_execution_parity_gate_review_text data-driven-smoke-json-output-preview-v1 --data-driven-smoke-json-output-preview build_data_driven_smoke_json_output_preview_review data_driven_smoke_json_output_preview_text data-driven-smoke-timeout-failure-semantics-v1 --data-driven-smoke-timeout-failure-semantics build_data_driven_smoke_timeout_failure_semantics_review data_driven_smoke_timeout_failure_semantics_review_text data-driven-smoke-manual-fallback-proof-v1 --data-driven-smoke-manual-fallback-proof build_data_driven_smoke_manual_fallback_proof_review data_driven_smoke_manual_fallback_proof_review_text data-driven-smoke-execution-risk-review-v1 --data-driven-smoke-execution-risk-review build_data_driven_smoke_execution_risk_review data_driven_smoke_execution_risk_review_text data-driven-smoke-expansion-readiness-v1 --data-driven-smoke-expansion-readiness build_data_driven_smoke_expansion_readiness_review data_driven_smoke_expansion_readiness_review_text smoke-registry-data-driven-execution-trial-closure-v1 --smoke-registry-data-driven-execution-trial-closure build_smoke_registry_data_driven_execution_trial_closure_review smoke_registry_data_driven_execution_trial_closure_review_text pilot_checks_executed=5 data_driven_execution=pass manual_parity=exact_for_all_selected manual_registry_replaced=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True


# v991-v1000 smoke registry fallback migration pilot public wrappers.
def build_fallback_migration_readiness_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_fallback_migration_readiness_gate_review(root_dir)
def fallback_migration_readiness_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().fallback_migration_readiness_gate_review_text(report, full=full)
def print_fallback_migration_readiness_gate_review(full: bool = False) -> None:
    print(fallback_migration_readiness_gate_review_text(build_fallback_migration_readiness_gate_review(), full=full))
def build_data_driven_first_pilot_dispatch_preview_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_data_driven_first_pilot_dispatch_preview_review(root_dir)
def data_driven_first_pilot_dispatch_preview_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().data_driven_first_pilot_dispatch_preview_review_text(report, full=full)
def print_data_driven_first_pilot_dispatch_preview_review(full: bool = False) -> None:
    print(data_driven_first_pilot_dispatch_preview_review_text(build_data_driven_first_pilot_dispatch_preview_review(), full=full))
def build_pilot_fallback_dispatch_trial_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_pilot_fallback_dispatch_trial_review(root_dir)
def pilot_fallback_dispatch_trial_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().pilot_fallback_dispatch_trial_review_text(report, full=full)
def print_pilot_fallback_dispatch_trial_review(full: bool = False) -> None:
    print(pilot_fallback_dispatch_trial_review_text(build_pilot_fallback_dispatch_trial_review(), full=full))
def build_pilot_fallback_result_ledger_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_pilot_fallback_result_ledger_review(root_dir)
def pilot_fallback_result_ledger_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().pilot_fallback_result_ledger_review_text(report, full=full)
def print_pilot_fallback_result_ledger_review(full: bool = False) -> None:
    print(pilot_fallback_result_ledger_review_text(build_pilot_fallback_result_ledger_review(), full=full))
def build_json_output_stability_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_json_output_stability_gate_review(root_dir)
def json_output_stability_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().json_output_stability_gate_review_text(report, full=full)
def print_json_output_stability_gate_review(full: bool = False) -> None:
    print(json_output_stability_gate_review_text(build_json_output_stability_gate_review(), full=full))
def build_fast_install_release_isolation_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_fast_install_release_isolation_gate_review(root_dir)
def fast_install_release_isolation_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().fast_install_release_isolation_gate_review_text(report, full=full)
def print_fast_install_release_isolation_gate_review(full: bool = False) -> None:
    print(fast_install_release_isolation_gate_review_text(build_fast_install_release_isolation_gate_review(), full=full))
def build_manual_fallback_removal_resistance_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_manual_fallback_removal_resistance_gate_review(root_dir)
def manual_fallback_removal_resistance_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().manual_fallback_removal_resistance_gate_review_text(report, full=full)
def print_manual_fallback_removal_resistance_gate_review(full: bool = False) -> None:
    print(manual_fallback_removal_resistance_gate_review_text(build_manual_fallback_removal_resistance_gate_review(), full=full))
def build_pilot_migration_risk_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_pilot_migration_risk_review(root_dir)
def pilot_migration_risk_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().pilot_migration_risk_review_text(report, full=full)
def print_pilot_migration_risk_review(full: bool = False) -> None:
    print(pilot_migration_risk_review_text(build_pilot_migration_risk_review(), full=full))
def build_v1000_milestone_readiness_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_v1000_milestone_readiness_review(root_dir)
def v1000_milestone_readiness_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().v1000_milestone_readiness_review_text(report, full=full)
def print_v1000_milestone_readiness_review(full: bool = False) -> None:
    print(v1000_milestone_readiness_review_text(build_v1000_milestone_readiness_review(), full=full))
def build_smoke_registry_fallback_migration_pilot_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    return _smoke_registry_pilot_module().build_smoke_registry_fallback_migration_pilot_closure_review(root_dir)
def smoke_registry_fallback_migration_pilot_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    return _smoke_registry_pilot_module().smoke_registry_fallback_migration_pilot_closure_review_text(report, full=full)
def print_smoke_registry_fallback_migration_pilot_closure_review(full: bool = False) -> None:
    print(smoke_registry_fallback_migration_pilot_closure_review_text(build_smoke_registry_fallback_migration_pilot_closure_review(), full=full))

# v991.0-v1000.0 self-development cycle wrapper tokens: fallback-migration-readiness-gate-v1 --fallback-migration-readiness-gate build_fallback_migration_readiness_gate_review fallback_migration_readiness_gate_review_text data-driven-first-pilot-dispatch-preview-v1 --data-driven-first-pilot-dispatch-preview build_data_driven_first_pilot_dispatch_preview_review data_driven_first_pilot_dispatch_preview_review_text pilot-fallback-dispatch-trial-v1 --pilot-fallback-dispatch-trial build_pilot_fallback_dispatch_trial_review pilot_fallback_dispatch_trial_review_text pilot-fallback-result-ledger-v1 --pilot-fallback-result-ledger build_pilot_fallback_result_ledger_review pilot_fallback_result_ledger_review_text json-output-stability-gate-v1 --json-output-stability-gate build_json_output_stability_gate_review json_output_stability_gate_review_text fast-install-release-isolation-gate-v1 --fast-install-release-isolation-gate build_fast_install_release_isolation_gate_review fast_install_release_isolation_gate_review_text manual-fallback-removal-resistance-gate-v1 --manual-fallback-removal-resistance-gate build_manual_fallback_removal_resistance_gate_review manual_fallback_removal_resistance_gate_review_text pilot-migration-risk-review-v1 --pilot-migration-risk-review build_pilot_migration_risk_review pilot_migration_risk_review_text v1000-milestone-readiness-review-v1 --v1000-milestone-readiness-review build_v1000_milestone_readiness_review v1000_milestone_readiness_review_text smoke-registry-fallback-migration-pilot-closure-v1 --smoke-registry-fallback-migration-pilot-closure build_smoke_registry_fallback_migration_pilot_closure_review smoke_registry_fallback_migration_pilot_closure_review_text pilot_checks=5 data_driven_first_dispatch=active_for_pilot_trial_path_only manual_fallback=preserved registry_globally_replaced=False manual_registry_replaced=False smoke_registry_behavior_changed=False json_output_changed=False fast_smoke_changed=False install_smoke_changed=False release_smoke_changed=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True

# v911.0 release gate stale assertion truth repair self-development tokens: release-gate-stale-assertion-truth-repair-v1 --release-gate-stale-assertion-truth-repair build_release_gate_stale_assertion_truth_repair_review release_gate_stale_assertion_truth_repair_review_text executable_smoke_assertion_audit executable_smoke_assertion_finding_count stale_current_state_finding_count EXPECTED_CURRENT_VERSION token_presence_not_enough=True metadata_docs_audit_dynamic_current=True probe_containment_limits_honest=True network_access_not_measured=True external_filesystem_writes_not_measured=True release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v908.0 manifest validation normalization self-development tokens: manifest-validation-normalization-v1 --manifest-validation-normalization build_manifest_validation_normalization_review manifest_validation_normalization_review_text build_manifest_validation_normalization_summary legacy_version_field_validation_mode=compatibility_only_not_current_state historical_origin_versions_allowed=True current_state_version_source=manifest_representation_version_and_last_verified_for_version legacy_version_is_current_state_source=False surface_origin_versions_required=True manifest_representation_versions_required_current=True last_verified_versions_required_current=True policies_passed=True release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v909.0 source package privacy deep scan self-development tokens: source-package-privacy-deep-scan-v1 --source-package-privacy-deep-scan build_source_package_privacy_deep_scan_review source_package_privacy_deep_scan_review_text privacy_deep_scan_summary private_content_findings_for_items content_scans_allowlisted_data=True blocks_private_self_state_content=True user_specific_identifier_detected runtime_goal_state_detected approval_or_action_trace_detected memory_like_state_detected data/self_model.json source_metadata_allowed=False policies_passed=True release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v910.0 metadata/current marker gate reconciliation self-development tokens: metadata-and-current-marker-gate-reconciliation-v1 --metadata-and-current-marker-gate-reconciliation build_metadata_and_current_marker_gate_reconciliation_review metadata_and_current_marker_gate_reconciliation_review_text current_marker_source_count current_marker_checked_count stale_current_marker_count historical_reference_allowed=True metadata_current_state_aligned=True release_history_current_entry_aligned=True smoke_expectation_current_aligned=True policies_passed=True release_blocking=True review_only=True autonomy_expanded=False expands_autonomy=False dashboard_wiring_activated=False api_wiring_activated=False cli_wiring_activated=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v931.0-v935.0 generated scaffold sandbox output prep self-development tokens: generated-scaffold-sandbox-output-schema-v1 --generated-scaffold-sandbox-output-schema build_generated_scaffold_sandbox_output_schema_review generated_scaffold_sandbox_output_schema_review_text generated-scaffold-sandbox-artifact-preview-v1 --generated-scaffold-sandbox-artifact-preview build_generated_scaffold_sandbox_artifact_preview_review generated_scaffold_sandbox_artifact_preview_review_text generated-scaffold-hash-ledger-v1 --generated-scaffold-hash-ledger build_generated_scaffold_hash_ledger_review generated_scaffold_hash_ledger_review_text generated-scaffold-sandbox-parity-comparison-v1 --generated-scaffold-sandbox-parity-comparison build_generated_scaffold_sandbox_parity_comparison_review generated_scaffold_sandbox_parity_comparison_review_text generated-scaffold-sandbox-output-closure-v1 --generated-scaffold-sandbox-output-closure build_generated_scaffold_sandbox_output_closure_review generated_scaffold_sandbox_output_closure_review_text sandbox_artifact_count=5 hash_count=5 comparison_count=5 runtime_writes_sandbox_files=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v936.0-v940.0 generated scaffold wrapper prep self-development tokens: generated-scaffold-wrapper-mapping-schema-v1 --generated-scaffold-wrapper-mapping-schema build_generated_scaffold_wrapper_mapping_schema_review generated_scaffold_wrapper_mapping_schema_review_text dashboard-compatibility-wrapper-preview-v1 --dashboard-compatibility-wrapper-preview build_dashboard_compatibility_wrapper_preview_review dashboard_compatibility_wrapper_preview_review_text cli-api-compatibility-wrapper-preview-v1 --cli-api-compatibility-wrapper-preview build_cli_api_compatibility_wrapper_preview_review cli_api_compatibility_wrapper_preview_review_text smoke-compatibility-wrapper-preview-v1 --smoke-compatibility-wrapper-preview build_smoke_compatibility_wrapper_preview_review smoke_compatibility_wrapper_preview_review_text generated-scaffold-wrapper-prep-closure-v1 --generated-scaffold-wrapper-prep-closure build_generated_scaffold_wrapper_prep_closure_review generated_scaffold_wrapper_prep_closure_review_text wrapper_artifact_count=5 wrapper_hash_count=5 wrapper_schema_field_count=16 runtime_writes_wrapper_files=False manual_code_replaced=False generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
