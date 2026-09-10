from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.v1142_6_operator_correction_reliability_review_tests import seed
from conscious_agent.operator_correction_reliability_review import OperatorCorrectionReliabilityReviewStore
from conscious_agent.operator_correction_visible_behavior_evidence import OperatorCorrectionVisibleBehaviorEvidenceStore
from conscious_agent.operator_correction_acceptance_learning_governance_checkpoint import (
    build_operator_correction_acceptance_learning_governance_checkpoint,
)

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"
    application_id, continuity_id = seed(runtime)
    reviews = OperatorCorrectionReliabilityReviewStore(runtime)
    evidence = OperatorCorrectionVisibleBehaviorEvidenceStore(runtime)
    review_id = reviews.register(
        "governance-review",
        application_id=application_id,
        continuity_id=continuity_id,
        expected_influence=True,
        observed_influence=True,
    )["review_id"]
    evidence.register(
        "governance-evidence",
        review_id=review_id,
        behavior_surface_id="reflection",
    )

    report = build_operator_correction_acceptance_learning_governance_checkpoint(
        runtime, source_root=ROOT
    )
    require(report["contract_version"] == "v1142.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 20)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1142.2")
    require(report["integration"]["contract_version"] == "v1142.5")
    require(report["reliability"]["contract_version"] == "v1142.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "operator_text_exposed",
                "reasoning_text_exposed",
                "conversation_exposed",
                "prompt_exposed",
                "provider_payload_exposed",
                "private_project_record_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "history_rewritten",
                "belief_mutated",
                "goal_mutated",
                "motivation_mutated",
                "self_model_mutated",
                "reasoning_executed",
                "approval_created",
                "authorization_created",
                "external_action_executed",
                "installation_performed",
                "promotion_performed",
                "certification_performed",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["eligibility_created_by_checkpoint"]
        and not report["guidance_created_by_checkpoint"]
        and not report["application_created_by_checkpoint"]
        and not report["continuity_created_by_checkpoint"]
        and not report["reliability_review_created_by_checkpoint"]
        and not report["visible_evidence_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "operator-correction-acceptance-learning-governance-checkpoint",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1142.9"
    )

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api(
            "GET",
            "/api/cognition/operator-correction-acceptance-learning-governance-checkpoint",
        )
        require(
            status == 200
            and (payload.get("data") or {}).get("contract_version") == "v1142.9"
        )
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/operator-correction-acceptance-learning-governance-checkpoint",
            body={},
        )
        require(post_status in (404, 405))
    finally:
        if old_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data_dir

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require(
        "operator-correction-acceptance-learning-governance-checkpoint-panel" in dashboard
        and "/api/cognition/operator-correction-acceptance-learning-governance-checkpoint" in dashboard
        and "loadOperatorCorrectionAcceptanceLearningGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1142, 9)
        and (working != (1142, 9) or previous == (1142, 8))
        and "v1142.9 Operator Correction and Acceptance Learning Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_record_count",
            "guidance_record_count",
            "application_record_count",
            "continuity_record_count",
            "reliability_review_count",
            "visible_evidence_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1142.9"}))
