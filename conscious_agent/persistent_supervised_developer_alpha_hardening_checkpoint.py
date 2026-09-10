from __future__ import annotations

"""Read-only v1189.9 Persistent Supervised Developer Alpha hardening checkpoint.

Consolidates the v1189 adversarial hardening, durable replay defense,
long-session evidence, stale-state, privacy, authority, and recovery-review
contracts. All cases are synthetic and content-free. Durable nonce writes are
restricted to isolated temporary runtime roots and are removed before return.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from adversarial_campaign_hardening_long_session import create_long_session_evidence, register_review_nonce
from adversarial_campaign_hardening_long_session_checkpoint import build_adversarial_campaign_hardening_long_session_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from persistent_developer_adversarial_reliability import ALLOWED_ACTIONS, ALLOWED_STATES, assess_persistent_developer_reliability, create_reliability_review, public_summary
from persistent_developer_adversarial_reliability_checkpoint import _case, build_persistent_developer_adversarial_reliability_checkpoint
from persistent_supervised_developer_hardening_checkpoint import build_persistent_supervised_developer_hardening_checkpoint

CONTRACT_VERSION = "v1189.9"
_CHECKPOINT_ID = "persistent-supervised-developer-alpha-hardening:v1189.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_LIMITATIONS = (
    "Source, privacy, authority, and long-session observations remain caller-supplied content-free evidence.",
    "Nonce durability and writer exclusion remain local single-host filesystem foundations.",
    "Recovery review records intent only and does not resume, restart, retry, repair, or execute campaign work.",
    "No policy, future work selection, installation, promotion, certification, publication, or release authority is created.",
    "Desktop Codex and native-provider review remain deferred until the v1200 decision gate.",
)


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    if not root.exists():
        return digest.hexdigest(), count
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


def _signed(row: Mapping[str, Any], field: str, **changes: object) -> dict[str, Any]:
    result = dict(row)
    result.update(changes)
    result.pop(field, None)
    result[field] = _digest(result)
    return result


def build_persistent_supervised_developer_alpha_hardening_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []
    require = lambda value: checks.append(bool(value))

    with tempfile.TemporaryDirectory(prefix="eidolon-v1189-9-") as isolated:
        runtime = Path(isolated) / "runtime"
        retained = (
            build_persistent_supervised_developer_hardening_checkpoint(source_root=source, runtime_root=runtime),
            build_adversarial_campaign_hardening_long_session_checkpoint(source_root=source, runtime_root=runtime),
            build_persistent_developer_adversarial_reliability_checkpoint(source_root=source, runtime_root=runtime),
        )
        for report, version in zip(retained, ("v1189.2", "v1189.5", "v1189.8")):
            require(report.get("ok") is True)
            require(report.get("passed") == report.get("total"))
            require(report.get("contract_version") == version)
            require(report.get("read_only") is True)
            require(report.get("post_available") is False)
            require(report.get("content_free") is True)
            require(report.get("source_modified") is False)
            require(report.get("authority_preserved") is True)
            require(report.get("desktop_verification_deferred_until_v1200") is True)

        hardening, long_session, source_digest = _case()
        registration = register_review_nonce(
            runtime_root=runtime,
            campaign_id="campaign-alpha-hardening-0001",
            review_nonce=hardening["review_nonce"],
            operator_review_digest=_h("v1189.9:nonce"),
            expected_generation=0,
        )
        require(registration.get("status") == "registered")
        require(registration.get("generation") == 1)
        require(registration.get("review_nonce") == hardening.get("review_nonce"))
        require(len(str(registration.get("nonce_ledger_digest", ""))) == 64)
        require(registration.get("authority_granted") is False)
        require(registration.get("automatic_resume") is False)
        require(registration.get("execution_invoked") is False)

        assessments: list[dict[str, Any]] = []
        for index, state in enumerate(sorted(ALLOWED_STATES)):
            interruptions = index if state not in {"active", "completed"} else 0
            row = assess_persistent_developer_reliability(
                hardening_receipt=hardening,
                long_session_evidence=long_session,
                nonce_registration=registration,
                current_source_digest=source_digest,
                expected_source_digest=source_digest,
                current_nonce_generation=1,
                expected_nonce_generation=1,
                session_state=state,
                interruption_count=interruptions,
            )
            assessments.append(row)
            require(row.get("status") == "operator_review_required")
            require(row.get("session_state") == state)
            require(row.get("source_stale") is False)
            require(row.get("error_count") == 0)
            require(row.get("content_free") is True)
            require(row.get("automatic_resume") is False)
            require(row.get("automatic_retry") is False)
            require(row.get("execution_invoked") is False)
            require(row.get("provider_contacted") is False)
            require(row.get("model_contacted") is False)
            require(row.get("policy_modified") is False)
            require(row.get("future_work_selection_modified") is False)
            require(row.get("authority_granted") is False)
            summary = public_summary(row)
            require(summary.get("content_free") is True)
            require(summary.get("authority_granted") is False)
            require(summary.get("status") == "operator_review_required")

        review_count = 0
        for decision, expected_status in (("approve", "approved_not_executed"), ("reject", "recorded"), ("defer", "recorded")):
            for action in sorted(ALLOWED_ACTIONS):
                chosen = action if decision == "approve" else "hold"
                row = create_reliability_review(
                    assessment=assessments[0],
                    decision=decision,
                    action=chosen,
                    operator_review_digest=_h(f"review:{decision}:{action}"),
                )
                review_count += 1
                require(row.get("status") == expected_status)
                require(row.get("decision") == decision)
                require(row.get("action") == chosen)
                require(row.get("content_free") is True)
                require(row.get("recovery_executed") is False)
                require(row.get("automatic_resume") is False)
                require(row.get("execution_invoked") is False)
                require(row.get("authority_granted") is False)

        stale_source = assess_persistent_developer_reliability(
            hardening_receipt=hardening,
            long_session_evidence=long_session,
            nonce_registration=registration,
            current_source_digest=_h("v1189.9:changed-source"),
            expected_source_digest=source_digest,
            current_nonce_generation=1,
            expected_nonce_generation=1,
            session_state="restart_pending",
            interruption_count=3,
        )
        require(stale_source.get("status") == "operator_review_required")
        require(stale_source.get("source_stale") is True)
        require(stale_source.get("error_count") == 0)

        negative_rows: list[Mapping[str, Any]] = []
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening, long_session_evidence=long_session, nonce_registration=registration,
            current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=2, expected_nonce_generation=1, session_state="active", interruption_count=0,
        ))
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening, long_session_evidence=long_session, nonce_registration=registration,
            current_source_digest="bad", expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="active", interruption_count=0,
        ))
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening, long_session_evidence=long_session, nonce_registration=registration,
            current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="unknown", interruption_count=0,
        ))
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening, long_session_evidence=long_session, nonce_registration=registration,
            current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="paused", interruption_count=-1,
        ))
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening, long_session_evidence=long_session, nonce_registration=registration,
            current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="paused", interruption_count=1,
            privacy_findings=("bounded-finding",),
        ))
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening, long_session_evidence=long_session, nonce_registration=registration,
            current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="paused", interruption_count=1,
            authority_claims=("release",),
        ))
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=_signed(hardening, "hardening_receipt_digest", campaign_id="tampered"),
            long_session_evidence=long_session, nonce_registration=registration,
            current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="active", interruption_count=0,
        ))
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening,
            long_session_evidence={**long_session, "session_index": 999},
            nonce_registration=registration, current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="active", interruption_count=0,
        ))
        bad_nonce = dict(registration); bad_nonce["review_nonce"] = "other-review-nonce"
        negative_rows.append(assess_persistent_developer_reliability(
            hardening_receipt=hardening, long_session_evidence=long_session, nonce_registration=bad_nonce,
            current_source_digest=source_digest, expected_source_digest=source_digest,
            current_nonce_generation=1, expected_nonce_generation=1, session_state="active", interruption_count=0,
        ))
        for row in negative_rows:
            require(row.get("status") == "blocked")
            require(int(row.get("error_count", 0)) >= 1)
            require(row.get("content_free") is True)
            require(row.get("execution_invoked") is False)
            require(row.get("authority_granted") is False)

        replay = register_review_nonce(
            runtime_root=runtime,
            campaign_id="campaign-alpha-hardening-0001",
            review_nonce=hardening["review_nonce"],
            operator_review_digest=_h("v1189.9:nonce"),
            expected_generation=1,
        )
        stale_generation = register_review_nonce(
            runtime_root=runtime,
            campaign_id="campaign-alpha-hardening-0001",
            review_nonce="alpha-hardening-review-0002",
            operator_review_digest=_h("v1189.9:nonce:2"),
            expected_generation=0,
        )
        require(replay.get("status") == "blocked")
        require("replayed_review_nonce" in replay.get("errors", []))
        require(stale_generation.get("status") == "blocked")
        require("stale_nonce_generation" in stale_generation.get("errors", []))

        session_negative = (
            create_long_session_evidence(hardening_receipt=hardening, session_id="bad", session_index=1,
                started_at_ms=0, observed_at_ms=1, checkpoint_count=1, interruption_count=0, source_digest=source_digest),
            create_long_session_evidence(hardening_receipt=hardening, session_id="campaign-session-negative-1", session_index=0,
                started_at_ms=0, observed_at_ms=1, checkpoint_count=1, interruption_count=0, source_digest=source_digest),
            create_long_session_evidence(hardening_receipt=hardening, session_id="campaign-session-negative-2", session_index=1,
                started_at_ms=10, observed_at_ms=1, checkpoint_count=1, interruption_count=0, source_digest=source_digest),
            create_long_session_evidence(hardening_receipt=hardening, session_id="campaign-session-negative-3", session_index=1,
                started_at_ms=0, observed_at_ms=1, checkpoint_count=-1, interruption_count=0, source_digest=source_digest),
        )
        for row in session_negative:
            require(row.get("status") == "blocked")
            require(int(row.get("error_count", 0)) >= 1)
            require(row.get("automatic_resume") is False)
            require(row.get("execution_invoked") is False)
            require(row.get("authority_granted") is False)

        registry = inspect_checkpoint_registry(source_root=source)
        descriptor = next((row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "persistent-supervised-developer-alpha-hardening-checkpoint"), None)
        require(descriptor is not None)
        require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
        require((descriptor or {}).get("builder") == "build_persistent_supervised_developer_alpha_hardening_checkpoint")
        require(not registry.get("duplicate_checkpoint_ids"))
        require(not registry.get("duplicate_builder_targets"))
        require(registry.get("provider_contacted") is False)
        require(registry.get("runtime_data_read") is False)
        require(registry.get("source_modified") is False)

        privacy = package_privacy_summary_for_root(source)
        require(privacy.get("ok") is True)
        require(privacy.get("source_only") is True)
        require(privacy.get("forbidden_count") == 0)
        require(privacy.get("private_content_finding_count") == 0)

    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    summary = {
        "retained_bundle_count": 3,
        "session_state_case_count": len(ALLOWED_STATES),
        "reliability_review_case_count": review_count,
        "blocked_boundary_case_count": len(negative_rows) + 2 + len(session_negative),
        "durable_nonce_case_count": 3,
        "long_session_case_count": 1 + len(session_negative),
        "source_file_count": after_count,
    }
    report = {
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "source_modified": False,
        "runtime_mutated": False,
        "production_source_modified": False,
        "sandbox_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "automatic_retry": False,
        "automatic_resume": False,
        "automatic_continuation": False,
        "recovery_executed": False,
        "policy_modified": False,
        "future_work_selection_modified": False,
        "authority_granted": False,
        "authority_preserved": True,
        "desktop_verification_deferred_until_v1200": True,
        "summary": summary,
        "limitations": list(_LIMITATIONS),
        "source_signature_before": before_digest,
        "source_signature_after": after_digest,
    }
    report["structural_digest"] = _digest(report)
    return report
