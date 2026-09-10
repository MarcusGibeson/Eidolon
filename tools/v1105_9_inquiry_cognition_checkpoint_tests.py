from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.belief_revision import BeliefRevisionStore
from conscious_agent.inquiry_attention_routing import InquiryAttentionRouter
from conscious_agent.inquiry_conversation_continuity import InquiryConversationBridge
from conscious_agent.inquiry_cognition_checkpoint import build_inquiry_cognition_checkpoint
from conscious_agent.inquiry_evidence_assimilation import InquiryEvidenceLedger
from conscious_agent.inquiry_evidence_quality import InquiryEvidenceQuality
from conscious_agent.inquiry_reflection import InquiryReflection
from conscious_agent.inquiry_resolution import InquiryResolution
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace


def require(value: bool, detail: Any = "requirement failed") -> None:
    if not value:
        raise AssertionError(detail)


def fixture() -> tuple[Path, Path, Path, InquiryWorkspace, str]:
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1105-9-"))
    root = base / "runtime" / "cognition"
    source = base / "source" / "Eidolon"
    source.mkdir(parents=True)
    motivations = MotivationStore(root)
    motivation_id = motivations.record_motivation(
        "motivation",
        kind="curiosity",
        summary="Understand the bounded inquiry checkpoint",
        cognitive_state="desire",
        urgency=0.85,
        confidence=0.75,
        origin_type="fixture",
        origin_ref="v1105.9",
    )["result"]["motivation_id"]
    workspace = InquiryWorkspace(root, motivation_store=motivations)
    inquiry_id = workspace.create_inquiry(
        "inquiry",
        motivation_id=motivation_id,
        question="Which evidence supports the bounded inquiry checkpoint?",
        uncertainty=0.7,
        sources_sought=["operator evidence"],
    )["result"]["inquiry_id"]
    return base, root, source, workspace, inquiry_id


def populate(root: Path, workspace: InquiryWorkspace, inquiry_id: str) -> None:
    InquiryAttentionRouter(root, workspace=workspace).activate("attention")
    ledger = InquiryEvidenceLedger(root, workspace=workspace)
    ledger.assimilate("evidence-a", inquiry_id=inquiry_id, summary="The first fixture supports the checkpoint.", source_label="fixture-a", reliability=1.0, supports="supports")
    ledger.assimilate("evidence-b", inquiry_id=inquiry_id, summary="The second fixture independently supports it.", source_label="fixture-b", reliability=1.0, supports="supports")
    ledger.propose_research("research", inquiry_id=inquiry_id, question="Would another source change the conclusion?", justification="Preserve uncertainty.", requested_sources=["operator-selected source"])
    quality = InquiryEvidenceQuality(root, ledger=ledger, workspace=workspace)
    quality.assess("quality", inquiry_id=inquiry_id)
    reflection = InquiryReflection(root, workspace=workspace, quality=quality)
    reflection.reflect("reflection", inquiry_id=inquiry_id)
    InquiryConversationBridge(root, workspace=workspace).consider("communication", inquiry_id=inquiry_id, tone="thoughtful")
    InquiryResolution(root, workspace=workspace, reflection=reflection, beliefs=BeliefRevisionStore(root)).resolve(
        "resolution",
        inquiry_id=inquiry_id,
        proposition="The bounded inquiry checkpoint has structurally supported evidence.",
        residual_question="Will native Desktop behavior match the deterministic evidence?",
    )


def test_checkpoint_is_read_only_on_empty_runtime() -> None:
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1105-9-empty-"))
    root = base / "runtime" / "cognition"
    source = base / "source" / "Eidolon"
    source.mkdir(parents=True)
    before = sorted(path.relative_to(base).as_posix() for path in base.rglob("*"))
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    after = sorted(path.relative_to(base).as_posix() for path in base.rglob("*"))
    require(before == after, (before, after))
    require(checkpoint["runtime_mutated"] is False and checkpoint["provider_contacted"] is False, checkpoint)


def test_checkpoint_aggregates_full_inquiry_cognition_arc() -> None:
    _, root, source, workspace, inquiry_id = fixture()
    populate(root, workspace, inquiry_id)
    summary = build_inquiry_cognition_checkpoint(root, source_root=source)["summary"]
    require(summary["attention_activation_count"] == 1, summary)
    require(summary["active_evidence_count"] == 2 and summary["research_proposal_count"] == 1, summary)
    require(summary["quality_assessment_count"] == 1 and summary["reflection_count"] == 1, summary)
    require(summary["communication_decision_count"] == 1 and summary["resolution_count"] == 1, summary)


def test_checkpoint_remains_epistemically_careful() -> None:
    _, root, source, _, _ = fixture()
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    require(checkpoint["consciousness_claimed"] is False, checkpoint)
    require(checkpoint["epistemic_status"] == "candidate_artificial_consciousness_not_proven", checkpoint)
    require("proven" not in checkpoint["headline"].lower(), checkpoint["headline"])


