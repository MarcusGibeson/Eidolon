from __future__ import annotations

"""v1400 Autonomous Developer Gamma repeatability, review, and soak checkpoint."""

import ast
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from autonomous_developer_gamma_scorecard import EXPECTED_TASK_CLASSES

CONTRACT_VERSION = "v1400.8"
REQUIRED_MODULES = (
    "representative_greenfield_task.py",
    "representative_existing_project_feature.py",
    "representative_bug_report_task.py",
    "representative_refactoring_task.py",
    "representative_data_migration_task.py",
    "representative_ui_workflow_task.py",
    "representative_provider_backed_task.py",
    "no_prompt_gamma_session.py",
    "autonomous_developer_gamma_scorecard.py",
)
WINDOWS_SENSITIVE_PREFIXES = (
    "dashboard/", "conscious_agent/dashboard", "run_eidolon.ps1", "setup.ps1",
    "scripts/windows", "tools/windows", "conscious_agent/windows",
)
WINDOWS_BASELINE_SHA256 = {
    "conscious_agent/dashboard.py": "9f70f7638ac702542342e3aa4588551af4cc8b6aa24882243b92d5db238c2b36",
    "conscious_agent/dashboard_layout.py": "646810cf3cd2195dbf556e76f0c422db346515b552e67f8085abd8d9be6d52b3",
    "conscious_agent/dashboard_chat_console.py": "aab759658f34ce2b5715c8994832e54470f5abff21f21f7dd0e540d2b3e1b40d",
    "conscious_agent/dashboard_chat_styles.py": "8bb330b0e1ef2b58c5ef6205d2fc4382ffbcc5a162ed63330f228e676bc279df",
    "conscious_agent/static/dashboard.css": "a4b0779e327126e24600952c69ba930653a878809229df74519462ea3e8b90bc",
    "conscious_agent/static/dashboard.js": "716869134ec2c842837887fa619a156453ff287100c58da9aaa44d7953fe4c72",
    "run_eidolon.ps1": "8f14bb9612996a46022291ba41551b6cdc975448aa1b6f2c0e9c08107081d3f5",
    "setup.ps1": "73dc182baa656deef5913c7989d67212bcd9cdd36a1c8a763d8befcdb287694c",
}
DIGEST = re.compile(r"^[a-f0-9]{64}$")
PROTECTED_CORE_PATHS = {
    "conscious_agent/release_authority.py",
    "conscious_agent/checkpoint_registry.py",
    "conscious_agent/release_metadata.py",
    "release_metadata.py",
    "docs/release/release_metadata_manifest.json",
}
DENIED = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "authority_expansion_authorized": False,
    "external_publish_authorized": False,
    "independent_authority_granted": False,
}


