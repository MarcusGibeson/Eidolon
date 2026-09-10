from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.background_cognition_bridge_v2505 import validate_background_scheduler_ticket
from conscious_agent.background_structural_cognition_v2505 import derive_structural_background_outcome
from conscious_agent.unified_cognitive_state_frame import build_unified_cognitive_state_frame
checks=[]
def req(v,n):checks.append(n);assert v,n
base={'ticket_id':'bg_abc','status':'prepared_not_executed','work_kind':'memory_consolidation_review','evidence_digest':'a'*64,'execution_authorized':False}
v=validate_background_scheduler_ticket(base);req(v['ok'],'bridge_ok');req(v['new_experience'],'memory_maps_experience');req(not v['execution_authority_inferred'],'bridge_no_exec')
for kind in ['proposal_preparation','shell_execution']:
 try:validate_background_scheduler_ticket({**base,'work_kind':kind});raise AssertionError(kind)
 except ValueError:checks.append(kind+'_rejected')
try:validate_background_scheduler_ticket({**base,'execution_authorized':True});raise AssertionError('authority accepted')
except ValueError:checks.append('authority_ticket_rejected')
with tempfile.TemporaryDirectory(prefix='eidolon-v2505-7-8-') as td:
 frame=build_unified_cognitive_state_frame(Path(td),trigger_type='background_memory_review')
 mem=derive_structural_background_outcome('INTEGRATE_EXPERIENCE',frame);req(mem['outcome_type']=='MEMORY_INTEGRATION_CANDIDATE','memory_candidate');req(not mem['candidate_applied'],'candidate_only')
 reflect=derive_structural_background_outcome('REFLECT',frame);req(reflect['outcome_type']=='THOUGHT_CONTINUATION','reflect_continues');req(not reflect['provider_contacted'] and not reflect['raw_content_read'],'provider_raw_absent')
 recall=derive_structural_background_outcome('RECALL_MEMORY',frame);req(recall['outcome_type']=='NO_DURABLE_CHANGE','recall_no_fake_memory_mutation');req(not recall['tool_executed'] and not recall['source_mutated'],'no_action')
print(json.dumps({'ok':True,'contract':'v2505.7-v2505.8','passed':len(checks),'checks':checks},sort_keys=True))
