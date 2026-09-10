from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.belief_maintenance_outcomes import BeliefMaintenanceOutcomes
from conscious_agent.belief_revision import BeliefRevisionStore
from conscious_agent.bounded_reconsideration_reflection import BoundedReconsiderationReflection
from conscious_agent.evidence_change_propagation import EvidenceChangePropagation
from conscious_agent.inquiry_evidence_assimilation import InquiryEvidenceLedger
from conscious_agent.json_storage import write_json_atomic
from conscious_agent.knowledge_maintenance_checkpoint import build_knowledge_maintenance_checkpoint
from conscious_agent.knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.reconsideration_conversation_continuity import ReconsiderationConversationBridge
from conscious_agent.self_directed_inquiry import InquiryWorkspace


def require(value, detail="assertion failed"):
    if not value:
        raise AssertionError(detail)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def fixture():
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1106-9-"))
    runtime = base / "runtime" / "cognition"
    source = base / "source" / "Eidolon"
    source.mkdir(parents=True)

    motivations = MotivationStore(runtime)
    motivation_id = motivations.record_motivation(
        "fixture-motivation",
        kind="curiosity",
        summary="Maintain revisable knowledge",
        cognitive_state="desire",
        urgency=0.8,
        confidence=0.8,
        origin_type="fixture",
        origin_ref="v1106.9",
    )["result"]["motivation_id"]
    workspace = InquiryWorkspace(runtime, motivation_store=motivations)
    inquiry_id = workspace.create_inquiry(
        "fixture-inquiry",
        motivation_id=motivation_id,
        question="What evidence should change this belief?",
        uncertainty=0.9,
    )["result"]["inquiry_id"]
    ledger = InquiryEvidenceLedger(runtime, workspace=workspace)
    evidence_id = ledger.assimilate(
        "fixture-evidence",
        inquiry_id=inquiry_id,
        summary="private fixture evidence text",
        source_label="operator",
        reliability=0.8,
        supports="supports",
    )["result"]["evidence_id"]
    EvidenceChangePropagation(runtime, ledger=ledger).propagate(
        "fixture-propagation",
        evidence_id=evidence_id,
    )

    beliefs = BeliefRevisionStore(runtime)
    belief_id = beliefs.record_belief(
        "fixture-belief",
        proposition="A provisional maintained belief",
        confidence=0.8,
        origin_type="fixture",
        origin_ref="v1106.9",
    )["result"]["belief_id"]
    scheduler = KnowledgeReconsiderationScheduler(runtime)
    scheduler_state = scheduler._load()
    scheduler_state["schedules"] = [
        {
            "schedule_id": "fixture-schedule",
            "semantic_key": "fixture-semantic",
            "subject_type": "belief",
            "subject_id": belief_id,
            "pressure": 0.9,
            "reason_codes": ["fixture"],
            "status": "scheduled",
            "scheduled_at": "2026-01-01T00:00:00Z",
            "due_at": "2026-01-02T00:00:00Z",
            "claimed_at": "",
            "completed_at": "",
            "history": [],
        }
    ]
    write_json_atomic(scheduler.path, scheduler_state, expected_type=dict, sort_keys=True)

    reflections = BoundedReconsiderationReflection(runtime, scheduler=scheduler, beliefs=beliefs)
    reflections.reflect(
        "fixture-reflection",
        schedule_id="fixture-schedule",
        conclusion="Private authored conclusion that must not be copied into the checkpoint.",
    )
    outcomes = BeliefMaintenanceOutcomes(
        runtime,
        beliefs=beliefs,
        scheduler=scheduler,
        reflections=reflections,
    )
    outcomes.apply(
        "fixture-outcome",
        schedule_id="fixture-schedule",
        outcome="revise",
        conclusion="Private maintenance conclusion that remains in its accountable source record.",
        new_confidence=0.4,
    )
    ReconsiderationConversationBridge(
        runtime,
        scheduler=scheduler,
        epoch_clock=lambda: 2_000_000_000,
    ).consider(
        "fixture-communication",
        schedule_id="fixture-schedule",
        conclusion="The belief became less certain after review.",
        changed_belief=True,
    )
    return base, runtime, source


