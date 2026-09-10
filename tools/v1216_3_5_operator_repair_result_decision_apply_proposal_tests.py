from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1216-b-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import operator_repair_result_review as review
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1215_supervised_repair_fixture import build_authorized_repair_fixture, provider_output
from v1216_repair_result_review_fixture import build_repair_result_review_fixture

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


fixture = build_authorized_repair_fixture("b-chat")
runtime = fixture["runtime"]
calls: list[str] = []


def provider(prompt: str) -> str:
    calls.append(prompt)
    return provider_output(prompt, repaired=True)


try:
    turn = process_ordinary_chat_development_turn(
        fixture["repair_proposal"]["authorization_phrase"],
        runtime_root=runtime,
        provider_generate=provider,
        python_executable=sys.executable,
    )
    require(turn["active"] is True, turn)
    require(turn["event"] == "supervised_repair_completed", turn)
    require("operator_repair_result_review" in turn)
    packet = turn["operator_repair_result_review"]
    require(packet["ok"] is True, packet)
    require(packet["candidate_apply_eligible"] is True)
    require(len(packet["decision_phrases"]) == 4)
    require("choose one exact disposition" in turn["conversation_response"].lower())
    require("nothing has been applied" in turn["conversation_response"].lower())
    require(len(calls) == 1)

    phrase = next(value for value in packet["decision_phrases"] if "propose-apply" in value)
    decision_turn = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
    require(decision_turn["active"] is True, decision_turn)
    require(decision_turn["event"] == "operator_repair_result_decision_recorded")
    decision = decision_turn["operator_repair_result_review"]
    require(decision["decision"] == "propose-apply")
    require(decision["decision_state"] == "apply_proposal_requested")
    require(decision["apply_proposal_requested"] is True)
    apply_proposal = decision_turn["bounded_repaired_candidate_apply_proposal"]
    require(apply_proposal["ok"] is True, apply_proposal)
    require(apply_proposal["status"] == "bounded_repaired_candidate_apply_proposal_authorization_required")
    require(apply_proposal["apply_scope"] == "one_selected_project_apply_attempt")
    require(apply_proposal["apply_target"] == "exact_isolated_repaired_candidate")
    require(apply_proposal["maximum_apply_attempts"] == 1)
    require(apply_proposal["requires_exact_authorization"] is True)
    require(apply_proposal["apply_proposal_created"] is True)
    require(apply_proposal["apply_authorization_required"] is True)
    require(apply_proposal["apply_proposal_digest"] in apply_proposal["authorization_phrase"])
    require(packet["review_digest"] == apply_proposal["review_digest"])
    require(packet["supervised_repair_result_digest"] == apply_proposal["supervised_repair_result_digest"])
    require(packet["repair_workspace_digest"] == apply_proposal["repair_workspace_digest"])
    require(apply_proposal["provider_contacted"] is False)
    require(apply_proposal["tests_executed"] is False)
    require(apply_proposal["project_modified"] is False)
    require(apply_proposal["selected_project_modified"] is False)
    require(apply_proposal["source_modified"] is False)
    require(apply_proposal["apply_authorized"] is False)
    require(apply_proposal["rollback_authorized"] is False)
    require(apply_proposal["install_authorized"] is False)
    require(apply_proposal["promotion_authorized"] is False)
    require(apply_proposal["release_authorized"] is False)
    require(apply_proposal["authority_granted"] is False)
    require("no apply has run" in decision_turn["conversation_response"].lower())
    require(len(calls) == 1)

    replay = process_ordinary_chat_development_turn(phrase, runtime_root=runtime)
    require(replay["operator_repair_result_review"]["operation_status"] == "resumed")
    require(replay["bounded_repaired_candidate_apply_proposal"]["operation_status"] == "resumed")
    require(replay["bounded_repaired_candidate_apply_proposal"]["apply_proposal_digest"] == apply_proposal["apply_proposal_digest"])
    require(len(calls) == 1)
    require(review.process_operator_repair_result_review_control(
        apply_proposal["authorization_phrase"], runtime_root=runtime
    ) == {"active": False, "event": "inactive"})
    encoded = json.dumps(decision_turn, sort_keys=True)
    require("count_words" not in encoded)
    require("return 0" not in encoded)
    require(str(runtime) not in encoded)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

failed_fixture = build_repair_result_review_fixture(passed=False, seed="b-fail")
try:
    packet = failed_fixture["repair_result_review"]
    forged = review._review_phrase(
        "propose-apply", packet["review_digest"], packet["proposal_id"], 1, 2
    )
    blocked = review.process_operator_repair_result_review_control(
        forged, runtime_root=failed_fixture["runtime"]
    )
    require(blocked["active"] is True)
    require(blocked["event"] == "operator_repair_result_decision_not_allowed")
    require(blocked["operator_repair_result_review"]["apply_authorized"] is False)
    require("bounded_repaired_candidate_apply_proposal" not in blocked)
finally:
    shutil.rmtree(failed_fixture["runtime"], ignore_errors=True)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1216.5-operator-repair-result-decision-apply-proposal"') == 2)
require(release.count("tools/v1216_3_5_operator_repair_result_decision_apply_proposal_tests.py") == 1)

print(json.dumps({
    "ok": True,
    "version": "1216.5",
    "checks": len(checks),
    "passed": sum(checks),
    "apply_proposal_prepared": True,
    "apply_executed": False,
    "additional_provider_calls": 0,
}, sort_keys=True))
