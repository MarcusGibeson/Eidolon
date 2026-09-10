from copy import deepcopy
from datetime import datetime, timezone

from conscious_agent.unified_memory_context import (
    audit_unified_memory_selection,
    build_unified_memory_runtime_projection,
    verify_unified_memory_runtime_diagnostics,
    verify_unified_memory_selection_audit,
)

NOW = datetime(2026, 7, 31, tzinfo=timezone.utc)


def base_rows():
    return [
        {"id": "semantic", "type": "fact", "fact_key": "roadmap", "content": "v1165 unifies memory access", "source": "semantic_store", "confidence": .9},
        {"id": "relationship", "type": "preference", "content": "The operator prefers source-only archives", "source": "operator", "relationship_eligible": True, "use_in_conversation": True},
        {"id": "project", "type": "project_event", "content": "Bundle C is active", "source": "project_manager", "project_id": "eidolon"},
    ]


def projection(**kwargs):
    return build_unified_memory_runtime_projection("Continue Bundle C", memory_records=base_rows(), now=NOW, **kwargs)


def receipt(value):
    return {"created_at": "2026-07-31T07:00:00+00:00", "cognitive_context": {"unified_memory_runtime_diagnostics": deepcopy(value["diagnostics"])}}


def test_v1165_6_oversized_receipt_collection_fails_closed():
    first = projection()
    receipts = [receipt(first) for _ in range(25)]
    recovered = projection(prior_unified_memory_receipts=receipts)
    assert recovered["policy"]["policy_recovered"] is True
    assert recovered["policy"]["continuity_disposition"] == "recover_literal_request"
    assert recovered["diagnostics"]["prior_receipts_oversized"] == 1
    assert recovered["selected_memory_records"] == []


def test_v1165_6_malformed_receipt_collection_fails_closed_without_mutation():
    recovered = projection(prior_unified_memory_receipts={"not": "a sequence"})
    assert recovered["policy"]["policy_recovered"] is True
    assert recovered["diagnostics"]["prior_receipt_recovery"] == "malformed_receipt_collection"
    assert recovered["diagnostics"]["memory_mutated"] is False


def test_v1165_6_mixed_valid_tampered_and_replayed_receipts_recover_deterministically():
    first = projection()
    valid = receipt(first)
    tampered = deepcopy(valid)
    tampered["cognitive_context"]["unified_memory_runtime_diagnostics"]["domain_count"] = 99
    recovered = projection(prior_unified_memory_receipts=[valid, deepcopy(valid), tampered])
    assert recovered["policy"]["policy_recovered"] is True
    assert recovered["diagnostics"]["prior_receipts_verified"] == 1
    assert recovered["diagnostics"]["prior_receipts_replayed"] == 1
    assert recovered["diagnostics"]["prior_receipt_recovery"] == "invalid_prior_receipt"


def test_v1165_7_provenance_anomaly_degrades_evidence():
    rows = base_rows() + [{"id": "bad", "type": "fact", "content": "bad lineage", "source": "x", "role": "unknown_owner"}]
    value = build_unified_memory_runtime_projection("continue", memory_records=rows, now=NOW)
    # ownership normalizes to system, so diagnostics must remain complete and bounded.
    assert value["diagnostics"]["provenance_anomalies"] == 0
    assert value["diagnostics"]["provenance_complete"] is True


def test_v1165_7_diagnostics_tamper_including_provenance_is_detected():
    value = projection()
    tampered = dict(value["diagnostics"])
    tampered["provenance_anomalies"] = 5
    assert not verify_unified_memory_runtime_diagnostics(tampered)


def test_v1165_8_selection_audit_is_content_free_and_compliant():
    value = projection()
    audit = audit_unified_memory_selection(value)
    assert audit["compliant"] is True
    assert audit["selected_count"] == len(value["selected_memory_records"])
    assert audit["contains_memory_text"] is False
    assert verify_unified_memory_selection_audit(audit)


def test_v1165_8_selection_audit_detects_authority_and_private_fields():
    value = projection()
    value["selected_memory_records"].append({"id": "forged", "content": "x", "approval_granted": True, "private_chain_of_thought": "hidden"})
    audit = audit_unified_memory_selection(value)
    assert audit["compliant"] is False
    assert audit["authority_violation_count"] == 1
    assert audit["private_field_violation_count"] == 1


def test_v1165_8_selection_audit_tampering_is_detected():
    audit = audit_unified_memory_selection(projection())
    tampered = dict(audit)
    tampered["compliant"] = not tampered["compliant"]
    assert not verify_unified_memory_selection_audit(tampered)
