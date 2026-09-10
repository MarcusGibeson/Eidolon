"""Demand evidence admission, including the vendor-offerings trial regression."""
import json
import sys
import runpy
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / "conscious_agent")]
from bounded_research_reasoning import validate_research_synthesis, decompose_research_objective, build_source_strategy, plan_adaptive_follow_up
from conversational_research_actions import _research_report_message

checks = []
def check(value, name):
    assert value, name
    checks.append(name)

payload = {"findings": [{"title": "Market demand", "summary": "Demand is established by the variety of offerings.", "citation_ids": ["a", "b"]}]}
def source(cid, host, **changes):
    return {"citation_id": cid, "public_url": f"https://{host}/study", "source_kind": "primary_data", "freshness": "fresh", "stance": "supports", "relevance_score": 0.9, "quality_score": 0.9, **changes}
def admit(rows):
    return validate_research_synthesis(payload, citations=rows, required_evidence_dimension="demand")

for name, rows in [
    ("vendor_offerings_are_not_demand", [source("a", "vendor-one.example", source_kind="primary_official"), source("b", "vendor-two.example", source_kind="primary_official")]),
    ("unknown_stance_is_not_support", [source("a", "one.example", stance="unknown"), source("b", "two.example", stance="unknown")]),
    ("refuting_sources_cannot_support", [source("a", "one.example", stance="refutes"), source("b", "two.example", stance="refutes")]),
    ("repeated_publisher_is_not_independent", [source("a", "one.example"), source("b", "one.example")]),
    ("stale_sources_do_not_pass", [source("a", "one.example", freshness="stale"), source("b", "two.example", freshness="stale")]),
    ("irrelevant_sources_do_not_pass", [source("a", "one.example", relevance_score=0.1), source("b", "two.example", relevance_score=0.1)]),
]:
    result = admit(rows)
    check(not result["ok"] and not result["rendered_answer"], name)
    check(result["rejected_opportunity_reason_counts"].get("independent_dimension_support_missing") == 1, name + "_reason")

check(admit([source("a", "one.example"), source("b", "two.example")])["ok"], "independent_support_can_pass")
payload["findings"][0]["citation_ids"].append("c")
check(not admit([source("a", "one.example"), source("b", "two.example"), source("c", "three.example", stance="refutes")])["ok"], "supporting_majority_does_not_erase_conflict")
payload["findings"][0]["citation_ids"].pop()
plan = decompose_research_objective("Research dental waitlist scheduling demand.")
check(plan["subquestions"][0]["evidence_dimension"] == "demand", "demand_dimension_bound_to_plan")
follow = plan_adaptive_follow_up(plan, build_source_strategy(plan), {"claims": [{"claim_code": "rq1", "state": "incomplete"}]}, remaining_query_budget=1, remaining_page_budget=1, remaining_failure_budget=1)
query = follow["queries"][0]["query"]
check("dental" in query and "survey" in query and "complaints" in query, "follow_up_targets_customer_evidence_and_subject")
message = _research_report_message({}, {"status": "research_report_insufficient_evidence", "limitations": ["Vendor offerings do not establish demand."]})
check("Vendor offerings do not establish demand." in message, "operator_sees_rejection_reason")

fixture = runpy.run_path(str(root / "tools" / "v2730_9_4_research_trial_repair_tests.py"))
class UnsupportedDemandAdapter(fixture["NarrowDemandAdapter"]):
    def synthesize(self, **kwargs):
        return {"ok": True, "provider_contacted": True, "provider_request_count": 1,
                "payload": {"findings": [{"title": "Market demand", "summary": "Offerings prove strong market demand.",
                                           "citation_ids": ["web-fixture-1", "web-fixture-2"]}]}}
store = fixture["store"]
created = store.create_session("demand-gate-create", objective=fixture["objective"], budget=fixture["budget"])["result"]
auth = store.authorize_session("demand-gate-authorize", session_id=created["session_id"], session_digest=created["session_digest"], public_query_confirmed=True)["result"]
run = store.execute_session("demand-gate-execute", session_id=created["session_id"], authorization_digest=auth["authorization_digest"], adapter=UnsupportedDemandAdapter())
report = run["result"]["report"]
check(report["status"] == "research_report_insufficient_evidence", "normal_session_rejects_unsupported_model_demand")
check(not report["rendered_answer"], "rejected_prose_is_not_rendered")
check(any("Unsupported model conclusions were withheld" in text for text in report["limitations"]), "normal_session_explains_support_gap")
check("Unsupported model conclusions were withheld" in _research_report_message({}, report), "normal_chat_renders_specific_gap_before_generic_limits")
check(report["provider_request_count"] == 1, "rejected_synthesis_still_counts_provider_contact")
print(json.dumps({"ok": True, "passed": len(checks), "checks": checks}))
