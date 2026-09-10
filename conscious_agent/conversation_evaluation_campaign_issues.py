from __future__ import annotations

"""Privacy-safe v1088.3 issue aggregation for operator evaluation campaigns.

The aggregator reads only redacted campaign and daily-evaluation summaries. It
never inspects transcript text, prompts, private notes, campaign objectives, or
provider payloads. Counts are descriptive evidence only: no priority, score,
winner, release recommendation, or automatic task is produced.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation import DailyEvaluationError, load_daily_evaluation
from conversation_daily_evaluation_protocol import ISSUE_DOMAINS, ISSUE_SEVERITIES
from conversation_evaluation_outcomes import OUTCOME_CLASSES
from conversation_evaluation_campaign import EvaluationCampaignError, load_evaluation_campaign

EVALUATION_CAMPAIGN_ISSUE_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _empty_severity_counts() -> dict[str, int]:
    return {severity: 0 for severity in ISSUE_SEVERITIES}


def build_evaluation_campaign_issue_aggregation(campaign_id: str) -> dict[str, Any]:
    campaign = load_evaluation_campaign(campaign_id)
    refs = [row for row in list(campaign.get("evaluation_refs") or ()) if isinstance(row, Mapping)]
    domain_counts = {domain: 0 for domain in ISSUE_DOMAINS}
    severity_counts = _empty_severity_counts()
    outcome_counts = {outcome: 0 for outcome in OUTCOME_CLASSES}
    outcome_counts["unclassified"] = 0
    domain_evaluations: dict[str, set[str]] = {domain: set() for domain in ISSUE_DOMAINS}
    domain_reproducible_counts = {domain: 0 for domain in ISSUE_DOMAINS}
    evidence_rows: list[dict[str, Any]] = []
    affected_evaluations: set[str] = set()
    reproducible_evaluations: set[str] = set()
    missing_evaluation_count = 0
    total_observations = 0
    reproducible_observation_count = 0

    for ref in refs:
        evaluation_id = str(ref.get("evaluation_id") or "")
        try:
            summary = load_daily_evaluation(evaluation_id)
        except DailyEvaluationError:
            missing_evaluation_count += 1
            evidence_rows.append({
                "evaluation_id": evaluation_id,
                "availability": "missing",
                "evaluation_revision": 0,
                "evaluation_state": "unknown",
                "outcome": "unclassified",
                "observation_count": 0,
                "issue_domains": [],
                "severity_counts": _empty_severity_counts(),
                "reproducible_observation_count": 0,
                "observation_evidence_digest": "",
            })
            continue

        observations = [row for row in list(summary.get("observations") or ()) if isinstance(row, Mapping)]
        evaluation_severities = _empty_severity_counts()
        evaluation_domains: set[str] = set()
        evaluation_reproducible = 0
        total_observations += len(observations)
        for observation in observations:
            domain = str(observation.get("issue_domain") or "none")
            severity = str(observation.get("severity") or "none")
            if domain not in domain_counts:
                domain = "none"
            if severity not in severity_counts:
                severity = "none"
            domain_counts[domain] += 1
            severity_counts[severity] += 1
            evaluation_severities[severity] += 1
            domain_evaluations[domain].add(evaluation_id)
            evaluation_domains.add(domain)
            if bool(observation.get("reproducible")):
                reproducible_observation_count += 1
                evaluation_reproducible += 1
                domain_reproducible_counts[domain] += 1

        nonempty_domains = sorted(domain for domain in evaluation_domains if domain != "none")
        if nonempty_domains:
            affected_evaluations.add(evaluation_id)
        if evaluation_reproducible:
            reproducible_evaluations.add(evaluation_id)
        outcome_record = summary.get("outcome") if isinstance(summary.get("outcome"), Mapping) else {}
        outcome = str(outcome_record.get("outcome") or outcome_record.get("outcome_code") or "unclassified")
        if outcome not in outcome_counts:
            outcome = "unclassified"
        outcome_counts[outcome] += 1
        evidence_rows.append({
            "evaluation_id": evaluation_id,
            "availability": "available",
            "evaluation_revision": max(0, int(summary.get("revision") or 0)),
            "evaluation_state": str(summary.get("state") or "active"),
            "outcome": outcome,
            "observation_count": len(observations),
            "issue_domains": nonempty_domains,
            "severity_counts": evaluation_severities,
            "reproducible_observation_count": evaluation_reproducible,
            "observation_evidence_digest": str(summary.get("observation_evidence_digest") or ""),
        })

    issue_groups = [
        {
            "issue_domain": domain,
            "observation_count": domain_counts[domain],
            "affected_evaluation_count": len(domain_evaluations[domain]),
            "reproducible_observation_count": domain_reproducible_counts[domain],
        }
        for domain in ISSUE_DOMAINS
        if domain != "none" and domain_counts[domain] > 0
    ]
    stable_evidence = {
        "campaign_id": str(campaign.get("campaign_id") or ""),
        "campaign_revision": max(0, int(campaign.get("revision") or 0)),
        "evaluation_count": len(refs),
        "missing_evaluation_count": missing_evaluation_count,
        "total_observations": total_observations,
        "affected_evaluation_count": len(affected_evaluations),
        "reproducible_evaluation_count": len(reproducible_evaluations),
        "reproducible_observation_count": reproducible_observation_count,
        "issue_domain_counts": domain_counts,
        "severity_counts": severity_counts,
        "outcome_counts": outcome_counts,
        "issue_groups": issue_groups,
        "evidence_rows": evidence_rows,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_issue_aggregation",
        "schema_version": EVALUATION_CAMPAIGN_ISSUE_SCHEMA_VERSION,
        **stable_evidence,
        "issue_aggregation_digest": _digest(stable_evidence),
        "descriptive_counts_only": True,
        "priority_assigned": False,
        "autonomous_prioritization": False,
        "automatic_task_created": False,
        "automatic_follow_up_created": False,
        "statistical_significance_claimed": False,
        "transcript_inspected": False,
        "prompt_inspected": False,
        "private_notes_inspected": False,
        "private_campaign_plan_inspected": False,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def campaign_issue_aggregation_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "campaign_label", "objective", "content", "text", "message", "messages",
        "user_message", "assistant_response", "transcript", "prompt", "note", "notes",
        "temporary_instruction", "pinned_context", "queued_operator_intent", "provider_payload",
        "credentials", "vectors", "embedding", "receipt", "receipts", "hidden_reasoning",
        "chain_of_thought",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
