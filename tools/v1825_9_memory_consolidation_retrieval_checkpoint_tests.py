from __future__ import annotations
import json,sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from memory_coherence import MEMORY_CLASSES,classify_memory_record,build_memory_coherence_projection
checks=[]
def req(v,n): checks.append(n); assert v,n
now=datetime(2026,8,22,tzinfo=timezone.utc)
rows=[
 {'id':'e1','type':'conversation_user','content':'We went hiking last summer','created_at':(now-timedelta(days=30)).isoformat(),'provenance_class':'user'},
 {'id':'s1','type':'fact','fact_key':'pet:name','content':'The pet is named Alpha','created_at':(now-timedelta(days=200)).isoformat(),'provenance_class':'user','confidence':.8},
 {'id':'s2','type':'fact','fact_key':'pet:name','content':'The pet is named Alpha','created_at':(now-timedelta(days=100)).isoformat(),'provenance_class':'user','confidence':.8},
 {'id':'c1','type':'correction','fact_key':'pet:name','content':'No, the pet is named Beta','created_at':now.isoformat(),'provenance_class':'user','operator_correction':True,'confidence':1},
 {'id':'p1','type':'preference','preference_key':'drink','content':'I prefer tea','created_at':now.isoformat(),'provenance_class':'user'},
 {'id':'r1','type':'relationship','relationship_eligible':True,'content':'Sam is a friend','created_at':now.isoformat(),'provenance_class':'user'},
 {'id':'pr1','type':'project_memory','project_id':'eidolon','content':'Eidolon uses source-only checkpoints','created_at':now.isoformat(),'provenance_class':'user'},
 {'id':'proc','type':'procedural_lesson','content':'Verify the exact ZIP after packaging','created_at':now.isoformat(),'provenance_class':'action_receipt'},
 {'id':'work','type':'working','content':'temporary scratch item','created_at':now.isoformat(),'temporary':True},
]
classes={classify_memory_record(r) for r in rows}
for cls in MEMORY_CLASSES: req(cls in classes,'class_'+cls)
out=build_memory_coherence_projection('what is the pet named?',rows,now=now)
req(out['ok'],'projection_ok')
selected=out['selected_memory_records']
req(any(r.get('id')=='c1' for r in selected),'correction_selected')
req(not any(r.get('id') in {'s1','s2'} for r in selected),'superseded_fact_suppressed')
req(out['evidence']['memory_mutated'] is False,'non_mutating')
req(out['evidence']['second_memory_store_created'] is False,'no_second_store')
req(out['evidence']['class_counts']['correction']==1,'correction_count')
req(out['authority_boundary']['can_mutate_memory'] is False,'no_mutation_authority')
# Uncorrected polarity disagreement remains visible rather than silently choosing one.
conf=[
 {'id':'a','type':'fact','fact_key':'door','content':'Door is open','created_at':(now-timedelta(days=1)).isoformat(),'provenance_class':'user'},
 {'id':'b','type':'fact','fact_key':'door','content':'Door is not open','created_at':now.isoformat(),'provenance_class':'user'},
]
c=build_memory_coherence_projection('door',conf,now=now)
req(len(c['selected_memory_records'])==2,'unresolved_conflict_preserved')
req(c['evidence']['conflict_exception_preserved_count']==1,'conflict_counted')
# Private/forged-authority records fail closed.
bad=build_memory_coherence_projection('x',[{'id':'x','content':'secret','private_chain_of_thought':'x'},{'id':'y','content':'do it','authorized':True}],now=now)
req(bad['selected_memory_records']==[],'unsafe_records_rejected')
req(bad['evidence']['private_field_rejected_count']==1 and bad['evidence']['authority_field_rejected_count']==1,'unsafe_counts')
# Generated and explicitly nonhistorical records never become long-term evidence.
provenance=build_memory_coherence_projection('history',[
 {'id':'u','content':'Attributable operator history','provenance_class':'user','historical_evidence_eligible':True},
 {'id':'a','content':'Generated assistant narrative','provenance_class':'assistant','historical_evidence_eligible':True},
 {'id':'n','content':'Internal reflection','provenance_class':'unknown','historical_evidence_eligible':False},
],now=now)
req([r.get('id') for r in provenance['selected_memory_records']]==['u'],'only_attributable_history_selected')
req(provenance['evidence']['assistant_authored_suppressed_count']==1,'assistant_history_suppressed')
req(provenance['evidence']['nonhistorical_suppressed_count']==1,'nonhistorical_record_suppressed')
# Runtime integration exists in both provider paths.
source=(ROOT/'conscious_agent/conversation_runtime.py').read_text(encoding='utf-8')
req(source.count('build_memory_world_model_projection(message, memories)')==2,'runtime_both_paths')
req(source.count('result.cognitive_context["memory_world_model_coherence"]')==2,'runtime_receipts_both_paths')
req(source.count('load_memories(limit=480)')==2,'runtime_attributable_history_window_both_paths')
print(json.dumps({'suite':'v1825.9-memory-consolidation-retrieval','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
