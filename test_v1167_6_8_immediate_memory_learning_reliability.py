from conscious_agent.immediate_memory_learning import (
    audit_immediate_memory_learning,
    build_immediate_memory_learning,
    build_learning_commit_boundary_handoff,
    validate_prior_learning_receipts,
    verify_immediate_memory_learning_audit,
)

C=("preserve_historical_truth","no_unconfirmed_memory_mutation","current_message_precedence")

def projection(message="From now on, I prefer concise replies."):
    return build_immediate_memory_learning(message,[{"preference_key":"reply_style"}],C)

def handoff(kind="preference_change", resolved=True):
    p=projection()
    c=dict(p["candidate"])
    c["candidate_type"]=kind
    c["target_key"]="reply_style" if resolved else "unresolved"
    return build_learning_commit_boundary_handoff(c,provider_completed=True,assistant_memory_committed=True)

def test_conflicting_verified_receipts_fail_closed():
    r=validate_prior_learning_receipts([handoff("preference_change"),handoff("retraction")])
    assert r["conflicting_receipts"] is True
    assert r["continuity_disposition"]=="literal_request_only_recovery"

def test_resolved_and_unresolved_receipts_conflict():
    r=validate_prior_learning_receipts([handoff(resolved=True),handoff(resolved=False)])
    assert r["conflicting_receipts"] is True

def test_tampered_receipt_is_counted_and_recovers():
    h=handoff(); h=dict(h); h["candidate_type"]="correction"
    r=validate_prior_learning_receipts([h])
    assert r["tampered_receipt_count"]==1
    assert r["continuity_disposition"]=="literal_request_only_recovery"

def test_oversized_receipt_bytes_recover():
    h=handoff(); wrapped={"immediate_memory_learning_commit_handoff":h,"padding":"x"*25000}
    r=validate_prior_learning_receipts([wrapped])
    assert r["oversized_receipt_bytes"] is True
    assert r["continuity_disposition"]=="literal_request_only_recovery"

def test_compliant_projection_and_handoff_audit():
    p=projection(); h=build_learning_commit_boundary_handoff(p["candidate"],provider_completed=True,assistant_memory_committed=True)
    a=audit_immediate_memory_learning(p,h)
    assert a["compliant"] is True
    assert verify_immediate_memory_learning_audit(a)
    assert "reply_style" not in str(a)

def test_audit_detects_forged_authority():
    p=projection(); p=dict(p); p["policy"]=dict(p["policy"]); p["policy"]["execute"]=True
    a=audit_immediate_memory_learning(p)
    assert a["authority_violation_count"]==1 and a["compliant"] is False

def test_audit_detects_recovered_candidate_leak():
    p=projection(); p=dict(p); p["policy"]=dict(p["policy"]); p["policy"]["policy_recovered"]=True
    a=audit_immediate_memory_learning(p)
    assert a["recovered_candidate_violation"] is True

def test_audit_tamper_detection():
    a=audit_immediate_memory_learning(projection())
    a=dict(a); a["compliant"]=not a["compliant"]
    assert verify_immediate_memory_learning_audit(a) is False

def test_runtime_paths_share_learning_handoff_and_diagnostics():
    source=open("conscious_agent/conversation_runtime.py",encoding="utf-8").read()
    assert source.count("build_learning_commit_boundary_handoff(")==2
    assert source.count('immediate_memory_learning_commit_handoff')==2
    assert source.count("prior_learning_receipts=session_history")==2
