from __future__ import annotations
"""v1381 evidence-linked read-only model of Eidolon's own source capabilities and limits."""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1381.8"
DENIED = {
    "self_change_authorized": False,
    "source_mutation_authorized": False,
    "project_mutation_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}
CAPABILITY_EVIDENCE = {
    "durable_campaigns": ("conscious_agent/durable_campaign_checkpoint.py", "tools/v1380_9_durable_campaign_checkpoint_tests.py"),
    "conflict_reconciliation": ("conscious_agent/conflict_reconciliation.py", "tools/v1377_9_conflict_reconciliation_checkpoint_tests.py"),
    "campaign_rollback": ("conscious_agent/campaign_rollback.py", "tools/v1378_9_campaign_rollback_checkpoint_tests.py"),
    "multi_day_continuity": ("conscious_agent/multi_day_continuity.py", "tools/v1379_9_multi_day_continuity_checkpoint_tests.py"),
    "verification_intelligence": ("conscious_agent/verification_intelligence_checkpoint.py", "tools/v1360_9_verification_intelligence_checkpoint_tests.py"),
    "diagnosis_and_repair": ("conscious_agent/diagnosis_repair_integration.py", "tools/v1370_9_diagnosis_repair_checkpoint_tests.py"),
}
LIMITS = (
    "no_independent_authority",
    "no_unrestricted_network_authority",
    "no_release_authority",
    "no_unreviewed_source_mutation",
    "native_windows_evidence_requires_windows",
    "evidence_scores_are_not_authority",
)
BOUNDARY_CATEGORIES = ("authority", "release", "secrets", "rollback", "evidence_verification")


def _d(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_self_model(*, source_root: str | Path, extra_capability_evidence: Mapping[str, Sequence[str]] | None = None) -> dict[str, Any]:
    root = Path(source_root).expanduser().resolve()
    try:
        from release_authority import WORKING_SOURCE_VERSION
    except ImportError:
        from release_authority import WORKING_SOURCE_VERSION  # type: ignore
    modules = sorted((root / "conscious_agent").glob("*.py"))
    if not modules:
        return {"ok": False, "status": "self_model_source_unavailable", "action_executed": False, **DENIED}
    module_rows = [{"module_name": p.stem, "path_digest": _d(p.relative_to(root).as_posix()), "source_digest": _file_digest(p)} for p in modules]
    registry: dict[str, Sequence[str]] = dict(CAPABILITY_EVIDENCE)
    for key, paths in (extra_capability_evidence or {}).items():
        registry[str(key)] = tuple(str(x) for x in paths)
    caps = []
    for name in sorted(registry):
        paths = list(registry[name])
        evidence = []
        for rel in paths:
            p = root / rel
            if p.is_file(): evidence.append({"path_digest": _d(rel), "artifact_digest": _file_digest(p), "artifact_kind": "test" if rel.startswith("tools/") else "source"})
        caps.append({"capability": name, "status": "evidence_present" if len(evidence) == len(paths) and evidence else "evidence_incomplete", "evidence_count": len(evidence), "evidence": evidence, "capability_digest": _d([name, evidence])})
    model = {
        "contract_version": CONTRACT_VERSION,
        "working_source_version": WORKING_SOURCE_VERSION,
        "source_root_digest": _d(str(root)),
        "module_count": len(module_rows),
        "module_manifest_digest": _d(module_rows),
        "capability_count": len(caps),
        "capabilities": caps,
        "known_limits": list(LIMITS),
        "known_limits_digest": _d(LIMITS),
        "protected_boundary_categories": list(BOUNDARY_CATEGORIES),
        "protected_boundary_categories_digest": _d(BOUNDARY_CATEGORIES),
        "claims_require_evidence": True,
        "missing_evidence_does_not_imply_capability": True,
        "raw_source_content_exposed": False,
        "read_only": True,
        "content_free": True,
        "action_executed": False,
        **DENIED,
    }
    model["self_model_digest"] = _d(model)
    return {"ok": True, "status": "self_model_ready", "self_model": model, "action_executed": False, **DENIED}


def compare_self_model_version(*, self_model: Mapping[str, Any], expected_self_model_digest: str, current_version: str) -> dict[str, Any]:
    row = dict(self_model); supplied = str(row.pop("self_model_digest", "")); valid = supplied == expected_self_model_digest and supplied == _d(row)
    if not valid: return {"ok": False, "status": "self_model_stale_or_tampered", "action_executed": False, **DENIED}
    stale = str(row.get("working_source_version")) != str(current_version)
    return {"ok": True, "status": "self_model_version_checked", "stale": stale, "modeled_version": row.get("working_source_version"), "current_version": current_version, "refresh_required": stale, "action_executed": False, **DENIED}


def process_self_model_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show self model", "inspect self model", "show eidolon self model"}: return {"active": False}
    rec = dict((project_state or {}).get("self_model") or {})
    return {"active": True, "ok": bool(rec), "status": "self_model_found" if rec else "self_model_missing", "self_model": rec, "action_executed": False, **DENIED}


__all__ = ["CONTRACT_VERSION", "CAPABILITY_EVIDENCE", "LIMITS", "BOUNDARY_CATEGORIES", "build_self_model", "compare_self_model_version", "process_self_model_control"]
