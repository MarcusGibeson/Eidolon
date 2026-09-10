from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.memory_consolidation_runtime_v2506 import prepare_memory_consolidation
from conscious_agent.memory_consolidation_candidates_v2506 import MemoryConsolidationCandidateStore
checks=[]
def req(v,n):checks.append(n);assert v,n
records=[
 {'id':'x1','type':'experience','content':'Test failed then was repaired','source':'user','confidence':.8},
 {'id':'x2','type':'experience','content':'Another repaired test','source':'user','confidence':.8},
 {'id':'lesson1','type':'lesson','content':'Run focused tests first','source':'development_outcome_lesson','confidence':.9},
 {'id':'self1','type':'reflection','content':'I should prefer bounded verification','source':'reflection','role':'assistant','confidence':.8},
]
with tempfile.TemporaryDirectory(prefix='eidolon-v2506-6-9-') as td:
 root=Path(td);r=prepare_memory_consolidation('consolidate-1',runtime_root=root,message='tests',memory_records=records,protected_operator_constraints=['preserve_historical_truth'])
 req(r['ok'],'prepared');req(r['candidate_count']>=2,'candidates');req('PROCEDURAL_LESSON_REVIEW' in r['candidate_types'],'procedure_candidate');req('AUTOBIOGRAPHICAL_CONTINUITY_REVIEW' in r['candidate_types'],'self_candidate');req(not r['candidate_applied'],'not_applied');req(not r['memory_mutated'] and not r['memory_deleted'] and not r['memory_retracted'],'no_memory_mutation');req(not r['provider_contacted'] and not r['model_trained'],'no_provider_training');req(r['historical_truth_preserved'],'history_preserved');req(not r['authority_broadened'],'no_authority')
 replay=prepare_memory_consolidation('consolidate-1',runtime_root=root,message='tests',memory_records=records,protected_operator_constraints=['preserve_historical_truth']);req(replay['record_id']==r['record_id'],'replay_same_record')
 ins=MemoryConsolidationCandidateStore(root).inspection_summary();req(ins['candidate_set_count']==1,'one_durable_candidate_set')
print(json.dumps({'ok':True,'checkpoint_version':'2506.9','contract':'Unified Memory Consolidation Foundations','passed':len(checks),'total':len(checks),'checks':checks},sort_keys=True))
