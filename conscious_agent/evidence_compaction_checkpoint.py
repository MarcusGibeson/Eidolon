from __future__ import annotations

"""Read-only v1192.9 Bounded Evidence Compaction checkpoint.

Consolidates deterministic evidence compaction, exact expansion and equivalence,
operator review, and replay/interruption/privacy reliability evidence. The
checkpoint reads source contracts only and does not compact retained runtime
evidence, replace originals, execute recovery, or grant authority.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from bounded_evidence_compaction import create_evidence_record, compact_evidence, expand_compaction, public_compaction_summary, verify_compaction_equivalence
from bounded_evidence_compaction_checkpoint import build_bounded_evidence_compaction_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from evidence_compaction_reliability import assess_compaction_reliability, create_reliability_record, public_reliability_summary
from evidence_compaction_reliability_checkpoint import build_evidence_compaction_reliability_checkpoint
from evidence_compaction_review import create_compaction_review, create_compaction_review_request, public_compaction_review_summary, review_compaction
from evidence_compaction_review_checkpoint import build_evidence_compaction_review_checkpoint
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1192.9"
_CHECKPOINT_ID = "bounded-evidence-compaction:v1192.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_LIMITATIONS = (
    "The checkpoint validates caller-supplied, content-free evidence contracts and does not compact retained runtime evidence.",
    "Approved review presents retention eligibility only; original evidence is not replaced, deleted, or rewritten.",
    "Interruption, restart, outage, replay, and recovery remain evidence-only and never trigger automatic recovery or execution.",
    "No approval, rollback, provider/model operation, thread, process, runtime mutation, installation, promotion, publication, release, or authority is invoked.",
    "Verifier ownership and inherited historical profile debt remain for v1193; Desktop Codex and native-provider review remain scheduled for v1200.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        count += 1
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), count


def _sample_records(snapshot_digest: str, context_digest: str) -> list[dict[str, Any]]:
    domains = (
        "conversation", "cognition", "reasoning", "planning", "campaign",
        "approval", "action", "result", "learning",
    )
    kinds = ("observation", "observation", "decision", "decision", "transition", "decision", "transition", "result", "learning")
    outcomes = ("retained", "revised", "retained", "suspended", "completed", "retained", "completed", "completed", "revised")
    uncertainties = ("none", "bounded", "conflicted", "unresolved", "bounded", "none", "bounded", "none", "bounded")
    approvals = ("not_required", "not_required", "review_required", "deferred", "approved", "approved", "approved", "approved", "review_required")
    rollbacks = ("not_applicable", "not_applicable", "available", "available", "verified", "available", "verified", "verified", "available")
    rows: list[dict[str, Any]] = []
    previous = ""
    for sequence, domain in enumerate(domains):
        row = create_evidence_record(
            evidence_id=f"v1192.9-evidence-{domain}",
            sequence=sequence,
            previous_evidence_digest=previous,
            snapshot_digest=snapshot_digest,
            context_digest=context_digest,
            artifact_digest=_digest({"artifact": domain, "sequence": sequence}),
            receipt_digest=_digest({"receipt": domain, "sequence": sequence}),
            domain=domain,
            evidence_kind=kinds[sequence],
            outcome=outcomes[sequence],
            uncertainty_code=uncertainties[sequence],
            approval_state=approvals[sequence],
            rollback_state=rollbacks[sequence],
        )
        rows.append(row)
        previous = row["evidence_digest"]
    return rows


def build_evidence_compaction_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    retained = (
        build_bounded_evidence_compaction_checkpoint(source_root=source),
        build_evidence_compaction_review_checkpoint(source_root=source),
        build_evidence_compaction_reliability_checkpoint(source_root=source),
    )
    retained_versions = ("v1192.2", "v1192.5", "v1192.8")
    for report, version in zip(retained, retained_versions):
        for key, expected in (
            ("ok", True), ("contract_version", version), ("read_only", True),
            ("post_available", False), ("content_free", True),
            ("execution_invoked", False), ("authority_granted", False),
        ):
            require(report.get(key) == expected)
        require(report.get("passed") == report.get("total"))
        require(report.get("source_unchanged") is True)

    snapshot_digest = _digest({"checkpoint": _CHECKPOINT_ID, "surface": "unified-experience"})
    context_digest = _digest({"checkpoint": _CHECKPOINT_ID, "context": "evidence-compaction"})
    records = _sample_records(snapshot_digest, context_digest)
    require(len(records) == 9)
    require(len({row["domain"] for row in records}) == 9)
    require([row["sequence"] for row in records] == list(range(9)))
    require(records[0]["previous_evidence_digest"] == "")
    for index, row in enumerate(records):
        require(row.get("snapshot_digest") == snapshot_digest)
        require(row.get("context_digest") == context_digest)
        require(row.get("authority_state") == "separate_not_granted")
        require(len(str(row.get("evidence_digest") or "")) == 64)
        if index:
            require(row.get("previous_evidence_digest") == records[index - 1].get("evidence_digest"))

    compacted = compact_evidence(records, snapshot_digest=snapshot_digest, context_digest=context_digest)
    expanded = expand_compaction(
        compacted,
        expected_snapshot_digest=snapshot_digest,
        expected_context_digest=context_digest,
    )
    equivalence = verify_compaction_equivalence(
        records,
        compacted,
        snapshot_digest=snapshot_digest,
        context_digest=context_digest,
    )
    compaction_summary = public_compaction_summary(compacted, equivalence)
    for value in (
        compacted.get("status") == "compacted",
        compacted.get("lossless_claim") is True,
        expanded.get("status") == "expanded",
        expanded.get("records") == records,
        equivalence.get("status") == "equivalent",
        equivalence.get("equivalent") is True,
        equivalence.get("historical_truth_preserved") is True,
        equivalence.get("approval_truth_preserved") is True,
        equivalence.get("rollback_truth_preserved") is True,
        equivalence.get("uncertainty_truth_preserved") is True,
        equivalence.get("authority_separation_preserved") is True,
        compaction_summary.get("content_free") is True,
        compaction_summary.get("record_count") == 9,
        compaction_summary.get("authority_granted") is False,
    ):
        require(value)

    equivalence_digest = _digest({
        "original_digest": equivalence.get("original_digest"),
        "expanded_digest": equivalence.get("expanded_digest"),
        "record_count": equivalence.get("record_count"),
    })
    request = create_compaction_review_request(
        request_id="v1192.9-compaction-review-request",
        compaction_digest=compacted["compaction_digest"],
        terminal_evidence_digest=records[-1]["evidence_digest"],
        snapshot_digest=snapshot_digest,
        context_digest=context_digest,
        record_count=len(records),
        equivalence_digest=equivalence_digest,
        purpose_code="operator_review",
    )
    review_results: dict[str, dict[str, Any]] = {}
    for decision in ("approve", "reject", "defer"):
        review = create_compaction_review(
            request_digest=request["request_digest"],
            decision=decision,
            review_id=f"v1192.9-compaction-review-{decision}",
            operator_review_digest=_digest({"decision": decision, "checkpoint": _CHECKPOINT_ID}),
        )
        result = review_compaction(
            request=request,
            review=review,
            current_snapshot_digest=snapshot_digest,
            current_context_digest=context_digest,
            current_compaction_digest=compacted["compaction_digest"],
            current_terminal_evidence_digest=records[-1]["evidence_digest"],
            equivalence_verified=True,
        )
        public = public_compaction_review_summary(result)
        review_results[decision] = result
        require(result.get("status") == f"review_{'approved' if decision == 'approve' else 'rejected' if decision == 'reject' else 'deferred'}")
        require(result.get("original_evidence_preserved") is True)
        require(result.get("replacement_performed") is False)
        require(result.get("deletion_performed") is False)
        require(result.get("execution_invoked") is False)
        require(result.get("approval_created") is False)
        require(result.get("approval_consumed") is False)
        require(result.get("authority_granted") is False)
        require(public.get("content_free") is True)
    require(review_results["approve"].get("compaction_retention_presented") is True)
    require(review_results["reject"].get("compaction_retention_presented") is False)
    require(review_results["defer"].get("compaction_retention_presented") is False)

    reliability_rows: list[dict[str, Any]] = []
    previous_reliability = ""
    event_actions = (
        ("interruption", "preserve"),
        ("restart", "review_required"),
        ("stale_compaction", "rebuild_required"),
        ("replay", "reject"),
        ("privacy", "reject"),
        ("tamper", "reject"),
        ("outage", "defer"),
        ("recovery_review", "review_required"),
    )
    for sequence, (event_type, action) in enumerate(event_actions):
        row = create_reliability_record(
            record_id=f"v1192.9-reliability-{event_type}",
            event_type=event_type,
            action=action,
            compaction_digest=compacted["compaction_digest"],
            terminal_evidence_digest=records[-1]["evidence_digest"],
            snapshot_digest=snapshot_digest,
            context_digest=context_digest,
            review_digest=_digest({"event": event_type, "sequence": sequence}),
            sequence=sequence,
            previous_record_digest=previous_reliability,
        )
        reliability_rows.append(row)
        previous_reliability = row["record_digest"]
    reliability = assess_compaction_reliability(
        records=reliability_rows,
        current_compaction_digest=compacted["compaction_digest"],
        current_terminal_evidence_digest=records[-1]["evidence_digest"],
        current_snapshot_digest=snapshot_digest,
        current_context_digest=context_digest,
    )
    reliability_summary = public_reliability_summary(reliability)
    for value in (
        reliability.get("ok") is True,
        reliability.get("status") == "reliability_verified",
        reliability.get("record_count") == 8,
        reliability.get("interruption_count") == 1,
        reliability.get("restart_count") == 1,
        reliability.get("replay_detected") is False,
        reliability.get("original_evidence_preserved") is True,
        reliability.get("automatic_recovery") is False,
        reliability.get("replacement_performed") is False,
        reliability.get("deletion_performed") is False,
        reliability.get("execution_invoked") is False,
        reliability.get("provider_contacted") is False,
        reliability.get("model_contacted") is False,
        reliability.get("thread_started") is False,
        reliability.get("process_started") is False,
        reliability.get("runtime_modified") is False,
        reliability.get("authority_granted") is False,
        reliability_summary.get("content_free") is True,
    ):
        require(value)

    blocked_cases: dict[str, list[str]] = {}

    stale = expand_compaction(
        compacted,
        expected_snapshot_digest=_digest("stale-snapshot"),
        expected_context_digest=context_digest,
    )
    blocked_cases["stale-compaction"] = list(stale.get("errors") or [])
    require(stale.get("status") == "blocked")
    require("stale_compaction_snapshot" in blocked_cases["stale-compaction"])

    tampered = dict(compacted)
    tampered["compaction_digest"] = "0" * 64
    tamper_result = expand_compaction(
        tampered,
        expected_snapshot_digest=snapshot_digest,
        expected_context_digest=context_digest,
    )
    blocked_cases["compaction-tamper"] = list(tamper_result.get("errors") or [])
    require(tamper_result.get("status") == "blocked")
    require("compaction_tamper" in blocked_cases["compaction-tamper"])

    private_request = dict(request)
    private_request["prompt"] = "private"
    private_review = create_compaction_review(
        request_digest=private_request["request_digest"],
        decision="approve",
        review_id="v1192.9-private-review",
        operator_review_digest=_digest("private-review"),
    )
    private_result = review_compaction(
        request=private_request,
        review=private_review,
        current_snapshot_digest=snapshot_digest,
        current_context_digest=context_digest,
        current_compaction_digest=compacted["compaction_digest"],
        current_terminal_evidence_digest=records[-1]["evidence_digest"],
        equivalence_verified=True,
    )
    blocked_cases["private-review"] = list(private_result.get("errors") or [])
    require(private_result.get("status") == "blocked")
    require("private_or_authority_content_present" in blocked_cases["private-review"])

    replay_rows = [dict(row) for row in reliability_rows]
    replay_rows[1]["review_digest"] = replay_rows[0]["review_digest"]
    replay_rows[1].pop("record_digest", None)
    from evidence_compaction_reliability import _digest as _reliability_digest
    replay_rows[1]["record_digest"] = _reliability_digest(replay_rows[1])
    replay_result = assess_compaction_reliability(
        records=replay_rows,
        current_compaction_digest=compacted["compaction_digest"],
        current_terminal_evidence_digest=records[-1]["evidence_digest"],
        current_snapshot_digest=snapshot_digest,
        current_context_digest=context_digest,
    )
    blocked_cases["replay"] = list(replay_result.get("errors") or [])
    require(replay_result.get("status") == "blocked")
    require(replay_result.get("replay_detected") is True)
    require("replay_detected" in blocked_cases["replay"])

    registry = inspect_checkpoint_registry(source_root=source)
    checkpoint_ids = {row.get("checkpoint_id") for row in registry.get("checkpoints", [])}
    for checkpoint_id in (
        "bounded-evidence-compaction-checkpoint",
        "evidence-compaction-review-checkpoint",
        "evidence-compaction-reliability-checkpoint",
        "evidence-compaction-checkpoint",
    ):
        require(checkpoint_id in checkpoint_ids)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))
    require(registry.get("read_only") is True)
    require(registry.get("content_free") is True)

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(privacy.get("forbidden_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)

    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    summary = {
        "retained_checkpoint_count": 3,
        "retained_check_total": sum(int(report.get("total", 0)) for report in retained),
        "unified_domain_count": len({row["domain"] for row in records}),
        "evidence_record_count": len(records),
        "compacted_record_count": compaction_summary.get("record_count", 0),
        "exact_expansion_verified": expanded.get("records") == records,
        "equivalence_verified": equivalence.get("equivalent") is True,
        "historical_truth_preserved": equivalence.get("historical_truth_preserved") is True,
        "uncertainty_truth_preserved": equivalence.get("uncertainty_truth_preserved") is True,
        "approval_truth_preserved": equivalence.get("approval_truth_preserved") is True,
        "rollback_truth_preserved": equivalence.get("rollback_truth_preserved") is True,
        "authority_separation_preserved": equivalence.get("authority_separation_preserved") is True,
        "review_decision_count": len(review_results),
        "approved_review_count": sum(result.get("status") == "review_approved" for result in review_results.values()),
        "rejected_review_count": sum(result.get("status") == "review_rejected" for result in review_results.values()),
        "deferred_review_count": sum(result.get("status") == "review_deferred" for result in review_results.values()),
        "reliability_event_count": len(reliability_rows),
        "blocked_case_count": len(blocked_cases),
        "original_evidence_preserved": True,
        "content_free": True,
    }
    structural = {
        "checkpoint_id": _CHECKPOINT_ID,
        "retained_versions": retained_versions,
        "compaction_digest": compacted.get("compaction_digest"),
        "terminal_evidence_digest": records[-1].get("evidence_digest"),
        "review_result_digests": {key: value.get("review_result_digest") for key, value in sorted(review_results.items())},
        "reliability_result_digest": reliability.get("result_digest"),
        "blocked_cases": blocked_cases,
        "summary": summary,
    }
    return {
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "summary": summary,
        "blocked_cases": blocked_cases,
        "limitations": list(_LIMITATIONS),
        "structural_digest": _digest(structural),
        "source_unchanged": before_digest == after_digest,
        "source_file_count": before_count,
        "runtime_mutated": False,
        "production_source_modified": False,
        "original_evidence_preserved": True,
        "replacement_performed": False,
        "deletion_performed": False,
        "automatic_recovery": False,
        "rollback_invoked": False,
        "execution_invoked": False,
        "approval_created": False,
        "approval_consumed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "installation_invoked": False,
        "promotion_invoked": False,
        "publication_invoked": False,
        "release_invoked": False,
        "authority_granted": False,
        "authority_preserved": True,
        "global_profile_pass_claimed": False,
        "desktop_verification_deferred_until_v1200": True,
    }
