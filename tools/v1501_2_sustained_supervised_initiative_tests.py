from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from dashboard_chat_console import _propose_explicit_chat_action
from supervised_development_continuation import is_supervised_development_continuation
from supervised_initiative_queue import (
    build_supervised_initiative_shortlist,
    inspect_supervised_initiative_queue,
    queue_supervised_initiative,
    reconcile_supervised_initiative_queue,
)
from v1489_product_capability_integration import integrate_v1489_product_capabilities


CHECKS: list[str] = []


def require(condition: object, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    rows = [(path.name, hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted((ROOT / "conscious_agent").glob("*.py"))]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


candidate = {
    "candidate_id": "discovery-1234567890abcdef1234",
    "evidence_digest": "e" * 64,
    "eligibility_digest": "f" * 64,
    "source_module": "conscious_agent/example.py",
    "proposed_destination_module": "conscious_agent/example_helpers.py",
    "source_symbols": ["first_helper", "second_helper"],
    "estimated_dependency_count": 1,
    "test_reference_file_count": 5,
    "confidence": 1.0,
}
hardening = {"eligible_candidates": [candidate], "eligible_count": 1}
comparison = {
    "ordered_comparison": [{"candidate_id": candidate["candidate_id"], "quality_score": .91}],
    "comparison_digest": "c" * 64,
    "candidate_count": 1,
}
shortlist = build_supervised_initiative_shortlist(hardening, comparison)

require(is_supervised_development_continuation("Continue your supervised development."), "exact_continue_command_recognized")
require(is_supervised_development_continuation("Resume the supervised self-development cycle"), "resume_alias_recognized")
require(not is_supervised_development_continuation("It would be nice if you continued developing someday."), "wish_does_not_authorize_cycle")
require(not is_supervised_development_continuation("Continue your supervised development and install it."), "compound_install_request_not_accepted")
require(_propose_explicit_chat_action("Continue your supervised development.", "") is None, "dashboard_defers_continue_command_to_receipt_bound_runtime")

before = source_signature()
old_runtime = os.environ.get("EIDOLON_DATA_DIR")
temporary = Path(tempfile.mkdtemp(prefix="eidolon-v1501-2-"))
try:
    runtime = temporary / "runtime"
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    proposal_id = "improvement-abcdef1234567890abcd"
    proposal_digest = "d" * 64
    authorization_texts: list[str] = []

    def created(_control, _root, *, operator_authorization_text=""):
        authorization_texts.append(operator_authorization_text)
        proposal = {
            "proposal_id": proposal_id,
            "proposal_digest": proposal_digest,
            "dynamic_candidate_id": candidate["candidate_id"],
            "evidence_digest": candidate["evidence_digest"],
            "state": "awaiting_operator_isolated_preparation",
            "isolated_preparation_phrase": f"Prepare isolated self-development proposal {proposal_id} digest {proposal_digest[:16]}.",
            "proposed_change": "Separate the selected helpers.",
        }
        return {"active": True, "event": "dynamic_self_development_proposal_created", "self_development_proposal": proposal}

    def prepared(_control, _root, *, operator_authorization_text=""):
        authorization_texts.append(operator_authorization_text)
        return {
            "active": True,
            "event": "isolated_self_development_workspace_prepared",
            "self_development_proposal": {
                "proposal_id": proposal_id,
                "proposal_digest": proposal_digest,
                "dynamic_candidate_id": candidate["candidate_id"],
                "evidence_digest": candidate["evidence_digest"],
                "state": "isolated_workspace_prepared",
            },
        }

    def implemented(_control, _root, *, provider_generate=None, operator_authorization_text=""):
        authorization_texts.append(operator_authorization_text)
        return {
            "active": True,
            "event": "isolated_self_development_candidate_ready",
            "self_development_proposal": {
                "proposal_id": proposal_id,
                "proposal_digest": proposal_digest,
                "dynamic_candidate_id": candidate["candidate_id"],
                "evidence_digest": candidate["evidence_digest"],
                "state": "isolated_implementation_review_ready",
                "implementation_result": {
                    "changed_file_count": 2,
                    "check_receipts": [{"passed": True}, {"passed": True}],
                    "provider_request_count": 0,
                },
            },
        }

    command = "Continue your supervised development."
    with (
        patch("v1489_product_capability_integration._installed_proposal_history", return_value=[]),
        patch("v1489_product_capability_integration.build_dynamic_improvement_discovery", return_value={"discovery_digest": "a" * 64}),
        patch("v1489_product_capability_integration.harden_dynamic_discovery", return_value=hardening),
        patch("v1489_product_capability_integration.compare_dynamic_candidates", return_value=comparison),
        patch("v1489_product_capability_integration._create_dynamic_proposal", side_effect=created) as create_mock,
        patch("v1489_product_capability_integration._prepare_isolated_proposal", side_effect=prepared) as prepare_mock,
        patch("v1489_product_capability_integration._implement_isolated_proposal", side_effect=implemented) as implement_mock,
    ):
        result = integrate_v1489_product_capabilities(command, {}, source_root=ROOT)

    require(result["event"] == "supervised_development_cycle_ready_for_operator_review", "one_command_reaches_review_boundary")
    require(result["completed_stages"] == ["initiative_selected", "initiative_advanced", "proposal_created", "workspace_prepared", "candidate_implemented_and_verified"], "reversible_stages_run_in_order")
    require(result["source_modified"] is False, "continue_cycle_preserves_active_source")
    require(result["operator_review_required"] is True, "cycle_stops_for_operator_review")
    require("Review and install candidate" in result["conversation_response"], "cycle_returns_exact_install_boundary")
    require(authorization_texts == [command, command, command], "one_explicit_command_binds_each_reversible_stage")
    require(create_mock.call_count == prepare_mock.call_count == implement_mock.call_count == 1, "each_stage_executes_exactly_once")

    queue = inspect_supervised_initiative_queue(runtime)
    latest = queue["recent_records"][-1]
    require(latest["lifecycle_state"] == "candidate_ready_for_review", "queue_tracks_candidate_review_state")
    require(latest["proposal_id"] == proposal_id, "queue_binds_exact_proposal")
    require(queue["active_count"] == 1, "review_ready_candidate_remains_visible")

    replay = integrate_v1489_product_capabilities(command, {}, source_root=ROOT)
    require(replay["event"] == "supervised_development_operator_review_required", "replay_stops_at_existing_review_boundary")
    require(replay["runtime_mutated"] is False, "replay_does_not_repeat_reversible_work")

    proposal_path = runtime / "self_development_proposals" / f"{proposal_id}.json"
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(json.dumps({
        "proposal_id": proposal_id,
        "dynamic_candidate_id": candidate["candidate_id"],
        "evidence_digest": candidate["evidence_digest"],
        "state": "operator_installed",
    }), encoding="utf-8")
    reconciled = reconcile_supervised_initiative_queue(runtime)
    require(reconciled["reconciled_count"] == 1, "installed_proposal_reconciles_once")
    require(reconciled["initiative_queue"]["active_count"] == 0, "installed_initiative_leaves_active_queue")
    require(reconciled["initiative_queue"]["recent_records"][-1]["lifecycle_state"] == "operator_installed", "installed_state_is_visible")
    require(reconcile_supervised_initiative_queue(runtime)["reconciled_count"] == 0, "installed_reconciliation_is_idempotent")
finally:
    if old_runtime is None:
        os.environ.pop("EIDOLON_DATA_DIR", None)
    else:
        os.environ["EIDOLON_DATA_DIR"] = old_runtime
    shutil.rmtree(temporary, ignore_errors=True)

require(source_signature() == before, "suite_preserves_authoritative_source")
print(json.dumps({
    "ok": True,
    "passed": len(CHECKS),
    "failed": 0,
    "checks": CHECKS,
    "suite": "v1501.2-sustained-supervised-initiative",
    "provider_contacted": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
}, indent=2, sort_keys=True))
