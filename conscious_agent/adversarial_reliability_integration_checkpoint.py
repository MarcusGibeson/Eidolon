from __future__ import annotations
"""Read-only v1196.8 adversarial reliability and integration checkpoint."""
import hashlib
from pathlib import Path
from typing import Any
from adversarial_reliability_integration import *
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1196.8"
_CHECKPOINT_ID = "adversarial-reliability-integration-checkpoint"


def _h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def build_adversarial_reliability_integration_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    del runtime_root
    checks: list[bool] = []
    def req(value: object) -> None: checks.append(bool(value))
    snapshot, context, evidence, authority = map(_h, ("snapshot", "context", "evidence", "authority"))
    prior = None
    samples = []
    for index, event_class in enumerate(EVENT_CLASSES, 1):
        event = build_reliability_event(
            event_id=f"event:{index}", event_class=event_class,
            surface=SURFACES[(index - 1) % len(SURFACES)], sequence=index,
            snapshot_digest=snapshot, context_digest=context, evidence_digest=evidence,
            authority_digest=authority, prior_event_digest=prior,
            foreground_latency_ms=index * 5, latency_budget_ms=250,
        )
        out = inspect_reliability_event(
            event=event, expected_snapshot_digest=snapshot, expected_context_digest=context,
            expected_evidence_digest=evidence, expected_authority_digest=authority,
            expected_prior_event_digest=prior,
        )
        for value in (out["ok"], out["exact_lineage_verified"], out["original_evidence_preserved"], out["foreground_available"]): req(value)
        for field in ("automatic_recovery_executed", "automatic_retry_executed", "cancellation_executed", "execution_invoked", "runtime_mutated", "provider_contacted", "authority_granted", "global_profile_pass_claimed"): req(out[field] is False)
        samples.append(out)
        prior = out["reliability_receipt_digest"]
    base = build_reliability_event(
        event_id="negative", event_class=EVENT_CLASSES[0], surface=SURFACES[0], sequence=1,
        snapshot_digest=snapshot, context_digest=context, evidence_digest=evidence,
        authority_digest=authority, foreground_latency_ms=1, latency_budget_ms=250,
    )
    mutations = {
        "stale_snapshot": ("snapshot_digest", _h("stale")),
        "stale_context": ("context_digest", _h("stale")),
        "stale_evidence": ("evidence_digest", _h("stale")),
        "stale_authority": ("authority_digest", _h("stale")),
        "latency": ("foreground_latency_ms", 251),
        "foreground_block": ("foreground_available", False),
        "evidence_loss": ("original_evidence_preserved", False),
        "recovery": ("automatic_recovery_requested", True),
        "retry": ("automatic_retry_requested", True),
        "cancellation": ("cancellation_executed", True),
        "execution": ("execution_invoked", True),
        "runtime": ("runtime_mutated", True),
        "provider": ("provider_contacted", True),
        "approval": ("approval_consumed", True),
        "authority": ("authority_granted", True),
        "global_pass": ("global_profile_pass_claimed", True),
    }
    blocked = {}
    from adversarial_reliability_integration import _digest
    for name, (field, value) in mutations.items():
        event = dict(base); event[field] = value
        body = dict(event); body.pop("event_digest", None); event["event_digest"] = _digest(body)
        out = inspect_reliability_event(
            event=event, expected_snapshot_digest=snapshot, expected_context_digest=context,
            expected_evidence_digest=evidence, expected_authority_digest=authority,
        )
        req(not out["ok"]); req(bool(out["errors"])); req(out["execution_invoked"] is False); req(out["authority_granted"] is False)
        blocked[name] = out
    tampered = dict(base); tampered["surface"] = SURFACES[1]
    tamper_out = inspect_reliability_event(event=tampered, expected_snapshot_digest=snapshot, expected_context_digest=context, expected_evidence_digest=evidence, expected_authority_digest=authority)
    req(not tamper_out["ok"]); req("event_tamper" in tamper_out["errors"]); blocked["tamper"] = tamper_out
    private = dict(base); private["prompt"] = "forbidden"
    body = dict(private); body.pop("event_digest", None); private["event_digest"] = _digest(body)
    private_out = inspect_reliability_event(event=private, expected_snapshot_digest=snapshot, expected_context_digest=context, expected_evidence_digest=evidence, expected_authority_digest=authority)
    req(not private_out["ok"]); req(any(x.startswith("private_field:") for x in private_out["errors"])); blocked["private"] = private_out
    privacy = package_privacy_summary_for_root(source); req(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((item for item in registry["checkpoints"] if item["checkpoint_id"] == _CHECKPOINT_ID), None)
    req(bool(descriptor)); req((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    summary = {
        "event_class_count": len(EVENT_CLASSES), "surface_count": len(SURFACES),
        "sample_count": len(samples), "negative_case_count": len(blocked),
        "content_free": True, "read_only": True, "foreground_available": True,
        "original_evidence_preserved": True, "automatic_recovery_executed": False,
        "automatic_retry_executed": False, "cancellation_executed": False,
        "execution_invoked": False, "runtime_mutated": False, "provider_contacted": False,
        "authority_state": "separate_not_granted", "authority_granted": False,
        "global_profile_pass_claimed": False,
    }
    return {
        "ok": all(checks), "checkpoint_id": "adversarial-reliability-integration:v1196.8",
        "contract_version": CONTRACT_VERSION, "passed": sum(checks), "total": len(checks),
        "summary": summary, "samples": samples, "blocked_cases": blocked,
        "limitations": [
            "Evidence-only; no attack, recovery, retry, cancellation, execution, provider contact, or mutation occurs.",
            "No approval or authority is created or consumed.",
            "The consolidated v1196.9 checkpoint remains deferred.",
        ],
    }
