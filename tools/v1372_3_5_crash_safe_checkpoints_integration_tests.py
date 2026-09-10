import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from crash_safe_campaign_checkpoints import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1372_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 p=build_step_checkpoint(campaign_id=C,campaign_record_digest=CR,step_id='s1',attempt_id='a1',state='prepared')['step_checkpoint'];persist_step_checkpoint(runtime_root=td,checkpoint=p);d=build_step_checkpoint(campaign_id=C,campaign_record_digest=CR,step_id='s1',attempt_id='a1',state='completed',operation_id='op1',result_digest=D('r1'),result_confirmed=True)['step_checkpoint'];req(persist_step_checkpoint(runtime_root=td,checkpoint=d)['ok'],'complete');P+=1
 rr=assess_campaign_recovery(runtime_root=td,campaign_id=C,campaign_record_digest=CR,ordered_step_ids=STEPS);req(rr['ok'] and rr['campaign_recovery']['completed_step_count']==1 and rr['campaign_recovery']['resume_step_digest']==D('s2'),'skip');P+=1;c=process_ordinary_chat_development_turn('show campaign recovery',project_state={'campaign_recovery':rr['campaign_recovery']});req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'] and not c['automatic_replay_authorized'],'readonly');P+=1;req(not rr['campaign_recovery']['duplicate_side_effect_replay'],'exactly once');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1372-integration'})
