from __future__ import annotations

"""Read-only v1191.9 Responsiveness and Background Work checkpoint.

Consolidates the v1191 queue foundations, reviewed presentation transitions,
and reliability hardening. It also verifies bounded repairs for ordinary-chat
software-development routing, campaign visibility, Windows newline-safe sandbox
repair materialization, and explicit UTF-8 reads in the current v1190 suites.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from action_proposal_handoff import build_action_proposal_handoff
from checkpoint_registry import inspect_checkpoint_registry
from developer_campaign_conversation_projection import build_developer_campaign_conversation_projection
from natural_language_action_routing import build_natural_language_action_projection
from package_integrity import package_privacy_summary_for_root
from responsive_work_queue_checkpoint import build_responsive_work_queue_checkpoint
from responsive_work_queue_reliability_checkpoint import build_responsive_work_queue_reliability_checkpoint
from responsive_work_queue_review_checkpoint import build_responsive_work_queue_review_checkpoint
from supervised_sandbox_repair_draft_checkpoint import _lineage
from supervised_sandbox_repair_draft_foundations import draft_supervised_sandbox_repair
from supervised_sandbox_repair_review_materialization import materialize_reviewed_sandbox_repair, review_repair_draft, sandbox_repair_materialization_public_summary

CONTRACT_VERSION = "v1191.9"
_CHECKPOINT_ID = "responsiveness-background-work:v1191.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_LIMITATIONS = (
    "Queue transitions and reliability outcomes remain content-free evidence and do not control real work.",
    "Ordinary chat exposes a proposal-only software-development campaign surface but does not persist a proposal or create approval.",
    "Windows newline repair preserves raw rollback bytes but still requires exact reviewed UTF-8 text content.",
    "No provider, model, thread, process, shell command, queued work, cancellation, recovery, or source mutation is invoked.",
    "Desktop Codex and native-provider review remain deferred until the v1200 decision gate.",
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


def build_responsiveness_background_work_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    del runtime_root
    before_digest, before_count = _tree_signature(source)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    retained = (
        build_responsive_work_queue_checkpoint(source_root=source),
        build_responsive_work_queue_review_checkpoint(source_root=source),
        build_responsive_work_queue_reliability_checkpoint(source_root=source),
    )
    for report, version in zip(retained, ("v1191.2", "v1191.5", "v1191.8")):
        for key, value in (
            ("ok", True), ("contract_version", version), ("read_only", True),
            ("post_available", False), ("content_free", True),
            ("provider_contacted", False), ("model_contacted", False),
            ("thread_started", False), ("process_started", False),
            ("execution_invoked", False), ("authority_granted", False),
        ):
            require(report.get(key) == value)
        require(report.get("passed") == report.get("total"))

    routing_results: dict[str, dict[str, Any]] = {}
    campaign_results: dict[str, dict[str, Any]] = {}
    for label, text in (
        ("make_web_page", "Make me a web page for my dog."),
        ("build_web_page", "Build me a web page for my dog."),
        ("build_application", "Build a small application for this project."),
    ):
        projection = build_natural_language_action_projection(text)
        handoff = build_action_proposal_handoff(projection, operation_id=f"v1191.9-{label}")
        campaign = build_developer_campaign_conversation_projection(
            projection, handoff, project_state={"active": True},
        )
        routing_results[label] = {
            "category": projection.get("intent", {}).get("category"),
            "grounding_status": projection.get("grounding", {}).get("grounding_status"),
            "capability_id": projection.get("grounding", {}).get("capability_id"),
            "proposal_state": handoff.get("proposal", {}).get("proposal_state"),
        }
        campaign_results[label] = campaign
        require(projection.get("intent", {}).get("category") == "action_request")
        require(projection.get("grounding", {}).get("grounding_status") == "matched")
        require(projection.get("grounding", {}).get("capability_id") == "software_development")
        require(projection.get("grounding", {}).get("capability_registered") is True)
        require(handoff.get("proposal", {}).get("proposal_state") == "ready_for_operator_review")
        require(handoff.get("proposal", {}).get("persisted") is False)
        require(handoff.get("approval_handoff", {}).get("approval_created") is False)
        require(handoff.get("execution_admission", {}).get("admitted") is False)
        require(campaign.get("status") == "supervised_campaign_proposal_visible")
        require(campaign.get("campaign_connected_to_conversation") is True)
        require(campaign.get("stage_count") == 9)
        require(campaign.get("lineage_surface_count") == 8)
        require(campaign.get("foreground_conversation_preserved") is True)
        require(campaign.get("proposal_persisted") is False)
        require(campaign.get("execution_invoked") is False)
        require(campaign.get("content_free") is True)
        require(campaign.get("authority_granted") is False)

    ordinary = build_natural_language_action_projection("Tell me about web design principles.")
    ordinary_handoff = build_action_proposal_handoff(ordinary, operation_id="v1191.9-ordinary")
    ordinary_campaign = build_developer_campaign_conversation_projection(ordinary, ordinary_handoff)
    require(ordinary.get("intent", {}).get("category") in {"conversation", "question"})
    require(ordinary_campaign.get("status") == "inactive")
    require(ordinary_campaign.get("campaign_connected_to_conversation") is False)

    newline_result: dict[str, Any]
    before_lf = "def broken():\n    return False\n"
    before_crlf = before_lf.replace("\n", "\r\n").encode("utf-8")
    after_lf = "def repaired():\n    return True\n"
    lineage = _lineage("pkg/windows_case.py", before_lf, status="failed", error_class="python_compile_failed")
    draft = draft_supervised_sandbox_repair(*lineage, before_lf, after_lf)
    review = review_repair_draft(draft, decision="approve", operator_actor="v1191.9-checkpoint")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1191-9-newline-") as temp:
        root = Path(temp)
        sandbox = root / "sandbox"
        fake_source = root / "source"
        fake_source.mkdir()
        destination = sandbox / "pkg" / "windows_case.py"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(before_crlf)
        newline_result = materialize_reviewed_sandbox_repair(
            draft, review, sandbox_root=sandbox, source_root=fake_source,
            current_target_text=before_lf, replacement_text=after_lf,
        )
        require(newline_result.get("materialization_status") == "materialized")
        require(newline_result.get("newline_normalization_applied") is True)
        require(destination.read_bytes() == after_lf.encode("utf-8"))
        require(newline_result.get("rollback_artifact_present") is True)
        require(newline_result.get("rollback_artifact_digest_verified") is True)
        rollback_path = sandbox / ".eidolon_repair_rollback" / f"{draft['draft_digest']}.rollback"
        require(rollback_path.exists())
        require(rollback_path.read_bytes() == before_crlf)
        require(newline_result.get("physical_baseline_target_digest") == hashlib.sha256(before_crlf).hexdigest())
        require(newline_result.get("baseline_target_digest") == hashlib.sha256(before_lf.encode("utf-8")).hexdigest())
        public = sandbox_repair_materialization_public_summary(newline_result)
        require(public.get("content_free") is True)
        require("replacement_text" not in public and "rollback_text" not in public)
        replay = materialize_reviewed_sandbox_repair(
            draft, review, sandbox_root=sandbox, source_root=fake_source,
            current_target_text=before_lf, replacement_text=after_lf,
        )
        require(replay.get("materialization_status") == "already_materialized")
        require(replay.get("sandbox_file_written") is False)
        require(not any(fake_source.rglob("*")))

    navigation_test = (source / "tools" / "v1190_3_5_unified_experience_navigation_tests.py").read_text(encoding="utf-8")
    reliability_test = (source / "tools" / "v1190_6_8_unified_experience_reliability_tests.py").read_text(encoding="utf-8")
    require(navigation_test.count('.read_text(encoding="utf-8")') >= 3)
    require(reliability_test.count('.read_text(encoding="utf-8")') >= 3)

    runtime_source = (source / "conscious_agent" / "conversation_runtime.py").read_text(encoding="utf-8")
    require(runtime_source.count("build_developer_campaign_conversation_projection(") == 2)
    require(runtime_source.count("developer_campaign_conversation_prompt(developer_campaign_projection)") == 2)
    require(runtime_source.count('result.cognitive_context["developer_campaign_conversation"]') == 2)

    registry = inspect_checkpoint_registry(source_root=source)
    row = next(
        (item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "responsiveness-background-work-checkpoint"),
        None,
    )
    require(row is not None)
    require((row or {}).get("contract_version") == CONTRACT_VERSION)
    require((row or {}).get("builder") == "build_responsiveness_background_work_checkpoint")
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    after_digest, after_count = _tree_signature(source)
    require(before_digest == after_digest)
    require(before_count == after_count)

    summary = {
        "retained_checkpoint_count": len(retained),
        "software_development_routing_case_count": len(routing_results),
        "campaign_conversation_case_count": len(campaign_results),
        "campaign_stage_count": 9,
        "campaign_lineage_surface_count": 8,
        "windows_newline_materialization_ready": newline_result.get("materialization_status") == "materialized",
        "raw_crlf_rollback_preserved": newline_result.get("rollback_artifact_digest_verified") is True,
        "utf8_windows_suite_fix_count": 2,
        "foreground_conversation_preserved": all(
            row.get("foreground_conversation_preserved") is True for row in campaign_results.values()
        ),
    }
    report = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "status": "ready" if all(checks) else "review_required",
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "summary": summary,
        "routing_results": routing_results,
        "limitations": list(_LIMITATIONS),
        "source_unchanged": before_digest == after_digest,
        "source_file_count": before_count,
        "runtime_mutated": False,
        "production_source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "execution_invoked": False,
        "queued_work_executed": False,
        "real_work_cancelled": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "authority_granted": False,
        "authority_preserved": True,
        "desktop_verification_deferred_until_v1200": True,
    }
    report["structural_digest"] = _digest(report)
    return report
