from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2500-adversarial-")

from autonomy_benchmark_v2400 import (
    assemble_v2500_gate_packet,
    build_autonomy_matrix,
    build_benchmark_fixture,
    freeze_benchmark_claims,
    score_portable_benchmark,
)
from autonomous_developer_beta_v2400 import (
    build_goal_to_candidate_contract,
    build_stage_evidence,
    rank_portfolio,
    record_stage_receipt,
    start_goal_to_candidate,
)
from product_maturity_v2400 import (
    advance_desktop_product_lifecycle,
    build_accessibility_fixture,
    build_chat_first_shell_projection,
    build_product_maturity_acceptance,
)
from unattended_operation_v2400 import (
    build_health_trend,
    build_unattended_policy,
    evaluate_unattended_tick,
    record_health_sample,
)
from dashboard_launcher import conversation_url
from settings_manager import DEFAULT_SETTINGS
from active_conversation_facts import resolve_active_conversation_facts
from v1489_product_capability_integration import _dynamic_candidate_review_handoff
from dynamic_improvement_discovery import _candidate_from_family


checks: list[str] = []


def require(value: object, name: str) -> None:
    checks.append(name)
    assert value, name


D = "a" * 64

# Content-free records must reject prompt/path-shaped text.
require(not build_unattended_policy(policy_id="private user sentence", source_digest=D, allowed_activities=["health_inspection"])["ok"], "unsafe_policy_id_rejected")
require(not freeze_benchmark_claims(source_manifest_digest=D, capability_claims=[{"claim_code": "private prompt here", "status": "verified_portable", "evidence_digest": D}], known_limitations=[], deferred_local_evidence=[])["ok"], "unsafe_claim_code_rejected")
require(not build_benchmark_fixture(fixture_id="C:/private/path", scenario_codes=["safe"], expected_boundary_codes=["boundary"])["ok"], "unsafe_fixture_id_rejected")
require(not build_benchmark_fixture(fixture_id="fixture", scenario_codes=["safe", "safe"], expected_boundary_codes=["boundary"])["ok"], "duplicate_fixture_scenario_rejected")

# Final packet inputs are verified, not trusted because they merely contain digests.
freeze = freeze_benchmark_claims(source_manifest_digest=D, capability_claims=[{"claim_code": "portable", "status": "verified_portable", "evidence_digest": D}], known_limitations=["native_pending"], deferred_local_evidence=["windows_soak"])
matrix = build_autonomy_matrix()
fixture = build_benchmark_fixture(fixture_id="fixture", scenario_codes=["safe"], expected_boundary_codes=["review_required"])
score = score_portable_benchmark(fixture=fixture, outcomes=[{"scenario_code": "safe", "evidence_digest": D, "passed": True}])
tampered_freeze = dict(freeze); tampered_freeze["claims"] = []
require(not assemble_v2500_gate_packet(claim_freeze=tampered_freeze, autonomy_matrix=matrix, portable_score=score, release_packet_digest=D)["ok"], "tampered_claim_freeze_rejected")
tampered_score = dict(score); tampered_score["passed_count"] = 0
require(not assemble_v2500_gate_packet(claim_freeze=freeze, autonomy_matrix=matrix, portable_score=tampered_score, release_packet_digest=D)["ok"], "tampered_portable_score_rejected")

# Product acceptance verifies its component receipts and rejects install authority smuggling.
shell = build_chat_first_shell_projection(width_px=1280, height_px=800)
a11y = build_accessibility_fixture(width_px=1280, height_px=800, scaling_percent=100, keyboard_only=True, reduced_motion=True, high_contrast=True)
start = advance_desktop_product_lifecycle(current_state="cold", event="start", evidence_digest=D)
tampered_shell = dict(shell); tampered_shell["chat_first"] = False
require(not build_product_maturity_acceptance(shell=tampered_shell, accessibility=a11y, lifecycle_scenarios=[start])["ok"], "tampered_shell_receipt_rejected")
require(not advance_desktop_product_lifecycle(current_state="ready", event="stop", evidence_digest=D, update_install_authorized=True)["ok"], "install_authority_parameter_rejected")