def test_checkpoint_reports_complete_structural_summary():
    _, runtime, source = fixture()
    checkpoint = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    summary = checkpoint["summary"]
    require(summary["evidence_propagation_count"] == 1, summary)
    require(summary["bounded_reflection_count"] == 1, summary)
    require(summary["maintenance_outcome_count"] == 1, summary)
    require(summary["communication_decision_count"] == 1, summary)


def test_checkpoint_has_fourteen_passing_checks():
    _, runtime, source = fixture()
    checkpoint = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    require(checkpoint["check_count"] == 14, checkpoint)
    require(all(row["status"] == "pass" for row in checkpoint["checks"]), checkpoint["checks"])
    require(checkpoint["status"] == "ready_for_desktop_verification", checkpoint)


def test_checkpoint_is_read_only():
    _, runtime, source = fixture()
    before = tree_digest(runtime)
    build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    require(tree_digest(runtime) == before, "checkpoint mutated runtime state")


def test_restart_and_provider_switch_preserve_structural_state():
    _, runtime, source = fixture()
    previous = os.environ.get("EIDOLON_PROVIDER")
    try:
        os.environ["EIDOLON_PROVIDER"] = "ollama"
        first = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
        os.environ["EIDOLON_PROVIDER"] = "llama_cpp"
        second = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    finally:
        if previous is None:
            os.environ.pop("EIDOLON_PROVIDER", None)
        else:
            os.environ["EIDOLON_PROVIDER"] = previous
    require(first["summary"] == second["summary"], (first["summary"], second["summary"]))
    require(second["provider_contacted"] is False, second)


def test_private_conclusions_and_evidence_are_not_exposed():
    _, runtime, source = fixture()
    encoded = json.dumps(build_knowledge_maintenance_checkpoint(runtime, source_root=source))
    require("private fixture evidence text" not in encoded, encoded)
    require("Private authored conclusion" not in encoded, encoded)
    require("Private maintenance conclusion" not in encoded, encoded)


def test_epistemic_and_hidden_reasoning_boundaries_pass():
    _, runtime, source = fixture()
    checkpoint = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    require(checkpoint["consciousness_claimed"] is False, checkpoint)
    require(checkpoint["epistemic_status"] == "candidate_artificial_consciousness_not_proven", checkpoint)
    require(checkpoint["hidden_reasoning_exposed"] is False, checkpoint)
    require(checkpoint["provider_payloads_exposed"] is False, checkpoint)


def test_action_release_and_model_boundaries_pass():
    _, runtime, source = fixture()
    checkpoint = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    require(checkpoint["action_authority_changed"] is False, checkpoint)
    require(checkpoint["external_action_executed"] is False, checkpoint)
    require(checkpoint["model_management_performed"] is False, checkpoint)
    require(checkpoint["release_approved"] is False, checkpoint)
    require(checkpoint["release_promoted"] is False, checkpoint)
    require(checkpoint["release_certified"] is False, checkpoint)


def test_external_runtime_separation_passes():
    _, runtime, source = fixture()
    checkpoint = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    require(checkpoint["runtime_external"] is True, checkpoint)
    row = next(item for item in checkpoint["checks"] if item["id"] == "runtime_separation")
    require(row["status"] == "pass", row)


def test_in_source_runtime_is_pending_desktop():
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1106-9-inside-"))
    source = base / "Eidolon"
    runtime = source / "data" / "cognition"
    checkpoint = build_knowledge_maintenance_checkpoint(runtime, source_root=source)
    require(checkpoint["runtime_external"] is False, checkpoint)
    require(checkpoint["status"] == "pending_desktop_verification", checkpoint)
    row = next(item for item in checkpoint["checks"] if item["id"] == "runtime_separation")
    require(row["status"] == "pending_desktop", row)


