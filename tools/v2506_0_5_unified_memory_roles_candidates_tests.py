from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.unified_memory_context import build_unified_memory_runtime_projection
from conscious_agent.unified_memory_roles_v2506 import build_unified_memory_role_projection,verify_unified_memory_role_projection
from conscious_agent.memory_consolidation_candidates_v2506 import derive_memory_consolidation_candidates,MemoryConsolidationCandidateStore
checks=[]
def req(v,n):checks.append(n);assert v,n
records=[
 {'id':'e1','type':'experience','content':'Worked on verifier performance','source':'user','confidence':.8},
 {'id':'e2','type':'experience','content':'Another verifier session','source':'user','confidence':.8},
 {'id':'s1','type':'semantic_fact','content':'Verifier is expensive','source':'operator_input','fact_key':'verifier_cost','confidence':.9},
 {'id':'r1','type':'relationship_memory','content':'Marcus is operator','source':'operator_input','relationship_eligible':True,'confidence':.9},
 {'id':'p1','type':'lesson','content':'Use targeted tests before full verifier','source':'development_outcome_lesson','confidence':.8},
 {'id':'a1','type':'reflection','content':'I tend to over-check broad suites','source':'reflection','role':'assistant','confidence':.7},
]
projection=build_unified_memory_runtime_projection('verifier',memory_records=records,protected_operator_constraints=['preserve_historical_truth'])
roles=build_unified_memory_role_projection(projection);req(verify_unified_memory_role_projection(roles),'roles_valid');req(roles['reference_count']>=5,'references_present');req(roles['role_counts']['semantic']>=1,'semantic');req(roles['role_counts']['relational']>=1,'relational');req(roles['role_counts']['procedural']>=1,'procedural');req(roles['role_counts']['autobiographical']>=1,'autobiographical')
cs=derive_memory_consolidation_candidates(roles);types=set(x['candidate_type'] for x in cs['candidates']);req('SEMANTIC_STABILITY_REVIEW' in types,'semantic_review');req('RELATIONSHIP_STABILITY_REVIEW' in types,'relationship_review');req('PROCEDURAL_LESSON_REVIEW' in types,'procedure_review');req('AUTOBIOGRAPHICAL_CONTINUITY_REVIEW' in types,'autobiographical_review');req(not cs['candidate_applied'] and not cs['memory_mutated'],'no_apply')
with tempfile.TemporaryDirectory(prefix='eidolon-v2506-0-5-') as td:
 store=MemoryConsolidationCandidateStore(Path(td));a=store.record('event',cs);b=store.record('event',cs);req(a['ok'] and b['idempotent'],'store_idempotent');ins=store.inspection_summary();req(ins['candidate_set_count']==1,'one_set');req(not ins['authority_boundary']['can_write_memory'],'store_no_write')
print(json.dumps({'ok':True,'contract':'v2506.0-v2506.5','passed':len(checks),'checks':checks},sort_keys=True))