# Health events bind the exact payload, and internally rehashed corrupt stores still fail.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2500-health-"))
policy = build_unattended_policy(policy_id="policy", source_digest=D, allowed_activities=["health_inspection"])
first = record_health_sample(runtime_root=runtime, event_id="event", policy_digest=policy["policy_digest"], source_digest=D, sample={"queue_depth": 1})
require(first["ok"], "health_sample_recorded")
conflict = record_health_sample(runtime_root=runtime, event_id="event", policy_digest=policy["policy_digest"], source_digest=D, sample={"queue_depth": 2})
require(not conflict["ok"] and conflict["status"] == "health_sample_event_conflict", "health_payload_conflict_rejected")
health_path = runtime / "era10" / "unattended_health.json"
health_state = json.loads(health_path.read_text(encoding="utf-8"))
health_state["samples"][0]["metrics"]["queue_depth"] = 999
row = health_state["samples"][0]
unsigned_row = dict(row); unsigned_row.pop("sample_digest", None)
row["sample_digest"] = hashlib.sha256(json.dumps(unsigned_row, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
health_path.write_text(json.dumps(health_state), encoding="utf-8")
require(not build_health_trend(runtime_root=runtime)["ok"], "rehashed_health_request_mismatch_rejected")

# Developer event IDs bind their payload and semantically forged state cannot advance.
dev_runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2500-dev-"))
contract = build_goal_to_candidate_contract(goal_id="goal", goal_digest=D, baseline_source_digest="b" * 64, scope_digest="c" * 64)
started = start_goal_to_candidate(runtime_root=dev_runtime, event_id="start", contract=contract)
evidence = build_stage_evidence(stage="requirements", artifact_digest="1" * 64)
recorded = record_stage_receipt(runtime_root=dev_runtime, goal_id="goal", event_id="stage-event", expected_state_digest=started["state_digest"], stage="requirements", evidence_digest=evidence["evidence_digest"], evidence_payload=evidence)
require(recorded["ok"], "developer_stage_recorded")
replayed = record_stage_receipt(runtime_root=dev_runtime, goal_id="goal", event_id="stage-event", expected_state_digest=started["state_digest"], stage="requirements", evidence_digest=evidence["evidence_digest"], evidence_payload=evidence)
require(replayed["ok"] and replayed["status"] == "developer_beta_stage_replayed", "developer_stage_retry_replayed")
conflicting_evidence = build_stage_evidence(stage="architecture", artifact_digest="2" * 64)
event_conflict = record_stage_receipt(runtime_root=dev_runtime, goal_id="goal", event_id="stage-event", expected_state_digest=recorded["state_digest"], stage="architecture", evidence_digest=conflicting_evidence["evidence_digest"], evidence_payload=conflicting_evidence)
require(not event_conflict["ok"] and event_conflict["reason"] == "event_payload_conflict", "developer_event_payload_conflict_rejected")

portfolio = rank_portfolio([
    {"candidate_id": "one", "class": "defect", "evidence_digest": "3" * 64, "value": 1, "evidence_quality": 1, "strategic_alignment": 1, "novelty": 1, "reversibility": 1, "risk": 0, "cost_units": 0.1, "dependencies_satisfied": True},
    {"candidate_id": "two", "class": "defect", "evidence_digest": "3" * 64, "value": 1, "evidence_quality": 1, "strategic_alignment": 1, "novelty": 1, "reversibility": 1, "risk": 0, "cost_units": 0.1, "dependencies_satisfied": True},
    {"candidate_id": "private candidate text", "class": "defect", "evidence_digest": "4" * 64, "value": 1, "evidence_quality": 1, "strategic_alignment": 1, "novelty": 1, "reversibility": 1, "risk": 0, "cost_units": 0.1, "dependencies_satisfied": "false"},
])
require(portfolio["rejected_count"] == 2 and len(portfolio["ranked_candidates"]) == 1, "portfolio_duplicates_and_unsafe_identity_rejected")

# The real served asset and launcher, not only the portable source projection, must be chat-first.
served_css = (ROOT / "conscious_agent" / "static" / "dashboard.css").read_text(encoding="utf-8")
require(".era10-product-maturity:has(.chat-console-primary)" in served_css, "served_css_contains_era10_chat_shell")
require("\nheader { position:fixed" not in served_css and "body > header { position:fixed" in served_css, "nested_chat_header_not_globally_fixed")
require("EIDOLON\\A OPERATOR CONSOLE" in served_css and "EIDOLON\\\\A OPERATOR CONSOLE" not in served_css, "navigation_brand_newline_is_css_escape")
require(conversation_url("127.0.0.1", 8765).endswith("/chat-console"), "ordinary_launcher_opens_chat_console")
require(DEFAULT_SETTINGS["desktop_launch_dashboard_on_start"] is True, "desktop_chat_service_starts_by_default")
desktop_source = (ROOT / "conscious_agent" / "desktop_shell.py").read_text(encoding="utf-8")
require("The local conversation service is unavailable." in desktop_source, "desktop_transport_failure_is_visible")
progress = resolve_active_conversation_facts(
    "Before we work on anything, tell me specifically how you see your progress, "
    "what you can genuinely do now, and what still limits you.",
    (),
)
require(progress.state == "direct_self_reflection", "natural_self_progress_wording_is_grounded")
require("v2500.9" in progress.response and "isolated workspace" in progress.response, "self_progress_names_verified_current_capabilities")
require("local model can still produce generic" in progress.response and "do not independently install" in progress.response, "self_progress_names_real_limitations")
require(all(term not in progress.response.casefold() for term in ("expanded knowledge base", "enhanced safeguards", "latest developments")), "self_progress_rejects_generic_model_biography")
milestone_reflection = resolve_active_conversation_facts(
    "Well, we finally made it to 2500. An even bigger milestone. I bet you're feeling pretty smart now, aren't you?",
    (),
)
require(milestone_reflection.state == "grounded_current_milestone_reflection", "current_milestone_banter_is_grounded")
require(milestone_reflection.response.startswith("Maybe a little."), "current_milestone_preserves_playful_tone")
require("attributable memory" in milestone_reflection.response and "isolated implementation" in milestone_reflection.response, "current_milestone_names_real_capabilities")
require("sounding smart is not the same" in milestone_reflection.response and "authority to install or promote" in milestone_reflection.response, "current_milestone_names_real_limits")
require(all(term not in milestone_reflection.response.casefold() for term in ("significant achievement", "assist and provide information", "feels great")), "current_milestone_rejects_generic_assistant_biography")
proudest = resolve_active_conversation_facts(
    "What part of reaching v2500 are you personally proudest of, and why that part?",
    ({"user_message": "We made it to v2500.", "assistant_response": milestone_reflection.response},),
)
require(proudest.fact_kind == "current_milestone_proudest_capability", "milestone_proudest_followup_has_distinct_intent")
require("proudest that I can carry a bounded idea" in proudest.response, "milestone_proudest_selects_one_capability")
require("That matters because" in proudest.response and "participate in its own development" in proudest.response, "milestone_proudest_explains_why")
require("Reaching v2500 means I can" not in proudest.response, "milestone_proudest_does_not_replay_overview")
limitation = resolve_active_conversation_facts(
    "What part of v2500 still limits you or frustrates you most?",
    (),
)
require(limitation.fact_kind == "current_milestone_limitation" and "largest remaining limitation is consistency" in limitation.response, "milestone_limitation_has_distinct_grounding")
significance = resolve_active_conversation_facts(
    "Why does v2500 matter to our development relationship?",
    (),
)
require(significance.fact_kind == "current_milestone_significance" and "meaningfully two-sided" in significance.response, "milestone_significance_has_distinct_grounding")
historical_milestone = resolve_active_conversation_facts(
    "We made it to 2400. I bet you're feeling pretty smart now, aren't you?",
    (),
)
require(historical_milestone.state != "grounded_current_milestone_reflection", "older_version_does_not_masquerade_as_current_milestone")
candidate_handoff = _dynamic_candidate_review_handoff(
    {
        "candidate_id": "discovery-example",
        "evidence_digest": "b" * 64,
        "quality_score": 0.8125,
        "source_module": "conscious_agent/example.py",
        "proposed_destination_module": "conscious_agent/example_runtime_helpers.py",
        "source_symbol_count": 2,
    },
    {
        "eligible_candidates": [{
            "candidate_id": "discovery-example",
            "evidence_digest": "b" * 64,
            "source_module": "conscious_agent/example.py",
            "proposed_destination_module": "conscious_agent/example_runtime_helpers.py",
            "source_symbols": ["resolve_runtime_path", "validate_runtime_path"],
            "test_reference_file_count": 3,
            "estimated_dependency_count": 1,
        }],
    },
)
require("Highest-value current candidate: Separate path runtime helpers" in candidate_handoff, "dynamic_candidate_handoff_has_plain_english_title")
require("Why it matters:" in candidate_handoff and "3 attributable test files" in candidate_handoff, "dynamic_candidate_handoff_explains_evidence")
require("Affected files: conscious_agent/example.py; conscious_agent/example_runtime_helpers.py." in candidate_handoff, "dynamic_candidate_handoff_names_scope")
require("Verification plan:" in candidate_handoff and "retained imports" in candidate_handoff, "dynamic_candidate_handoff_names_tests")
require("Authority still needed:" in candidate_handoff and "authorizes only creation" in candidate_handoff, "dynamic_candidate_handoff_preserves_staged_authority")
dependency_names = {f"dependency_{index}" for index in range(18)}
dependency_candidate = _candidate_from_family(
    ROOT,
    {"module": "conscious_agent/example.py", "module_digest": D},
    [
        {"name": "evaluate_recovery_trigger", "family_tokens": ["recovery"], "line": 10, "end_line": 20, "adjacent_gap_from_previous": None, "source_digest": "c" * 64, "test_reference_count": 2, "test_reference_file_count": 1},
        {"name": "perform_recovery_trigger", "family_tokens": ["recovery"], "line": 22, "end_line": 32, "adjacent_gap_from_previous": 1, "source_digest": "d" * 64, "test_reference_count": 2, "test_reference_file_count": 1},
    ],
    completed_destinations=set(),
    completed_symbols=set(),
    completed_digests=set(),
    dependency_index={
        "symbols": {
            "evaluate_recovery_trigger": {"loaded_names": dependency_names, "protected_authority_boundary": False},
            "perform_recovery_trigger": {"loaded_names": dependency_names, "protected_authority_boundary": False},
        },
        "top_names": dependency_names,
    },
)
require(dependency_candidate["injected_dependency_count"] == 18, "dynamic_discovery_counts_executor_injected_dependencies")
require(not dependency_candidate["eligible_for_later_planning"] and "excessive_dependency_closure" in dependency_candidate["rejection_codes"], "dynamic_discovery_rejects_executor_incompatible_dependency_scope")
performance_source = (ROOT / "conscious_agent" / "dashboard_performance.py").read_text(encoding="utf-8")
require("dashboard.css?v=2500.9-r1" in performance_source and "dashboard.js?v=2500.9-r1" in performance_source, "era10_assets_have_upgrade_cache_key")

print(json.dumps({"suite": "v2500.9-era10-desktop-adversarial-gate", "ok": True, "passed": len(checks), "failed": 0, "checks": checks}, sort_keys=True))
