from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
passed = 0


def require(condition):
    global passed
    assert condition
    passed += 1


with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    runtime_root = base / "runtime" / "cognition"
    runtime_root.mkdir(parents=True)
    os.environ["EIDOLON_DATA_DIR"] = str(base / "runtime")

    from conscious_agent.reflective_temporal_continuity_prospective_memory_checkpoint import (
        build_reflective_temporal_continuity_prospective_memory_checkpoint,
    )

    before = {
        path.relative_to(runtime_root).as_posix(): path.read_bytes()
        for path in runtime_root.rglob("*")
        if path.is_file()
    }
    report = build_reflective_temporal_continuity_prospective_memory_checkpoint(
        runtime_root,
        source_root=ROOT,
    )
    after = {
        path.relative_to(runtime_root).as_posix(): path.read_bytes()
        for path in runtime_root.rglob("*")
        if path.is_file()
    }

    require(report["contract_version"] == "v1117.9" and report["runtime_mutated"] is False and before == after)
    require(report["ok"] and len(report["checks"]) == 18 and all(row["status"] == "pass" for row in report["checks"]))
    require(set(report["summary"]) == {"prospective_memory_continuity", "temporal_review_continuity", "prospective_continuity_review"})
    require(next(row for row in report["checks"] if row["id"] == "prospective_obligation_persistence_lineage")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "missed_window_outcome_separation")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "bounded_prospective_review_sessions")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "prospective_outcome_evidence")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "future_commitment_reliability")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "false_pattern_suppression")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "operator_reviewed_rescheduling_boundary")["status"] == "pass")
    require(report["epistemic_status"] == "candidate_artificial_consciousness_not_proven" and not report["consciousness_claimed"])
    require(not any(report[key] for key in ("notification_created", "message_sent", "provider_contacted", "external_browsing_performed", "schedule_changed", "attention_selected", "intention_formed", "decision_committed", "proposal_created", "proposal_applied", "approval_granted", "authorization_granted", "external_action_executed", "release_approved", "release_promoted", "release_certified")))
    require(not any(report[key] for key in ("raw_messages_exposed", "raw_content_exposed", "prompts_exposed", "provider_payloads_exposed", "evidence_text_exposed", "hidden_reasoning_exposed", "private_content_exposed")))

    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api("GET", "/api/cognition/reflective-temporal-continuity-prospective-memory-checkpoint")
    require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1117.9")
    post_status, _ = dispatch_api("POST", "/api/cognition/reflective-temporal-continuity-prospective-memory-checkpoint", body={})
    require(post_status != 200)

    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "reflective-temporal-continuity-prospective-memory-checkpoint", "--json"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=dict(os.environ),
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1117.9")

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require("reflective-temporal-continuity-prospective-memory-checkpoint-panel" in dashboard and "/api/cognition/reflective-temporal-continuity-prospective-memory-checkpoint" in dashboard)
    require(report["runtime_external"] and report["desktop_verification_status"] == "pending")

print(json.dumps({"passed": passed, "total": 18, "suite": "v1117.9"}))
