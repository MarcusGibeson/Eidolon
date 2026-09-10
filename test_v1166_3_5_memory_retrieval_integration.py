from datetime import datetime, timezone, timedelta
from conscious_agent.memory_retrieval_relevance import build_memory_retrieval_relevance, verify_memory_retrieval_diagnostics

def ref(age='recent', confidence='medium', relevance=0, correction=False):
    return {'age_band':age,'confidence_band':confidence,'relevance_score':relevance,'explicit_correction':correction}

def receipt(result, when=None):
    return {'created_at':(when or datetime.now(timezone.utc)).isoformat(),'cognitive_context':{'memory_retrieval_runtime_diagnostics':result['diagnostics']}}

def test_direct_literal_match_outranks_ambient_high_confidence():
    p=build_memory_retrieval_relevance('dog project status',[{'content':'general profile fact'},{'content':'dog project status'}],[ref('current','high',8),ref('recent','low',0)])
    assert p['selected_memory_records'][0]['content']=='dog project status'

def test_newer_same_fact_suppresses_stale_conflict():
    p=build_memory_retrieval_relevance('favorite color',[{'content':'blue','fact_key':'favorite_color'},{'content':'green','fact_key':'favorite_color'}],[ref('archival','high',8),ref('recent','medium',8)])
    assert [r['content'] for r in p['selected_memory_records']]==['green']
    assert p['diagnostics']['stale_conflict_suppressed_count']==1

def test_explicit_correction_survives_same_fact_age_conflict():
    p=build_memory_retrieval_relevance('favorite color',[{'content':'blue','fact_key':'favorite_color','operator_correction':True},{'content':'green','fact_key':'favorite_color'}],[ref('archival','high',8,True),ref('recent','medium',8)])
    assert any(r['content']=='blue' for r in p['selected_memory_records'])

def test_verified_prior_receipt_resumes_bounded_context():
    base=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()],prior_retrieval_receipts=[receipt(base)])
    assert p['policy']['continuity_disposition']=='resume_verified_retrieval_context'
    assert p['diagnostics']['prior_receipts_verified']==1

def test_stale_prior_receipt_is_ignored():
    base=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    old=datetime.now(timezone.utc)-timedelta(days=9)
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()],prior_retrieval_receipts=[receipt(base,old)])
    assert p['diagnostics']['prior_receipts_stale']==1
    assert p['policy']['continuity_disposition']=='use_current_retrieval'

def test_tampered_prior_receipt_fails_closed():
    base=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    bad=dict(base['diagnostics']); bad['selected_count']=99
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()],prior_retrieval_receipts=[{'cognitive_context':{'memory_retrieval_runtime_diagnostics':bad}}])
    assert p['policy']['policy_recovered'] is True
    assert p['selected_memory_records']==[]

def test_replayed_receipt_does_not_amplify_continuity():
    base=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()])
    r=receipt(base)
    p=build_memory_retrieval_relevance('dog project',[{'content':'dog project'}],[ref()],prior_retrieval_receipts=[r,r])
    assert p['diagnostics']['prior_receipts_verified']==1
    assert p['diagnostics']['prior_receipts_replayed']==1

def test_diagnostics_remain_content_free_and_valid():
    p=build_memory_retrieval_relevance('secret dog project',[{'content':'secret dog project'}],[ref()])
    assert verify_memory_retrieval_diagnostics(p['diagnostics'])
    assert 'secret' not in str(p['diagnostics']) and 'dog' not in str(p['diagnostics'])

def test_shared_runtime_receipt_integration_source():
    source=open('conscious_agent/conversation_runtime.py',encoding='utf-8').read()
    assert source.count('prior_retrieval_receipts=session_history')==2
    assert source.count('memory_retrieval_projection["prompt_section"]')==2
