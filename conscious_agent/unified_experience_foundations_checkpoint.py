from __future__ import annotations

"""Read-only v1190.2 Unified Experience Foundations checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from unified_experience_foundations import DOMAINS, build_unified_experience_snapshot, create_experience_surface, unified_experience_public_summary

CONTRACT_VERSION = "v1190.2"
_CHECKPOINT_ID = "unified-experience-foundations:v1190.2"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_LIMITATIONS = (
    "The unified experience consumes caller-supplied content-free digests and does not fetch private subsystem records.",
    "One current surface per domain is projected; historical navigation and coordinated transitions are deferred to v1190.3-v1190.5.",
    "The projection creates, consumes, or infers no approval, execution, installation, promotion, certification, publication, or release authority.",
    "No provider/model contact, source mutation, runtime mutation, automatic continuation, or policy application occurs.",
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


def _surface_rows(*, context_digest: str, focus_domain: str = "campaign") -> list[dict[str, Any]]:
    states = {
        "conversation": "active",
        "cognition": "reflecting",
        "reasoning": "concluded",
        "planning": "approved",
        "campaign": "active",
        "approval": "approved_not_executed",
        "action": "eligible_not_executing",
        "result": "pending",
        "learning": "pending",
    }
    authorities = {
        "conversation": "none",
        "cognition": "none",
        "reasoning": "recorded_no_authority",
        "planning": "recorded_no_authority",
        "campaign": "recorded_no_authority",
        "approval": "approved_not_executed",
        "action": "review_required",
        "result": "none",
        "learning": "none",
    }
    rows: list[dict[str, Any]] = []
    previous = ""
    for index, domain in enumerate(DOMAINS):
        row = create_experience_surface(
            surface_id=f"experience-surface-{domain}",
            domain=domain,
            state=states[domain],
            sequence=index,
            context_digest=context_digest,
            artifact_digest=_h(f"v1190.2:{domain}:artifact"),
            receipt_digest=_h(f"v1190.2:{domain}:receipt"),
            previous_surface_digest=previous,
            operator_review_digest=(
                _h(f"v1190.2:{domain}:operator-review")
                if authorities[domain] in {"review_required", "approved_not_executed", "consumed_no_reuse"}
                else ""
            ),
            authority_state=authorities[domain],
            is_focus=domain == focus_domain,
        )
        rows.append(row)
        previous = row["surface_digest"]
    return rows


def _resign(row: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(row)
    updated.pop("surface_digest", None)
    updated["surface_digest"] = _digest(updated)
    return updated


def build_unified_experience_foundations_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root  # Read-only foundation; runtime data is neither read nor written.
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []
    require = lambda value: checks.append(bool(value))

    context = _h("v1190.2:unified-experience-context")
    rows = _surface_rows(context_digest=context)
    good = build_unified_experience_snapshot(
        experience_id="unified-experience-0001",
        context_digest=context,
        surfaces=rows,
        selected_surface_id="experience-surface-campaign",
        operator_view_digest=_h("v1190.2:operator-view"),
    )
    require(good.get("status") == "ready_for_operator_view")
    require(good.get("error_count") == 0)
    require(good.get("surface_count") == len(DOMAINS))
    require(good.get("domain_count") == len(DOMAINS))
    require(good.get("domains") == list(DOMAINS))
    require(good.get("selected_domain") == "campaign")
    require(good.get("selected_state") == "active")
    require(good.get("records_duplicated") is False)
    require(good.get("review_required_count") == 1)
    require(good.get("approved_not_executed_count") == 1)
    require(len(str(good.get("unified_experience_digest", ""))) == 64)

    summary = unified_experience_public_summary(good)
    require(summary.get("status") == "ready_for_operator_view")
    require(summary.get("surface_count") == len(DOMAINS))
    require(summary.get("selected_domain") == "campaign")
    require(summary.get("content_free") is True)
    require(summary.get("authority_granted") is False)
    require(summary.get("execution_invoked") is False)

    blocked_cases: dict[str, dict[str, Any]] = {}

    duplicate = list(rows)
    duplicate[-1] = _resign({**duplicate[-1], "domain": "result"})
    blocked_cases["duplicate_domain"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0002", context_digest=context, surfaces=duplicate,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:duplicate"),
    )

    tampered = [dict(row) for row in rows]
    tampered[2]["state"] = "blocked"
    blocked_cases["tampered_surface"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0003", context_digest=context, surfaces=tampered,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:tamper"),
    )

    mismatched_context = [dict(row) for row in rows]
    mismatched_context[1] = _resign({**mismatched_context[1], "context_digest": _h("wrong-context")})
    blocked_cases["context_mismatch"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0004", context_digest=context, surfaces=mismatched_context,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:context"),
    )

    bad_focus = [dict(row) for row in rows]
    bad_focus[0] = _resign({**bad_focus[0], "is_focus": True})
    blocked_cases["multiple_focus"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0005", context_digest=context, surfaces=bad_focus,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:focus"),
    )

    bad_authority = [dict(row) for row in rows]
    bad_authority[5] = _resign({**bad_authority[5], "authority_granted": True})
    blocked_cases["authority_expansion"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0006", context_digest=context, surfaces=bad_authority,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:authority"),
    )

    private = [dict(row) for row in rows]
    private[0] = _resign({**private[0], "conversation_text": "not allowed"})
    blocked_cases["private_content"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0007", context_digest=context, surfaces=private,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:private"),
    )

    inconsistent = [dict(row) for row in rows]
    inconsistent[6] = _resign({**inconsistent[6], "state": "completed"})
    blocked_cases["terminal_without_result"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0008", context_digest=context, surfaces=inconsistent,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:terminal"),
    )

    missing = rows[:-1]
    blocked_cases["incomplete_domains"] = build_unified_experience_snapshot(
        experience_id="unified-experience-0009", context_digest=context, surfaces=missing,
        selected_surface_id="experience-surface-campaign", operator_view_digest=_h("view:missing"),
    )

    for name, row in blocked_cases.items():
        require(row.get("status") == "blocked")
        require(row.get("error_count", 0) > 0)
        require(row.get("authority_granted") is False)
        require(row.get("execution_invoked") is False)
        require(row.get("content_free") is True)
        if name == "duplicate_domain":
            require("duplicate_domain" in row.get("errors", []) or "domain_set_mismatch" in row.get("errors", []))
        if name == "tampered_surface":
            require("tampered_surface" in row.get("errors", []))
        if name == "context_mismatch":
            require("context_lineage_mismatch" in row.get("errors", []))
        if name == "multiple_focus":
            require("exactly_one_focus_required" in row.get("errors", []))
        if name == "authority_expansion":
            require("authority_or_execution_expansion" in row.get("errors", []))
        if name == "private_content":
            require("private_or_authority_content_present" in row.get("errors", []))
        if name == "terminal_without_result":
            require("terminal_action_missing_result" in row.get("errors", []))
        if name == "incomplete_domains":
            require("incomplete_domain_set" in row.get("errors", []))

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "unified-experience-foundations-checkpoint"),
        None,
    )
    require(descriptor is not None)
    require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
    require((descriptor or {}).get("builder") == "build_unified_experience_foundations_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("forbidden_entry_count", 0) == 0)
    require(privacy.get("private_content_finding_count", 0) == 0)

    for field in (
        "execution_invoked", "automatic_continuation", "source_modified", "runtime_modified",
        "provider_contacted", "model_contacted", "approval_created", "approval_consumed", "authority_granted",
    ):
        require(good.get(field) is False)

    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    return {
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
        "automatic_continuation": False,
        "approval_created": False,
        "approval_consumed": False,
        "execution_invoked": False,
        "authority_granted": False,
        "authority_preserved": True,
        "desktop_verification_deferred_until_v1200": True,
        "source_signature_before": before_digest,
        "source_signature_after": after_digest,
        "source_file_count": before_count,
        "summary": {
            "domain_count": len(DOMAINS),
            "valid_snapshot_count": 1,
            "blocked_boundary_case_count": len(blocked_cases),
            "review_required_surface_count": good.get("review_required_count", 0),
            "approved_not_executed_surface_count": good.get("approved_not_executed_count", 0),
            "selected_domain": good.get("selected_domain", ""),
        },
        "limitations": list(_LIMITATIONS),
        "structural_digest": _digest({
            "checkpoint_id": _CHECKPOINT_ID,
            "valid": good.get("unified_experience_digest", ""),
            "blocked": {name: row.get("unified_experience_digest", "") for name, row in sorted(blocked_cases.items())},
        }),
    }
