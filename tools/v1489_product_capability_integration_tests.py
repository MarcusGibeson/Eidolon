from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v1489-product-integration-"))
PROJECT = RUNTIME / "selected-project"
PROJECT.mkdir(parents=True)
(PROJECT / "index.html").write_text("<!doctype html><title>Fixture</title>", encoding="utf-8")
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME / "runtime")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AGENT))

import conscious_agent.conversation_runtime as conversation_runtime_module
from conscious_agent.conversation_runtime import run_conversation_turn, stream_conversation_turn
from conscious_agent.conversation_sessions import create_conversation_session
from conscious_agent.initiative_communication_restraint import InitiativeCommunicationRestraint
from conscious_agent.v1489_product_capability_integration import (
    _apply_maintenance_helper_extraction,
    _apply_maintenance_task_queue_extraction,
    _blocked_self_development_explanation,
    _load_or_create_concrete_proposal,
    _next_improvement_spec,
    integrate_v1489_product_capabilities,
    public_v1489_product_capabilities,
)


passed = 0
failed = 0


def check(name: str, condition: bool, detail: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
        return
    failed += 1
    print("FAIL", name, detail)
    raise AssertionError(detail or name)


def manifest(root: Path) -> dict[str, tuple[int, int]]:
    # Production execution performs exact content manifests before and after this
    # suite. This local guard only needs to catch writes made by the test itself.
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


try:
    source_before = manifest(ROOT / "conscious_agent")
    project_before = manifest(PROJECT)

    enriched = integrate_v1489_product_capabilities(
        "Build a small calculator webpage and verify it works.",
        {"active": True, "event": "proposal_created", "authority_granted": False},
        project_state={"id": "fixture", "path": str(PROJECT)},
    )
    public = public_v1489_product_capabilities(enriched)
    check("production adapter adds planning evidence", public["reasoning_planning"]["candidate_approach_count"] >= 2, public)
    check("production adapter inventories selected project", public["practical_coding"]["project_file_count"] == 1, public)
    check("production adapter delegates execution", public["practical_coding"]["execution_owner"] == "isolated_coding_execution", public)
    check("production adapter grants no execution", public["reasoning_planning"]["authority_boundary"]["execution_authorized"] is False, public)

    self_session = create_conversation_session(title="v1489 product self inspection", select_session=False)
    self_turn = run_conversation_turn(
        "Inspect your own project and propose one improvement.",
        use_ai=True,
        session_id=self_session["id"],
        select_session_on_record=False,
    )
    check("ordinary chat reaches self-development assessment", self_turn.success and self_turn.completion_state == "development_campaign_lifecycle", self_turn.to_dict())
    check("self-development assessment is provider free", self_turn.provider_request_count == 0, self_turn.to_dict())
    check("self-development response names concrete source evidence", "conscious_agent/self_maintenance.py" in self_turn.response and "lines" in self_turn.response and "bytes" in self_turn.response, self_turn.response)
    check("self-development response reports focus testability truth", "no self_maintenance family currently meets attributable-test eligibility" in self_turn.response.casefold(), self_turn.response)
    check("self-development comparison may rank but never selects", "did not select a candidate" in self_turn.response and self_turn.to_dict().get("provider_request_count") == 0, self_turn.response)
    check("self-development discovery creates no new proposal authority", "create a proposal" in self_turn.response and "request approval" in self_turn.response, self_turn.response)
    check("self-development response is truthful", "contact a provider" in self_turn.response and "modify source" in self_turn.response, self_turn.response)

    evidence_session = create_conversation_session(title="v1489 evidence wording precedence", select_session=False)
    evidence_turn = run_conversation_turn(
        "Inspect your own project and propose one improvement. Explain what evidence supports it, what would change, and what approval you would need before modifying anything.",
        use_ai=True,
        session_id=evidence_session["id"],
        select_session_on_record=False,
    )
    check("development command outranks historical-memory fallback", evidence_turn.completion_state == "development_campaign_lifecycle", evidence_turn.to_dict())
    check("evidence wording remains provider free", evidence_turn.provider_request_count == 0, evidence_turn.to_dict())
    check("evidence wording does not produce memory denial", "attributable memory record" not in evidence_turn.response, evidence_turn.response)

    tiny_source = RUNTIME / "tiny-eidolon"
    tiny_agent = tiny_source / "conscious_agent"
    tiny_agent.mkdir(parents=True)
    (tiny_agent / "self_maintenance.py").write_text("def alpha():\n    return 1\n\ndef beta():\n    return 2\n", encoding="utf-8")
    (tiny_agent / "small.py").write_text("VALUE = 1\n", encoding="utf-8")
    tiny_before = manifest(tiny_source)
    tiny_assessment = integrate_v1489_product_capabilities(
        "Inspect your own project and propose one improvement.", {}, source_root=tiny_source
    )
    tiny_projection = tiny_assessment["v1489_supervised_self_development"]
    check("v1490 self inspection remains discovery only", tiny_projection["status"] == "dynamic_discovery_only" and tiny_projection["proposal_created"] is False, tiny_projection)
    check("tiny untestable source stops honestly", tiny_assessment["event"] == "dynamic_improvement_discovery_honest_stop", tiny_assessment)
    legacy_proposal = _load_or_create_concrete_proposal(tiny_source)
    check("legacy exact-authority proposal preparation remains available", legacy_proposal["proposal_id"].startswith("improvement-"), legacy_proposal)
    phrase = legacy_proposal["isolated_preparation_phrase"]
    prepared = integrate_v1489_product_capabilities(phrase, {}, source_root=tiny_source)
    check("exact phrase prepares isolated workspace", prepared["event"] == "isolated_self_development_prepared", prepared)
    check("isolated preparation preserves source", manifest(tiny_source) == tiny_before, prepared)
    replayed = integrate_v1489_product_capabilities(phrase, {}, source_root=tiny_source)
    check("isolated preparation is idempotent", replayed["event"] == "isolated_self_development_preparation_replayed", replayed)

    installed_path = RUNTIME / "runtime" / "self_development_proposals" / f"{legacy_proposal['proposal_id']}.json"
    installed = json.loads(installed_path.read_text(encoding="utf-8"))
    installed.update(
        {
            "state": "operator_installed",
            "implementation_result_digest": "fixture-installed-result",
            "implementation_result": {"changed_file_count": 2, "checks_passed": True},
        }
    )
    installed_path.write_text(json.dumps(installed, sort_keys=True), encoding="utf-8")
    next_assessment = integrate_v1489_product_capabilities(
        "Review your installed change, inspect your current source, and propose the next distinct development improvement.", {}, source_root=tiny_source
    )
    check("installed proposal does not restore catalog selection", next_assessment["v1489_supervised_self_development"]["status"] == "dynamic_discovery_only", next_assessment)
    check("dynamic discovery still grants no proposal authority", next_assessment["v1489_supervised_self_development"]["proposal_created"] is False, next_assessment)
    check("dynamic discovery remains provider free", next_assessment.get("provider_contacted") is False, next_assessment)

    installed_classes = [
        {"improvement_class": "bounded_maintainability_extraction"},
        {"improvement_class": "maintenance_task_queue_boundary_extraction"},
        {"improvement_class": "approval_record_boundary_extraction"},
    ]
    fourth = _next_improvement_spec(installed_classes)
    check("planner advances beyond original catalog", fourth is not None and fourth["improvement_class"] == "approval_revocation_boundary_extraction", fourth)
    check("planner never repeats exhausted catalog", _next_improvement_spec(installed_classes + [fourth]) is None)

    blocked_path = RUNTIME / "runtime" / "self_development_proposals" / "improvement-ffffffffffffffffffff.json"
    blocked_path.write_text(json.dumps({
        "proposal_id": "improvement-ffffffffffffffffffff",
        "state": "isolated_implementation_blocked",
        "implementation_failure_codes": ["symbol_refactoring_scope_requires_one_source_and_destination"],
        "provider_request_count": 0,
        "isolated_preparation_phrase": "Prepare isolated self-development proposal improvement-ffffffffffffffffffff digest 0123456789abcdef.",
    }), encoding="utf-8")
    blocked = _blocked_self_development_explanation()
    check("blocked receipt explains exact scope collision", "destination helper already existed" in blocked["conversation_response"], blocked)
    check("blocked receipt reports provider truth", "provider was not called" in blocked["conversation_response"].casefold(), blocked)
    followup = integrate_v1489_product_capabilities("Explain further", {})
    check("failure follow-up stays receipt grounded", followup["event"] == "self_development_failure_receipt_explained", followup)
    check("failure follow-up provides exact retry command", "say exactly:" in followup["conversation_response"], followup)

    extraction_root = RUNTIME / "bounded-helper-extraction"
    extraction_agent = extraction_root / "conscious_agent"
    extraction_agent.mkdir(parents=True)
    extraction_target = extraction_agent / "self_maintenance.py"
    extraction_target.write_text(
        "from pathlib import Path\nfrom typing import Any\n\n"
        + "\n".join(_apply_maintenance_helper_extraction.__globals__["_HELPER_DEFINITIONS"]),
        encoding="utf-8",
    )
    changed = _apply_maintenance_helper_extraction(extraction_root)
    check("bounded implementation changes exact allowlist", changed == ["conscious_agent/self_maintenance.py", "conscious_agent/self_maintenance_helpers.py"], changed)
    check("bounded implementation retains helper imports", "from self_maintenance_helpers import" in extraction_target.read_text(encoding="utf-8"))
    check("bounded implementation creates helper module", (extraction_agent / "self_maintenance_helpers.py").is_file())
    try:
        _apply_maintenance_helper_extraction(extraction_root)
    except RuntimeError:
        duplicate_blocked = True
    else:
        duplicate_blocked = False
    check("bounded implementation rejects duplicate application", duplicate_blocked)

    queue_root = RUNTIME / "bounded-task-queue-extraction"
    queue_agent = queue_root / "conscious_agent"
    queue_agent.mkdir(parents=True)
    queue_target = queue_agent / "self_maintenance.py"
    queue_globals = _apply_maintenance_task_queue_extraction.__globals__
    queue_target.write_text(
        "from typing import Any\nfrom self_maintenance_helpers import (\n    _read_json,\n)\n\n"
        + queue_globals["_TASK_SCORE_DEFINITION"]
        + queue_globals["_TASK_SELECTION_DEFINITIONS"],
        encoding="utf-8",
    )
    queue_changed = _apply_maintenance_task_queue_extraction(queue_root)
    queue_revised = queue_target.read_text(encoding="utf-8")
    check("task queue extraction changes exact allowlist", queue_changed == ["conscious_agent/self_maintenance.py", "conscious_agent/self_maintenance_task_queue.py"], queue_changed)
    check("task queue extraction retains bounded wrapper", "return _score_maintenance_goal_components(text, selected)" in queue_revised)
    check("task queue extraction imports selection helpers", "from self_maintenance_task_queue import" in queue_revised)
    check("task queue extraction creates focused module", (queue_agent / "self_maintenance_task_queue.py").is_file())

    stream_session = create_conversation_session(title="v1489 product self inspection stream", select_session=False)
    original_runtime_adapter = conversation_runtime_module.integrate_v1489_product_capabilities
    conversation_runtime_module.integrate_v1489_product_capabilities = (
        lambda message, lifecycle, project_state=None: integrate_v1489_product_capabilities(
            message, lifecycle, project_state=project_state, source_root=tiny_source
        )
    )
    try:
        stream = list(
            stream_conversation_turn(
                "Review Eidolon's source and identify the next development improvement. Explain what evidence supports it.",
                use_ai=True,
                session_id=stream_session["id"],
                select_session_on_record=False,
            )
        )
    finally:
        conversation_runtime_module.integrate_v1489_product_capabilities = original_runtime_adapter
    check("streaming chat reaches same production adapter", stream[-1]["event"] == "done" and stream[-1]["result"]["provider_request_count"] == 0, stream)

    restraint = InitiativeCommunicationRestraint(RUNTIME / "initiative")
    restraint.proposals.snapshot = lambda: {
        "proposals": [
            {
                "proposal_id": "proposal-fixture",
                "active": True,
                "eligible": True,
                "sensitivity": 0.1,
                "confidence": 0.9,
            }
        ]
    }
    eligible = restraint.decide(
        "event-eligible",
        proposal_id="proposal-fixture",
        user_present=True,
        user_receptive=True,
        conversation_active=True,
        meaningful_change=True,
    )
    check("existing initiative path invokes v1489 boundary", eligible["decision"]["v1489_boundary"]["surface_eligible"] is True, eligible)
    check("initiative boundary still cannot send", eligible["decision"]["v1489_boundary"]["can_send"] is False, eligible)
    private = restraint.decide(
        "event-private",
        proposal_id="proposal-fixture",
        user_present=True,
        user_receptive=True,
        conversation_active=True,
        meaningful_change=True,
        artifact_class="internal_thought",
    )
    check("private initiative is deferred by production path", private["status"] == "defer" and private["decision"]["reason_code"] == "private_artifact_boundary", private)

    check("selected project remains immutable", manifest(PROJECT) == project_before)
    check("authoritative source remains immutable", manifest(ROOT / "conscious_agent") == source_before)
finally:
    shutil.rmtree(RUNTIME, ignore_errors=True)

print(json.dumps({"ok": failed == 0, "passed": passed, "failed": failed}, sort_keys=True))
raise SystemExit(1 if failed else 0)