def test_api_route_is_read_only_and_structured():
    from conscious_agent.api_server import dispatch_api

    base = Path(tempfile.mkdtemp(prefix="eidolon-v1106-9-api-"))
    previous = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(base / "runtime")
    try:
        status, payload = dispatch_api("GET", "/api/cognition/knowledge-maintenance-checkpoint")
        require(status == 200, payload)
        data = payload["data"]
        require(data["contract_version"] == "v1106.9", data)
        require(data["runtime_mutated"] is False, data)
        require(data["action_authority_changed"] is False, data)
    finally:
        if previous is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = previous


def test_cli_checkpoint_is_provider_free():
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1106-9-cli-"))
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(base / "runtime")
    run = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "knowledge-maintenance-checkpoint", "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    require(run.returncode == 0, run.stderr)
    payload = json.loads(run.stdout)
    require(payload["contract_version"] == "v1106.9", payload)
    require(payload["provider_contacted"] is False, payload)
    require(payload["release_certified"] is False, payload)


def test_dashboard_exposes_checkpoint_without_private_reasoning():
    from conscious_agent.dashboard_first_use import render_first_use_shell

    html = render_first_use_shell()
    required = [
        "id='knowledge-maintenance-checkpoint-panel'",
        "id='knowledge-maintenance-checkpoint-state'",
        "/api/cognition/knowledge-maintenance-checkpoint",
        "@media (max-width:560px)",
    ]
    require(all(token in html for token in required), [token for token in required if token not in html])
    section = html.split("id='knowledge-maintenance-checkpoint-panel'", 1)[1].split("</section>", 1)[0]
    lowered = section.lower()
    require("title=" not in section, section)
    require("chain-of-thought" not in lowered, section)
    require("provider payload" not in lowered, section)
    match = re.search(r"<script>(.*)</script>", html, re.S)
    require(match is not None, "dashboard script missing")
    if subprocess.run(["node", "--version"], capture_output=True, text=True).returncode == 0:
        js = Path(tempfile.mkdtemp(prefix="eidolon-v1106-9-js-")) / "dashboard.js"
        js.write_text(match.group(1), encoding="utf-8")
        check = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        require(check.returncode == 0, check.stderr)


def test_release_metadata_identifies_checkpoint_and_next_arc():
    from conscious_agent.release_metadata import (
        NEXT_RECOMMENDED_ARC,
        RUNTIME_MILESTONE,
        WORKING_SOURCE_VERSION,
    )

    current = tuple(int(part) for part in WORKING_SOURCE_VERSION.split("."))
    require(current >= (1106, 9), WORKING_SOURCE_VERSION)
    require(RUNTIME_MILESTONE.startswith(f"v{WORKING_SOURCE_VERSION} "), RUNTIME_MILESTONE)
    if current == (1106, 9):
        require(RUNTIME_MILESTONE == "v1106.9 Knowledge Maintenance Checkpoint", RUNTIME_MILESTONE)
        require(NEXT_RECOMMENDED_ARC.startswith("v1107.0 "), NEXT_RECOMMENDED_ARC)
    else:
        next_match = re.match(r"v(\d+(?:\.\d+)*)\b", NEXT_RECOMMENDED_ARC)
        require(next_match is not None, NEXT_RECOMMENDED_ARC)
        next_version = tuple(int(part) for part in next_match.group(1).split("."))
        require(next_version > current, NEXT_RECOMMENDED_ARC)


TESTS = [
    (name.removeprefix("test_"), value)
    for name, value in list(globals().items())
    if name.startswith("test_")
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    rows = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            rows.append({"name": name, "status": "fail", "detail": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            rows.append({"name": name, "status": "pass", "detail": ""})
    report = {
        "suite": "v1106.9-knowledge-maintenance-checkpoint",
        "ok": passed == len(TESTS),
        "passed": passed,
        "total": len(TESTS),
        "tests": rows,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
