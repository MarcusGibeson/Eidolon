from __future__ import annotations
import sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.unified_cognitive_runtime_v2504 import UnifiedCognitiveRuntime
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v2504-6-8-') as td:
 root=Path(td);rt=UnifiedCognitiveRuntime(root)
 a=rt.begin_cycle('begin-1',trigger_type='cadence');req(a['ok'],'begin_ok');req(a['selected_operation']=='REST','idle_rest');req(not a['requires_completion'],'rest_no_completion');req(a['deliberate_inactivity'],'rest_deliberate')
 dup=rt.begin_cycle('begin-1',trigger_type='cadence');req(dup['idempotent'],'begin_idempotent')
 b=rt.begin_cycle('begin-2',trigger_type='completed_work',subject_ref='experience-1',new_experience=True);req(b['selected_operation']=='INTEGRATE_EXPERIENCE','experience_selected');req(b['requires_completion'] and b['work_ticket_id'],'work_ticket')
 s=rt.inspection_summary();req(s['open_cycle_count']==1,'one_open_cycle');req(s['thought_continuity']['active_count']==1,'thought_persisted')
 try:rt.complete_cycle('bad-ticket',cycle_id=b['cycle_id'],work_ticket_id='wrong',outcome_type='MEMORY_INTEGRATION_CANDIDATE');raise AssertionError('ticket mismatch accepted')
 except ValueError:checks.append('ticket_binding')
 c=rt.complete_cycle('complete-2',cycle_id=b['cycle_id'],work_ticket_id=b['work_ticket_id'],outcome_type='MEMORY_INTEGRATION_CANDIDATE',evidence_digests=['a'*64],changed_fields=['episodic_summary'],confidence=.8);req(c['ok'],'complete_ok');req(c['candidate_target']=='memory','memory_candidate');req(not c['candidate_applied'],'candidate_not_applied');req(c['thought_status']=='completed','thought_closed')
 cdup=rt.complete_cycle('complete-2',cycle_id=b['cycle_id'],work_ticket_id=b['work_ticket_id'],outcome_type='MEMORY_INTEGRATION_CANDIDATE');req(cdup['idempotent'],'complete_idempotent')
 s2=rt.inspection_summary();req(s2['open_cycle_count']==0,'no_open_after_complete');req(s2['thought_continuity']['active_count']==0,'thought_no_longer_active');req(s2['outcomes']['outcome_count']==1,'outcome_integrated');req(s2['receipts']['receipt_count']==2,'rest_and_completion_receipts')
 d=rt.begin_cycle('begin-3',trigger_type='manual_review',subject_ref='subject-cont',new_experience=True);cont=rt.complete_cycle('complete-3',cycle_id=d['cycle_id'],work_ticket_id=d['work_ticket_id'],outcome_type='THOUGHT_CONTINUATION');req(cont['thought_status']=='unfinished','continuation_remains_open_thought')
 e=rt.begin_cycle('begin-4',trigger_type='cadence');req(e['selected_operation']=='CONTINUE_THOUGHT','later_cycle_resumes_thought');req(e['subject_ref']=='subject-cont','subject_continuity')
 final=rt.inspection_summary();req(not final['authority_boundary']['can_execute_action'],'runtime_no_execution');req(not final['provider_contacted'] and not final['message_sent'],'runtime_no_external_io');req(not final['hidden_reasoning_exposed'],'runtime_no_cot')
print(json.dumps({'ok':True,'contract':'v2504.6-v2504.8','passed':len(checks),'checks':checks},sort_keys=True))
