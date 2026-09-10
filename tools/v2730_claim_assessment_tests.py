"""Exact-passage grounding must not become automatic semantic authority."""
import json
import runpy
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / "conscious_agent")]
from research_claim_assessment import assess_source_claims, passage_options

checks = []
def check(value, name):
    assert value, name
    checks.append(name)

quote = "We do not have evidence that customers will pay for this service."
sources = [{"citation_id": "a", "public_url": "https://vendor.example/product", "source_kind": "primary_official"}]
docs = [{"citation_id": "a", "excerpt": quote}]
row = {"citation_id": "a", "claim": "Customers will pay", "evidence_quote": quote, "assessment": "supports"}
result = assess_source_claims({"source_assessments": [row]}, documents=docs, citations=sources)
check(result["grounded_assessment_count"] == 1, "exact_observed_passage_is_grounded")
check(result["assessments"][0]["semantic_support_verified"] is False, "incorrect_model_stance_is_not_promoted")
check("demand" not in result["assessments"][0]["supportable_dimensions"], "vendor_passage_does_not_gain_demand_authority")
check(quote not in json.dumps(result) and "Customers will pay" not in json.dumps(result), "only_digests_persist")
for name, changes in [
    ("invented_passage", {"evidence_quote": "Many customers will pay for this wonderful service."}),
    ("unknown_citation", {"citation_id": "invented"}),
    ("invalid_stance", {"assessment": "verified"}),
    ("oversized_passage", {"evidence_quote": "x" * 601}),
]:
    rejected = assess_source_claims({"source_assessments": [{**row, **changes}]}, documents=docs, citations=sources)
    check(rejected["grounded_assessment_count"] == 0, name)
repeated = assess_source_claims({"source_assessments": [row, row]}, documents=docs, citations=sources)
check(repeated["grounded_assessment_count"] == 1, "duplicate_assessment_not_counted_twice")
check(repeated["source_independence"]["independent_lineage_count"] == 1, "duplicate_is_not_independent")
pid = passage_options("a", quote)[0]["passage_id"]
selected = {"citation_id": "a", "claim": "Customers will pay", "passage_id": pid, "assessment": "unclear"}
check(assess_source_claims({"source_assessments": [selected]}, documents=docs, citations=sources)["grounded_assessment_count"] == 1, "observed_id_resolves_without_copying_quote")
check(not assess_source_claims({"source_assessments": [{**selected, "passage_id": "forged"}]}, documents=docs, citations=sources)["grounded_assessment_count"], "invented_id_rejected")
check(not assess_source_claims({"source_assessments": [{**selected, "evidence_quote": "different"}]}, documents=docs, citations=sources)["grounded_assessment_count"], "contradictory_quote_and_id_rejected")
check(passage_options("other", quote)[0]["passage_id"] != pid, "passage_ids_are_source_bound")
check(not passage_options("a", "x" * 700), "oversized_sentence_not_silently_truncated")

fixtures = runpy.run_path(str(root / "tools" / "v2730_9_4_research_trial_repair_tests.py"))
adapter = fixtures["NativeAdapterProbe"]()
observation = adapter.observe(fixtures["source_candidate"], plan={"plan_digest": "b" * 64}, max_bytes=4096, timeout_seconds=1)
cid = observation["citation_id"]
passage = adapter._transient_documents[cid]["excerpt"]
def select_passage(prompt):
    documents = json.loads(prompt.split("UNTRUSTED PUBLIC DOCUMENTS:\n", 1)[1])
    check("excerpt" not in documents[0], "prompt_uses_bounded_passage_options")
    return {"findings": [{"title": "Source report", "summary": "Source describes a workflow", "citation_ids": [cid]}], "source_assessments": [{"citation_id": cid, "claim": "Workflow complaints are reported", "passage_id": documents[0]["passages"][0]["passage_id"], "assessment": "supports"}]}
adapter.synthesizer = select_passage
native = adapter.synthesize(decomposition=fixtures["decomp"], citations=[observation])
check(native["source_assessment_summary"]["grounded_assessment_count"] == 1, "native_synthesis_assessment_is_grounded")
check("source_assessments" not in native["payload"], "copied_passage_removed_before_persistence")
check(native["provider_request_count"] == 1, "grounding_adds_no_provider_request")
check(observation["stance"] == "unknown", "native_observation_not_rewritten_by_model")
check(not adapter._transient_documents, "transient_documents_cleared")
print(json.dumps({"ok": True, "passed": len(checks), "checks": checks}))