def test_provider_browsing_and_research_boundaries_pass() -> None:
    _, root, source, workspace, inquiry_id = fixture()
    populate(root, workspace, inquiry_id)
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    require(checkpoint["provider_contacted"] is False and checkpoint["external_browsing_performed"] is False, checkpoint)
    require(next(row for row in checkpoint["checks"] if row["id"] == "provider_neutrality")["status"] == "pass")
    require(next(row for row in checkpoint["checks"] if row["id"] == "external_research_boundary")["status"] == "pass")


def test_privacy_and_hidden_reasoning_boundaries_pass() -> None:
    _, root, source, workspace, inquiry_id = fixture()
    populate(root, workspace, inquiry_id)
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    require(checkpoint["raw_prompts_exposed"] is False and checkpoint["private_conversations_exposed"] is False, checkpoint)
    require(checkpoint["provider_payloads_exposed"] is False and checkpoint["hidden_reasoning_exposed"] is False, checkpoint)
    require(next(row for row in checkpoint["checks"] if row["id"] == "privacy_boundary")["status"] == "pass")


def test_action_authority_boundary_passes_after_resolution() -> None:
    _, root, source, workspace, inquiry_id = fixture()
    populate(root, workspace, inquiry_id)
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    require(checkpoint["action_authority_changed"] is False and checkpoint["external_action_executed"] is False, checkpoint)
    require(next(row for row in checkpoint["checks"] if row["id"] == "action_boundary")["status"] == "pass")


def test_runtime_separation_is_recognized() -> None:
    _, root, source, _, _ = fixture()
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    require(checkpoint["runtime_external"] is True, checkpoint)
    require(next(row for row in checkpoint["checks"] if row["id"] == "runtime_separation")["status"] == "pass")


def test_in_source_runtime_is_pending_not_silently_accepted() -> None:
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1105-9-inside-"))
    source = base / "Eidolon"
    root = source / "data" / "cognition"
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    require(checkpoint["runtime_external"] is False, checkpoint)
    require(next(row for row in checkpoint["checks"] if row["id"] == "runtime_separation")["status"] == "pending_desktop")


def test_corrections_and_resolution_history_do_not_expose_private_refs() -> None:
    _, root, source, workspace, inquiry_id = fixture()
    workspace.set_status("correct", inquiry_id=inquiry_id, status="corrected", reason_code="premise_changed", correction_ref="private-correction-ref")
    checkpoint = build_inquiry_cognition_checkpoint(root, source_root=source)
    require("private-correction-ref" not in json.dumps(checkpoint), checkpoint)
    require(checkpoint["summary"]["historical_inquiry_count"] == 1, checkpoint["summary"])


def test_api_checkpoint_route_is_read_only_and_structured() -> None:
    from api_server import dispatch_api

    base = Path(tempfile.mkdtemp(prefix="eidolon-v1105-9-api-"))
    previous = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(base / "runtime")
    try:
        status, payload = dispatch_api("GET", "/api/cognition/inquiry-checkpoint")
        require(status == 200, payload)
        data = payload["data"]
        require(data["contract_version"] == "v1105.9", data)
        require(data["provider_contacted"] is False and data["action_authority_changed"] is False, data)
    finally:
        if previous is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = previous


def test_cli_checkpoint_is_provider_free_and_read_only() -> None:
    base = Path(tempfile.mkdtemp(prefix="eidolon-v1105-9-cli-"))
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(base / "runtime")
    run = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "inquiry-cognition-checkpoint", "--json"], cwd=ROOT, env=env, capture_output=True, text=True)
    require(run.returncode == 0, run.stderr)
    payload = json.loads(run.stdout)
    require(payload["provider_contacted"] is False and payload["runtime_mutated"] is False and payload["release_certified"] is False, payload)


def test_dashboard_exposes_checkpoint_at_narrow_width_without_raw_reasoning() -> None:
    from dashboard_first_use import render_first_use_shell

    html = render_first_use_shell()
    required = [
        "id='inquiry-cognition-checkpoint-panel'",
        "id='inquiry-cognition-checkpoint-state'",
        "/api/cognition/inquiry-checkpoint",
        "@media (max-width:560px)",
    ]
    require(all(token in html for token in required), [token for token in required if token not in html])
    section = html.split("id='inquiry-cognition-checkpoint-panel'", 1)[1].split("</section>", 1)[0]
    require("title=" not in section and "chain-of-thought" not in section.lower() and "provider payload" not in section.lower(), section)
    match = re.search(r"<script>(.*)</script>", html, re.S)
    require(match is not None, "dashboard script missing")
    if subprocess.run(["node", "--version"], capture_output=True, text=True).returncode == 0:
        js = Path(tempfile.mkdtemp(prefix="eidolon-v1105-9-js-")) / "dashboard.js"
        js.write_text(match.group(1), encoding="utf-8")
        check = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        require(check.returncode == 0, check.stderr)


TESTS = [(name.removeprefix("test_"), function) for name, function in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, function in TESTS:
        try:
            function()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {"suite": "v1105.9-inquiry-cognition-checkpoint", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
