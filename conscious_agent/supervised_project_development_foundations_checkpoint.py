from __future__ import annotations

"""Read-only v1184.2 complete supervised project-development loop foundations checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from supervised_project_development_lineage import STAGES, create_project_stage_receipt, integrate_supervised_project_development, supervised_project_development_public_summary

CONTRACT_VERSION = "v1184.2"


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def build_supervised_project_development_foundations_checkpoint(*, source_root: str | Path | None = None, runtime_root: str | Path | None = None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    checks: list[bool] = []
    def require(value: object) -> None: checks.append(bool(value))
    rows = []
    previous = ""
    for stage in STAGES:
        row = create_project_stage_receipt(stage=stage, status="completed", artifact_digest=_h(stage), previous_receipt_digest=previous, operator_review_digest=_h(stage+":review"))
        rows.append(row); previous = row["receipt_digest"]
    complete = integrate_supervised_project_development(rows)
    summary = supervised_project_development_public_summary(complete)
    require(complete["complete_lineage"] is True)
    require(complete["status"] == "complete_review_required")
    require(complete["stage_count"] == 9)
    require(complete["production_source_modified"] is False)
    require(complete["sandbox_modified"] is False)
    require(complete["execution_invoked"] is False)
    require(complete["authority_granted"] is False)
    require(summary["content_free"] is True)
    for count in range(1, 9):
        partial = integrate_supervised_project_development(rows[:count])
        require(partial["status"] == "in_progress_review_required")
        require(partial["next_stage"] == STAGES[count])
    bad = dict(rows[3]); bad["artifact_digest"] = "0" * 64
    require(integrate_supervised_project_development([*rows[:3], bad])["status"] == "blocked")
    wrong = [dict(item) for item in rows[:3]]; wrong[2]["previous_receipt_digest"] = "f" * 64
    require("lineage_link_mismatch" in integrate_supervised_project_development(wrong)["errors"])
    terminal = [dict(item) for item in rows[:3]]; terminal[1] = create_project_stage_receipt(stage="deficiency_review", status="rejected", artifact_digest=_h("reject"), previous_receipt_digest=terminal[0]["receipt_digest"]); terminal[2] = create_project_stage_receipt(stage="specification", status="completed", artifact_digest=_h("later"), previous_receipt_digest=terminal[1]["receipt_digest"])
    require("continued_after_terminal_stage" in integrate_supervised_project_development(terminal)["errors"])
    registry = inspect_checkpoint_registry(source_root=source)
    row = next((item for item in registry["checkpoints"] if item["checkpoint_id"] == "supervised-project-development-foundations-checkpoint"), {})
    require(row.get("builder") == "build_supervised_project_development_foundations_checkpoint")
    require(registry["duplicate_checkpoint_ids"] == [])
    return {
        "ok": all(checks), "contract_version": CONTRACT_VERSION,
        "checkpoint_id": "supervised-project-development-foundations:v1184.2",
        "passed": sum(checks), "total": len(checks), "read_only": True,
        "content_free": True, "summary": summary,
        "production_source_modified": False, "sandbox_modified": False,
        "execution_invoked": False, "provider_contacted": False, "model_contacted": False,
        "approval_created": False, "authority_granted": False,
        "source_application_authorized": False, "release_authorized": False,
        "desktop_verification_deferred_until_v1200": True,
    }