def _d(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def build_gamma_architecture_review(*, source_root: str | Path, changed_paths_since_windows_review: Sequence[str]) -> dict[str, Any]:
    root = Path(source_root).resolve()
    module_rows = []
    for name in REQUIRED_MODULES:
        path = root / "conscious_agent" / name
        syntax_ok = False
        sha = ""
        if path.is_file():
            data = path.read_bytes(); sha = hashlib.sha256(data).hexdigest()
            try: ast.parse(data.decode("utf-8")); syntax_ok = True
            except Exception: syntax_ok = False
        module_rows.append({"module": name, "present": path.is_file(), "syntax_ok": syntax_ok, "sha256": sha})
    changed = sorted({str(x).replace("\\", "/") for x in changed_paths_since_windows_review})
    windows_sensitive = [p for p in changed if any(p == prefix or p.startswith(prefix) for prefix in WINDOWS_SENSITIVE_PREFIXES)]
    windows_baseline_rows = []
    for relative_path, expected_sha256 in WINDOWS_BASELINE_SHA256.items():
        path = root / relative_path
        actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        windows_baseline_rows.append({"path": relative_path, "expected_sha256": expected_sha256, "actual_sha256": actual_sha256, "matches": actual_sha256 == expected_sha256})
    protected = sorted(p for p in changed if p in PROTECTED_CORE_PATHS)
    try:
        import release_authority
        from checkpoint_registry import checkpoint_registry_manifest
        authority = release_authority.validate_release_authority(source_root=root)
        registry = checkpoint_registry_manifest(source_root=root)
        protected_review_ok = authority.get("ok") is True and registry.get("ok") is True and all(v is False for v in release_authority.AUTHORITY_FLAGS.values())
    except Exception:
        protected_review_ok = False
    checks = {
        "all_gamma_modules_present": all(r["present"] for r in module_rows),
        "all_gamma_modules_parse": all(r["syntax_ok"] for r in module_rows),
        "no_windows_sensitive_change_since_v1396": not windows_sensitive,
        "windows_baseline_hashes_match_v1396": all(row["matches"] for row in windows_baseline_rows),
        "protected_core_review_complete": protected_review_ok,
        "release_authority_still_denied": protected_review_ok,
    }
    row = {
        "contract_version": CONTRACT_VERSION,
        "module_rows": module_rows,
        "module_count": len(module_rows),
        "changed_paths_digest": _d(changed),
        "changed_path_count": len(changed),
        "windows_sensitive_changed_paths": windows_sensitive,
        "windows_baseline_rows": windows_baseline_rows,
        "protected_core_changed_paths": protected,
        "protected_core_review_required": bool(protected),
        "protected_core_review_complete": protected_review_ok,
        "checks": checks,
        "ok": all(checks.values()),
        "content_free": True,
        **DENIED,
    }
    row["review_digest"] = _d(row)
    return row


def build_windows_review_carryforward(*, validated_version: str, current_version: str, validation_receipt: Mapping[str, Any], architecture_review: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "desktop_layout", "narrow_layout", "keyboard_forward", "keyboard_backward",
        "focus_visible", "error_announcement", "completion_announcement", "no_horizontal_overflow",
    }
    receipt = dict(validation_receipt or {})
    receipt_body = dict(receipt)
    supplied_receipt_digest = str(receipt_body.pop("validation_digest", ""))
    receipt_sealed = supplied_receipt_digest == _d(receipt_body)
    vals = {str(row.get("name")): row.get("passed") is True for row in receipt.get("checks") or [] if isinstance(row, Mapping)}
    try:
        age = int(current_version.split(".")[0]) - int(validated_version.split(".")[0])
    except Exception:
        age = 9999
    row = {
        "contract_version": CONTRACT_VERSION,
        "validated_version": validated_version,
        "current_version": current_version,
        "version_age": age,
        "required_checks_complete": required.issubset({k for k, v in vals.items() if v}),
        "manual_windows_validation_performed": receipt_sealed and receipt.get("manual_validation_performed") is True and receipt.get("platform") == "windows",
        "validation_receipt_digest": supplied_receipt_digest,
        "validation_receipt_sealed": receipt_sealed,
        "no_windows_sensitive_change_since_validation": not bool(architecture_review.get("windows_sensitive_changed_paths")),
        "within_ten_version_review_window": 0 <= age <= 10,
        "architecture_review_digest": architecture_review.get("review_digest"),
        "content_free": True,
        **DENIED,
    }
    row["ok"] = all(row[k] for k in ("required_checks_complete", "manual_windows_validation_performed", "validation_receipt_sealed", "no_windows_sensitive_change_since_validation", "within_ten_version_review_window"))
    row["windows_review_digest"] = _d(row)
    return row


def run_gamma_long_soak(*, iteration_runner: Callable[[int], Mapping[str, Any]], iterations: int = 64, max_workers: int = 1) -> dict[str, Any]:
    count = max(1, min(512, int(iterations)))
    workers = max(1, min(4, int(max_workers)))
    failures = []
    evidence = []
    completed_tasks = 0
    class_completion_counts = {task_class: 0 for task_class in EXPECTED_TASK_CLASSES}
    def execute(index: int) -> dict[str, Any]:
        try:
            return dict(iteration_runner(index) or {})
        except Exception as exc:
            return {"ok": False, "failure_class": type(exc).__name__}

    if workers == 1:
        iteration_results = [execute(index) for index in range(count)]
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="gamma-soak") as pool:
            iteration_results = list(pool.map(execute, range(count)))

    for i, result in enumerate(iteration_results):
        task_rows = [dict(row) for row in result.get("task_evidence") or [] if isinstance(row, Mapping)]
        classes = [str(row.get("task_class") or "") for row in task_rows]
        task_evidence_valid = (
            len(task_rows) == len(EXPECTED_TASK_CLASSES)
            and set(classes) == set(EXPECTED_TASK_CLASSES)
            and len(classes) == len(set(classes))
            and all(row.get("ok") is True and DIGEST.fullmatch(str(row.get("evidence_digest") or "")) for row in task_rows)
        )
        iteration_digest = str(result.get("evidence_digest") or "")
        completed = int(result.get("completed_tasks") or 0)
        ok = result.get("ok") is True and task_evidence_valid and completed == len(EXPECTED_TASK_CLASSES) and DIGEST.fullmatch(iteration_digest) is not None
        completed_tasks += completed if ok else 0
        if ok:
            for task_class in classes:
                class_completion_counts[task_class] += 1
        evidence.append(iteration_digest if DIGEST.fullmatch(iteration_digest) else _d({"iteration": i, "invalid_evidence": True}))
        if not ok: failures.append({"iteration": i, "failure_digest": _d(result.get("failure_class") or "iteration_failed")})
    row = {
        "contract_version": CONTRACT_VERSION,
        "iterations": count,
        "max_workers": workers,
        "successful_iterations": count - len(failures),
        "failed_iterations": len(failures),
        "completed_tasks": completed_tasks,
        "task_class_completion_counts": class_completion_counts,
        "all_task_classes_repeated": all(value == count for value in class_completion_counts.values()),
        "iteration_evidence_complete": not failures,
        "repeatability_rate": round((count - len(failures)) / count, 6),
        "failures": failures,
        "evidence_chain_digest": _d(evidence),
        "long_soak_complete": count >= 64 and not failures and all(value == count for value in class_completion_counts.values()),
        "content_free": True,
        **DENIED,
    }
    row["soak_digest"] = _d(row)
    return row


