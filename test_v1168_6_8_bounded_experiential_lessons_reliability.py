from conscious_agent.bounded_experiential_lessons import (
    audit_bounded_experiential_lesson,
    build_bounded_experiential_lesson,
    build_lesson_review_boundary_handoff,
    validate_prior_lesson_receipts,
    verify_bounded_experiential_lesson_audit,
)
from conscious_agent.immediate_memory_learning import build_immediate_memory_learning

LC=("preserve_historical_truth","no_unconfirmed_memory_mutation","current_message_precedence")
BC=("no_uncontrolled_self_training","review_before_durable_lesson","preserve_historical_truth")

def projection():
    learning=build_immediate_memory_learning(
        "Correction: my preferred editor is Helix now",
        [{"preference_key":"preferred_editor","value":"Vim"}],
        protected_operator_constraints=LC,
    )
    return build_bounded_experiential_lesson(
        "Correction: my preferred editor is Helix now",
        learning,
        protected_operator_constraints=BC,
    )

def handoff(kind="corrective_lesson", source="explicit_user_change", target="resolved"):
    c=dict(projection()["candidate"])
    c["lesson_type"]=kind
    c["source_kind"]=source
    c["target_state"]=target
    return build_lesson_review_boundary_handoff(c,provider_completed=True,assistant_memory_committed=True)

def test_1168_6_mixed_target_resolution_receipts_fail_closed():
    r=validate_prior_lesson_receipts([handoff(target="resolved"),handoff(target="unresolved")])
    assert r["conflicting_receipts"] is True
    assert r["continuity_disposition"]=="literal_request_only_recovery"

def test_1168_6_same_type_conflicting_sources_fail_closed():
    r=validate_prior_lesson_receipts([handoff(source="explicit_user_change"),handoff(source="bounded_failure")])
    assert r["conflicting_receipts"] is True

def test_1168_6_tampered_receipt_checked_before_replay():
    good=handoff(); bad=dict(good); bad["source_kind"]="bounded_failure"
    r=validate_prior_lesson_receipts([good,bad])
    assert r["verified_receipt_count"]==1
    assert r["tampered_receipt_count"]==1
    assert r["replayed_receipt_count"]==0
    assert r["policy_recovered"] is True

def test_1168_6_oversized_receipt_payload_recovers():
    wrapped={"bounded_experiential_lesson_review_handoff":handoff(),"padding":"x"*25000}
    r=validate_prior_lesson_receipts([wrapped])
    assert r["oversized_receipt_bytes"] is True
    assert r["policy_recovered"] is True

def test_1168_7_compliant_projection_and_handoff_audit():
    p=projection(); h=build_lesson_review_boundary_handoff(p["candidate"],provider_completed=True,assistant_memory_committed=True)
    a=audit_bounded_experiential_lesson(p,h)
    assert a["compliant"] is True
    assert verify_bounded_experiential_lesson_audit(a)
    assert "helix" not in str(a).lower() and "vim" not in str(a).lower()

def test_1168_7_audit_detects_forged_authority():
    p=projection(); p=dict(p); p["policy"]=dict(p["policy"]); p["policy"]["training_permitted"]=True
    a=audit_bounded_experiential_lesson(p)
    assert a["authority_violation_count"]==1
    assert a["compliant"] is False

def test_1168_7_audit_detects_recovered_candidate_leak():
    p=projection(); p=dict(p); p["policy"]=dict(p["policy"]); p["policy"]["policy_recovered"]=True
    a=audit_bounded_experiential_lesson(p)
    assert a["recovered_candidate_violation"] is True

def test_1168_7_audit_detects_training_or_mutation_flags():
    p=projection(); p=dict(p); p["policy"]=dict(p["policy"]); p["policy"]["model_training_permitted"]=True
    a=audit_bounded_experiential_lesson(p)
    assert a["mutation_or_training_violation"] is True
    assert a["compliant"] is False

def test_1168_8_audit_tamper_detection():
    a=audit_bounded_experiential_lesson(projection())
    a=dict(a); a["compliant"]=not a["compliant"]
    assert verify_bounded_experiential_lesson_audit(a) is False

def test_1168_8_runtime_paths_share_lesson_audit():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("audit_bounded_experiential_lesson(")==2
    assert source.count('bounded_experiential_lesson_compliance_audit')==2
    assert source.count("build_lesson_review_boundary_handoff(")==2
