from __future__ import annotations
import json,sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from memory_world_model_coherence import build_memory_world_model_projection
from conversation_runtime import _long_term_memories
from active_conversation_facts import _facts_from_durable_memories,_facts_from_text
from conversation_entity_associations import resolve_conversation_association_query
import memory_world_model_controls as mwmc
checks=[]
def req(v,n): checks.append(n); assert v,n
now=datetime.now(timezone.utc)
rows=[
 {'id':'old','type':'fact','fact_key':'pet:name','content':'Pet is Alpha','provenance_class':'user','created_at':(now-timedelta(days=60)).isoformat(),'entity_id':'pet:1','name':'Alpha'},
 {'id':'new','type':'correction','fact_key':'pet:name','content':'Pet is Beta','provenance_class':'user','operator_correction':True,'created_at':now.isoformat(),'entity_id':'pet:1','name':'Beta'},
 {'id':'version','type':'library_version','fact_key':'lib:version','content':'Library version 1','provenance_class':'user','version':'1','created_at':(now-timedelta(days=250)).isoformat()},
 {'id':'assistant','type':'fact','fact_key':'assistant:claim','content':'Assistant invented fact','provenance_class':'assistant','created_at':now.isoformat()},
]
out=build_memory_world_model_projection('what is the pet name and library version?',rows)
req(out['ok'],'integrated_ok')
req(any(r.get('id')=='new' for r in out['selected_memory_records']),'correction_reaches_runtime_selection')
req(not any(r.get('id')=='old' for r in out['selected_memory_records']),'old_corrected_fact_removed')
req(not any(r.get('id')=='assistant' for r in out['selected_memory_records']),'assistant_authored_history_removed')
req(out['evidence']['stale_knowledge_count']>=1,'stale_knowledge_visible')
req(out['evidence']['provider_contacted'] is False and out['evidence']['external_browsing_performed'] is False,'no_external_side_effect')
req(out['authority_boundary']['can_mutate_memory'] is False and out['authority_boundary']['can_execute'] is False,'authority_preserved')
req('stale_knowledge_must_not_be_presented_as_current_without_current_evidence' in out['prompt_section'],'prompt_policy_currentness')
runtime_history=_long_term_memories([
 {'id':'user','type':'conversation_user','historical_evidence_eligible':True,'provenance_integrity':{'provenance_class':'user'}},
 {'id':'assistant','type':'conversation_eidolon','historical_evidence_eligible':False,'provenance_integrity':{'provenance_class':'assistant'}},
 {'id':'reflection','type':'reflection','historical_evidence_eligible':False,'use_in_conversation':True,'provenance_integrity':{'provenance_class':'unknown'}},
])
req([row.get('id') for row in runtime_history]==['user'],'runtime_preserves_only_attributable_history')
req(_facts_from_text("What is my fiancee's name?",offset=0)==[],'partner_query_not_parsed_as_fact')
req(_facts_from_text("Who is my stepdaughter?",offset=0)==[],'stepdaughter_query_not_parsed_as_fact')
remembered=_facts_from_durable_memories([
 {'type':'conversation_user','content':"Please remember that my fiancee's name is Melissa.",'historical_evidence_eligible':True,'provenance_integrity':{'provenance_class':'user'}},
 {'type':'conversation_user','content':"Please remember that my stepdaughter's name is Jordyn.",'historical_evidence_eligible':True,'provenance_integrity':{'provenance_class':'user'}},
 {'type':'conversation_eidolon','content':"Please remember that my fiancee's name is Wrong.",'historical_evidence_eligible':True,'provenance_integrity':{'provenance_class':'assistant'}},
])
req(remembered['user.partner.name'].value=='Melissa' and remembered['user.stepdaughter.name'].value=='Jordyn','explicit_user_history_reaches_fact_resolver')
unknown_association=resolve_conversation_association_query('What provider does Project Neptune use?',[],[])
req(unknown_association.state=='association_uncertain' and unknown_association.evidence_count==0,'natural_unsupported_provider_query_fails_closed')
source=(ROOT/'conscious_agent/conversation_runtime.py').read_text(encoding='utf-8')
req(source.count('memory_world_model_projection["selected_memory_records"]')==2,'production_selection_both_paths')
req(source.count('memory_world_model_projection["prompt_section"]')==2,'production_policy_both_paths')
ordinary_source=(ROOT/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
req('process_memory_world_model_control' in ordinary_source,'operator_control_routed_through_existing_chat_boundary')
ctrl=mwmc.process_memory_world_model_control('inspect memory world model')
req(ctrl.get('active') is True and ctrl.get('raw_memory_exposed') is False,'operator_inspection_content_free')
req(ctrl.get('authority_granted') is False and ctrl.get('memory_mutated') is False,'operator_inspection_non_authorizing')
blocked=mwmc.process_memory_world_model_control('inspect memory world model and install it')
req(blocked.get('active') is True and blocked.get('status')=='read_only_scope_expansion_rejected','operator_compound_scope_rejected')
original_projection=mwmc._projection
try:
    fake_inspection={'inspection_digest':'a'*64,'refresh_candidates':[{'knowledge_digest':'b'*24,'freshness_class':'time_sensitive'}]}
    mwmc._projection=lambda:{'ok':True,'knowledge_freshness':fake_inspection}
    prepared=mwmc.process_memory_world_model_control('prepare knowledge refresh '+('b'*24)+' at '+('a'*64))
    req(prepared.get('status')=='knowledge_refresh_proposal_prepared' and prepared['proposal']['browse_authorized'] is False,'refresh_proposal_digest_bound_non_authorizing')
    stale=mwmc.process_memory_world_model_control('prepare knowledge refresh '+('b'*24)+' at '+('c'*64))
    req(stale.get('status')=='stale_knowledge_inspection_digest','refresh_proposal_stale_digest_rejected')
finally:
    mwmc._projection=original_projection
print(json.dumps({'suite':'v1899.9-era4-integrated-memory-world-model','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
