from conscious_agent.memory_retrieval_relevance import (
    MAX_CANDIDATES, MAX_MESSAGE_CHARS, MAX_REFERENCE_COLLECTION,
    audit_memory_retrieval_selection, build_memory_retrieval_relevance,
    verify_memory_retrieval_audit, verify_memory_retrieval_diagnostics,
)

def ref(age='recent', confidence='medium', relevance=0):
    return {'age_band': age, 'confidence_band': confidence, 'relevance_score': relevance}

def test_oversized_candidate_collection_fails_closed():
    rows=[{'content':f'dog project {i}'} for i in range(MAX_CANDIDATES+1)]
    p=build_memory_retrieval_relevance('dog project', rows, [ref()] * len(rows))
    assert p['policy']['policy_recovered'] is True
    assert p['selected_memory_records']==[]
    assert p['diagnostics']['oversized_collection'] is True

def test_malformed_reference_collection_fails_closed():
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],{'age_band':'recent'})
    assert p['selected_memory_records']==[]
    assert p['policy']['recovery_reason']=='invalid_reference_collection'

def test_oversized_reference_collection_fails_closed():
    refs=[ref()]*(MAX_REFERENCE_COLLECTION+1)
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],refs)
    assert p['diagnostics']['oversized_references'] is True
    assert p['selected_memory_records']==[]

def test_oversized_message_fails_closed_without_echo():
    message='dog '+('x'*MAX_MESSAGE_CHARS)
    p=build_memory_retrieval_relevance(message,[{'content':'dog'}],[ref()])
    assert p['policy']['recovery_reason']=='oversized_message'
    assert p['selected_memory_records']==[]
    assert 'dog' not in str(p['diagnostics'])

def test_audit_accepts_compliant_selection_and_is_content_free():
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    a=audit_memory_retrieval_selection(p)
    assert a['compliant'] is True
    assert verify_memory_retrieval_audit(a)
    assert 'dog' not in str(a)

def test_audit_detects_forged_authority_in_selected_record():
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    p['selected_memory_records'][0]['approval_granted']=True
    a=audit_memory_retrieval_selection(p)
    assert a['compliant'] is False
    assert a['authority_violation_count']==1

def test_audit_detects_private_field_and_decision_mismatch():
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    p['selected_memory_records'][0]['hidden_reasoning']='secret'
    p['decisions'][0]['selected']=False
    a=audit_memory_retrieval_selection(p)
    assert a['private_field_violation_count']==1
    assert a['decision_mismatch_count']==1

def test_audit_tampering_is_detected():
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    a=audit_memory_retrieval_selection(p)
    a['selected_count']=99
    assert verify_memory_retrieval_audit(a) is False

def test_reliability_diagnostics_are_digest_bound():
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    assert verify_memory_retrieval_diagnostics(p['diagnostics'])
    bad=dict(p['diagnostics']); bad['oversized_collection']=True
    assert verify_memory_retrieval_diagnostics(bad) is False