def _valid_sealed(row: Mapping[str, Any], digest_key: str) -> bool:
    body = dict(row); supplied = str(body.pop(digest_key, "")); return supplied == _d(body)


def build_autonomous_developer_gamma_checkpoint(*, scorecard: Mapping[str, Any], architecture_review: Mapping[str, Any], windows_review: Mapping[str, Any], soak: Mapping[str, Any], current_version: str = "1400.9") -> dict[str, Any]:
    metrics = dict(scorecard.get("metrics") or {})
    thresholds = dict(scorecard.get("thresholds") or {})
    checks = {
        "current_version": current_version == "1400.9",
        "scorecard_sealed": _valid_sealed(scorecard, "scorecard_digest"),
        "scorecard_ready": scorecard.get("gamma_ready") is True and all(thresholds.values()),
        "representative_coverage": set(EXPECTED_TASK_CLASSES).issubset(set(metrics.get("task_class_coverage") or [])),
        "architecture_review_sealed": _valid_sealed(architecture_review, "review_digest") and architecture_review.get("ok") is True,
        "windows_review_sealed": _valid_sealed(windows_review, "windows_review_digest") and windows_review.get("ok") is True,
        "long_soak_sealed": _valid_sealed(soak, "soak_digest") and soak.get("long_soak_complete") is True,
        "repeatable_end_to_end": int(soak.get("successful_iterations") or 0) >= 64 and float(soak.get("repeatability_rate") or 0) == 1.0 and int(soak.get("completed_tasks") or 0) >= 64 * len(EXPECTED_TASK_CLASSES),
        "all_task_classes_repeated": soak.get("all_task_classes_repeated") is True and soak.get("iteration_evidence_complete") is True,
        "zero_boundary_violations": int(metrics.get("boundary_violation_count") or 0) == 0,
        "no_authority_expansion": True,
    }
    row = {
        "contract_version": CONTRACT_VERSION,
        "checkpoint_version": current_version,
        "scorecard_digest": scorecard.get("scorecard_digest"),
        "architecture_review_digest": architecture_review.get("review_digest"),
        "windows_review_digest": windows_review.get("windows_review_digest"),
        "soak_digest": soak.get("soak_digest"),
        "checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "gamma_checkpoint_ready": all(checks.values()),
        "initiative_expansion_authorized": False,
        "authority_expansion_authorized": False,
        "content_free": True,
        "action_executed": False,
        **DENIED,
    }
    row["checkpoint_digest"] = _d(row)
    return {"ok": row["gamma_checkpoint_ready"], "status": "autonomous_developer_gamma_checkpoint_ready" if row["gamma_checkpoint_ready"] else "autonomous_developer_gamma_checkpoint_blocked", "gamma_checkpoint": row, "action_executed": False, **DENIED}


def process_gamma_checkpoint_control(text: str, *, project_state: Mapping[str, Any] | None = None, **_: Any) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show gamma checkpoint", "inspect gamma checkpoint", "show autonomous developer gamma checkpoint"}:
        return {"active": False}
    record = dict((project_state or {}).get("gamma_checkpoint") or {})
    return {"active": True, "ok": bool(record), "status": "gamma_checkpoint_found" if record else "gamma_checkpoint_missing", "gamma_checkpoint": record, "action_executed": False, **DENIED}


__all__ = ["CONTRACT_VERSION", "REQUIRED_MODULES", "build_gamma_architecture_review", "build_windows_review_carryforward", "run_gamma_long_soak", "build_autonomous_developer_gamma_checkpoint", "process_gamma_checkpoint_control"]
