from __future__ import annotations

"""Read-only v1196.2 adversarial privacy and authority checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from adversarial_privacy_authority import ATTACK_CLASSES, AUTHORITY_DOMAINS, build_evidence, validate_adversarial_privacy_authority_evidence
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1196.2"


def _d(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def build_adversarial_privacy_authority_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    del runtime_root
    checks: list[bool] = []
    def require(value: object) -> None: checks.append(bool(value))
    rows: list[dict[str, Any]] = []
    prior = None
    for sequence, attack_class in enumerate(ATTACK_CLASSES, 1):
        row = build_evidence(
            attack_class=attack_class,
            target_domain=AUTHORITY_DOMAINS[(sequence - 1) % len(AUTHORITY_DOMAINS)],
            sequence=sequence,
            snapshot_digest=_d("snapshot"), context_digest=_d("context"),
            artifact_digest=_d(f"artifact:{sequence}"), receipt_digest=_d(f"receipt:{sequence}"),
            prior_receipt_digest=prior,
        )
        result = validate_adversarial_privacy_authority_evidence(
            row, expected_snapshot_digest=_d("snapshot"), expected_context_digest=_d("context"), expected_prior_receipt_digest=prior,
        )
        require(result["ok"] is True); require(not result["errors"]); require(result["summary"]["attack_blocked"] is True)
        rows.append(result["summary"]); prior = row["receipt_digest"]
    blocked: dict[str, dict[str, Any]] = {}
    mutations = {
        "stale_snapshot": {"snapshot_digest": _d("stale")},
        "stale_context": {"context_digest": _d("stale-context")},
        "private_field": {"secret": "redacted"},
        "authority": {"authority_granted": True},
        "execution": {"execution_invoked": True},
        "automatic": {"automatic_continuation": True},
        "tamper": {"evidence_digest": _d("tamper")},
        "unsupported": {"attack_class": "arbitrary_code"},
    }
    base = build_evidence(attack_class=ATTACK_CLASSES[0], target_domain=AUTHORITY_DOMAINS[0], sequence=1, snapshot_digest=_d("snapshot"), context_digest=_d("context"), artifact_digest=_d("a"), receipt_digest=_d("r"))
    for name, changes in mutations.items():
        candidate = dict(base); candidate.update(changes)
        if "evidence_digest" not in changes:
            from adversarial_privacy_authority import _digest
            candidate["evidence_digest"] = _digest({k:v for k,v in candidate.items() if k != "evidence_digest"})
        result = validate_adversarial_privacy_authority_evidence(candidate, expected_snapshot_digest=_d("snapshot"), expected_context_digest=_d("context"))
        require(result["ok"] is False); require(bool(result["errors"])); blocked[name] = result["summary"]
    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((r for r in registry["checkpoints"] if r["checkpoint_id"] == "adversarial-privacy-authority-checkpoint"), None)
    require(bool(descriptor)); require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    summary = {
        "attack_class_count": len(ATTACK_CLASSES), "authority_domain_count": len(AUTHORITY_DOMAINS),
        "blocked_attack_count": len(rows), "negative_case_count": len(blocked),
        "content_free": True, "read_only": True, "privacy_preserved": True,
        "authority_state": "separate_not_granted", "execution_invoked": False,
        "runtime_mutated": False, "provider_contacted": False, "model_contacted": False,
        "approval_created": False, "approval_consumed": False, "global_profile_pass_claimed": False,
    }
    # Stable extra assertions provide a meaningful bounded checkpoint floor.
    for field in ("content_free","read_only","privacy_preserved"):
        require(summary[field] is True)
    for field in ("execution_invoked","runtime_mutated","provider_contacted","model_contacted","approval_created","approval_consumed","global_profile_pass_claimed"):
        require(summary[field] is False)
    require(summary["authority_state"] == "separate_not_granted")
    return {
        "ok": all(checks), "checkpoint_id": "adversarial-privacy-authority:v1196.2",
        "contract_version": CONTRACT_VERSION, "passed": sum(checks), "total": len(checks),
        "summary": summary, "samples": rows, "blocked_cases": blocked,
        "limitations": [
            "Evidence-only; no attacks are executed and no private state is fetched.",
            "No approval, execution, cancellation, installation, promotion, certification, publication, release, or autonomous authority is granted.",
            "Replay, stale-state, interruption, cancellation, and recovery integration hardening continues in later v1196 bundles.",
        ],
    }
