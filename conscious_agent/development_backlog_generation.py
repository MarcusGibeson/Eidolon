from __future__ import annotations

"""v1262.3-v1262.5 integration from v1261 assessments to bounded backlog artifacts."""

from pathlib import Path
from typing import Any, Iterable, Mapping

from development_backlog_generation_foundations import BACKLOG_DENIED_AUTHORITY, build_backlog_from_assessment, public_development_backlog, validate_development_backlog
from evidence_based_project_inspection import build_evidence_based_project_assessment

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1262.5"


def generate_development_backlog(source_root: str | Path, *, external_evidence: Iterable[Mapping[str, Any]] = (), max_items: int = 32) -> dict[str, Any]:
    assessment = build_evidence_based_project_assessment(source_root, external_evidence=external_evidence)
    backlog = build_backlog_from_assessment(assessment, max_items=max_items)
    backlog["integration_contract_version"] = CONTRACT_VERSION
    backlog["assessment_generated_in_same_read_only_pass"] = True
    backlog["backlog_is_candidate_work_only"] = True
    backlog["priority_selection_deferred_to_v1263"] = True
    # reseal after integration-only flags are added
    import hashlib, json
    backlog["backlog_digest"] = hashlib.sha256(json.dumps({k:v for k,v in backlog.items() if k!="backlog_digest"}, sort_keys=True, separators=(",",":"), ensure_ascii=True, default=str).encode()).hexdigest()
    return backlog


def inspect_development_backlog(source_root: str | Path, *, external_evidence: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    backlog = generate_development_backlog(source_root, external_evidence=external_evidence)
    validation = validate_development_backlog(backlog)
    public = public_development_backlog(backlog)
    return {"ok": bool(validation.get("ok")), "status": "development_backlog_inspection_ready" if validation.get("ok") else "development_backlog_inspection_invalid",
            "validation": validation, "public_backlog": public, "backlog_digest": backlog.get("backlog_digest", ""), "read_only": True, **BACKLOG_DENIED_AUTHORITY}


__all__ = ["CONTRACT_VERSION", "generate_development_backlog", "inspect_development_backlog"]
