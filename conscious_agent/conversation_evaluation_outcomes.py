from __future__ import annotations

"""Deterministic v1087.2 classification of explicit evaluation observations.

Classification uses only operator-selected issue domains, severities, and
reproducibility flags. It never reads note text or conversation content and does
not call a provider or assign an autonomous quality score.
"""

import hashlib
import json
from typing import Any, Iterable, Mapping

from conversation_daily_evaluation_protocol import ISSUE_DOMAINS, ISSUE_SEVERITIES

OUTCOME_CLASSIFICATION_SCHEMA_VERSION = "1"
OUTCOME_CLASSES = (
    "successful_session",
    "minor_friction",
    "reproducible_defect",
    "provider_failure",
    "operator_aborted",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _normalized_observations(observations: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in list(observations or ()):
        if not isinstance(raw, Mapping):
            continue
        domain = str(raw.get("issue_domain") or "none").strip().lower()
        severity = str(raw.get("severity") or "none").strip().lower()
        if domain not in ISSUE_DOMAINS:
            domain = "none"
        if severity not in ISSUE_SEVERITIES:
            severity = "none"
        rows.append({
            "issue_domain": domain,
            "severity": severity,
            "reproducible": bool(raw.get("reproducible")),
        })
    return rows


def classify_evaluation_outcome(
    *,
    evaluation_state: str,
    observations: Iterable[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    state = str(evaluation_state or "active").strip().lower()
    rows = _normalized_observations(observations)
    domain_counts = {domain: 0 for domain in ISSUE_DOMAINS}
    severity_counts = {severity: 0 for severity in ISSUE_SEVERITIES}
    reproducible_count = 0
    for row in rows:
        domain_counts[row["issue_domain"]] += 1
        severity_counts[row["severity"]] += 1
        reproducible_count += int(row["reproducible"])

    provider_failure = any(
        row["issue_domain"] == "provider_transport" and row["severity"] in {"major", "blocking"}
        for row in rows
    )
    reproducible_defect = any(
        row["reproducible"] and row["issue_domain"] not in {"none", "operator"}
        for row in rows
    )
    friction = any(
        row["issue_domain"] != "none" or row["severity"] != "none"
        for row in rows
    )

    if state == "aborted":
        outcome = "operator_aborted"
        reason = "explicit_operator_abort"
    elif provider_failure:
        outcome = "provider_failure"
        reason = "explicit_provider_transport_failure"
    elif reproducible_defect:
        outcome = "reproducible_defect"
        reason = "explicit_reproducible_issue"
    elif friction:
        outcome = "minor_friction"
        reason = "explicit_nonreproducible_friction"
    else:
        outcome = "successful_session"
        reason = "no_explicit_issue_marked"

    stable_evidence = {
        "evaluation_state": state,
        "observation_count": len(rows),
        "domain_counts": domain_counts,
        "severity_counts": severity_counts,
        "reproducible_count": reproducible_count,
    }
    return {
        "type": "desktop_alpha_daily_evaluation_outcome",
        "schema_version": OUTCOME_CLASSIFICATION_SCHEMA_VERSION,
        "outcome": outcome,
        "reason": reason,
        "observation_count": len(rows),
        "domain_counts": domain_counts,
        "severity_counts": severity_counts,
        "reproducible_count": reproducible_count,
        "model_quality_issue_count": domain_counts["model_quality"],
        "provider_transport_issue_count": domain_counts["provider_transport"],
        "interface_issue_count": domain_counts["interface"],
        "session_continuity_issue_count": domain_counts["session_continuity"],
        "classification_digest": _digest(stable_evidence),
        "note_text_inspected": False,
        "transcript_inspected": False,
        "autonomous_scoring": False,
        "provider_invoked": False,
        "writes_state": False,
        "release_certified": False,
        "promotion_performed": False,
    }
