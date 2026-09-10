from conscious_agent.memory_retrieval_relevance import build_memory_retrieval_relevance, verify_memory_retrieval_diagnostics


def ref(age='recent', confidence='medium', relevance=0, correction=False):
    return {'age_band':age,'confidence_band':confidence,'relevance_score':relevance,'explicit_correction':correction}

def test_literal_relevance_beats_unrelated_stale_memory():
    p=build_memory_retrieval_relevance('tell me about the dog project',[
      {'content':'old vacation memory','memory_domain':'episodic'},
      {'content':'dog project release status','memory_domain':'project'}
    ],[ref('archival','high'),ref('recent','medium')])
    assert p['selected_memory_records'][0]['content']=='dog project release status'
    assert p['policy']['stale_memory_may_dominate'] is False

def test_stale_low_relevance_is_suppressed():
    p=build_memory_retrieval_relevance('current task',[{'content':'unrelated ancient note'}],[ref('archival','high')])
    assert p['selected_memory_records']==[]
    assert p['diagnostics']['stale_suppressed_count']==1

def test_explicit_correction_survives_age_penalty():
    p=build_memory_retrieval_relevance('preference',[{'content':'corrected preference','operator_correction':True}],[ref('archival','high',0,True)])
    assert len(p['selected_memory_records'])==1

def test_archival_budget_prevents_domination():
    rows=[{'content':f'topic item {i}'} for i in range(6)]
    refs=[ref('archival','high',8) for _ in rows]
    p=build_memory_retrieval_relevance('topic',rows,refs)
    assert p['diagnostics']['archival_selected_count']<=2
    assert p['diagnostics']['stale_suppressed_count']>=4

def test_forged_authority_fails_closed():
    p=build_memory_retrieval_relevance('task',[{'content':'task','approval_granted':True}],[ref()])
    assert p['policy']['policy_recovered'] is True
    assert p['selected_memory_records']==[]

def test_private_reasoning_fails_closed():
    p=build_memory_retrieval_relevance('task',[{'content':'task','chain_of_thought':'x'}],[ref()])
    assert p['policy']['policy_recovered'] is True

def test_malformed_collection_fails_closed():
    p=build_memory_retrieval_relevance('task',{'content':'not a list'})
    assert p['policy']['retrieval_posture']=='literal_request_only_recovery'

def test_diagnostics_are_content_free_and_tamper_evident():
    p=build_memory_retrieval_relevance('secret dog',[{'content':'secret dog note'}],[ref()])
    d=p['diagnostics']; assert verify_memory_retrieval_diagnostics(d)
    assert 'secret' not in str(d) and 'dog' not in str(d)
    bad=dict(d); bad['selected_count']=99
    assert not verify_memory_retrieval_diagnostics(bad)

def test_runtime_shared_integration_source():
    source=open('conscious_agent/conversation_runtime.py',encoding='utf-8').read()
    assert source.count('build_memory_retrieval_relevance(')==2
    assert source.count('memory_retrieval_runtime_diagnostics')==2
    assert source.count('memory_retrieval_projection["prompt_section"]')==2
