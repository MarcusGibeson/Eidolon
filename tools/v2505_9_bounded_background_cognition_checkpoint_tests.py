from __future__ import annotations
import json,sys,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.background_cognitive_runtime_v2505 import BackgroundCognitiveRuntime
from conscious_agent.background_cognition_bridge_v2505 import validate_background_scheduler_ticket
from conscious_agent.background_cognition_policy_v2505 import build_background_cognition_policy
from conscious_agent.cognitive_thought_continuity import CognitiveThoughtContinuityStore
checks=[]
def req(v,n):checks.append(n);assert v,n
class Clock:
 def __init__(self):self.t=datetime(2026,9,2,15,0,tzinfo=timezone.utc)
 def __call__(self):return self.t.isoformat().replace('+00:00','Z')
 def add(self,s):self.t+=timedelta(seconds=s)
with tempfile.TemporaryDirectory(prefix='eidolon-v2505-9-') as td:
 root=Path(td);clock=Clock();rt=BackgroundCognitiveRuntime(root,clock=clock);rt.configure('cfg',enabled=True,minimum_interval_seconds=5,max_cycles_per_hour=4)
 # One message-independent experience can be structurally integrated end-to-end.
 first=rt.run_structural_tick('experience',trigger_type='background_memory_review',subject_ref='private raw experience',new_experience=True)
 req(first['status']=='background_structural_cognition_completed','structural_completed');req(first['selected_operation']=='INTEGRATE_EXPERIENCE','experience_selected');req(first['outcome_type']=='MEMORY_INTEGRATION_CANDIDATE','memory_candidate');req(not first['candidate_applied'],'not_applied')
 clock.add(6)
 # Explicit unfinished continuity is resumed later without a user message.
 manual=rt.tick('manual-thought',trigger_type='background_cadence',subject_ref='continuing-subject',new_experience=True)
 rt.complete('manual-cont',background_cycle_id=manual['record']['background_cycle_id'],outcome_type='THOUGHT_CONTINUATION')
 clock.add(6);resumed=rt.run_structural_tick('resume',trigger_type='background_cadence')
 req(resumed['selected_operation']=='CONTINUE_THOUGHT','continuation_selected');req(resumed['outcome_type']=='THOUGHT_CONTINUATION','continuation_preserved')
 req(CognitiveThoughtContinuityStore(root).inspection_summary()['active_count']>=1,'thought_remains_bounded')
 # Background suppression remains first-class.
 clock.add(6);quiet=rt.run_structural_tick('quiet',new_experience=True,quiet_hours=True);req(quiet['status']=='background_cognition_suppressed','quiet_suppresses');req(not quiet['structural_completion_attempted'],'suppressed_not_completed')
 # Scheduler bridge is evidence-only and grants nothing.
 ticket={'ticket_id':'bg_1','status':'prepared_not_executed','work_kind':'plan_review','evidence_digest':'b'*64,'execution_authorized':False}
 bridge=validate_background_scheduler_ticket(ticket);req(bridge['trigger_type']=='background_plan_review','plan_bridge');req(not bridge['execution_authority_inferred'],'bridge_no_authority')
 inspection=rt.inspection_summary();req(inspection['open_cycle_count']==0,'no_open_cycles');req(not inspection['provider_contacted'] and not inspection['message_sent'],'no_provider_message');req(not inspection['tool_executed'] and not inspection['source_mutated'],'no_tool_source');req(not inspection['hidden_reasoning_exposed'],'no_hidden_reasoning');req(not build_background_cognition_policy()['authority_boundary']['can_apply_candidate'],'policy_no_apply')
 print(json.dumps({'ok':True,'checkpoint_version':'2505.9','contract':'Bounded Background Cognition Runtime Foundations','passed':len(checks),'total':len(checks),'checks':checks},sort_keys=True))
