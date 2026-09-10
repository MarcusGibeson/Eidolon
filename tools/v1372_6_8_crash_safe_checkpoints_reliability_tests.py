import sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from crash_safe_campaign_checkpoints import *
from v1372_test_support import *
P=0;req(not build_step_checkpoint(campaign_id=C,campaign_record_digest='bad',step_id='s1',attempt_id='a1',state='prepared')['ok'],'lineage');P+=1;req(not build_step_checkpoint(campaign_id=C,campaign_record_digest=CR,step_id='s1',attempt_id='a1',state='completed')['ok'],'result');P+=1
with tempfile.TemporaryDirectory() as td:
 p=build_step_checkpoint(campaign_id=C,campaign_record_digest=CR,step_id='s1',attempt_id='a1',state='prepared')['step_checkpoint'];req(persist_step_checkpoint(runtime_root=td,checkpoint=p)['ok'],'p');P+=1;side=build_step_checkpoint(campaign_id=C,campaign_record_digest=CR,step_id='s1',attempt_id='a1',state='side_effect_recorded',operation_id='op1',result_digest=D('uncertain'),mutating_side_effect=True,result_confirmed=False)['step_checkpoint'];req(persist_step_checkpoint(runtime_root=td,checkpoint=side)['ok'],'side');P+=1;rr=assess_campaign_recovery(runtime_root=td,campaign_id=C,campaign_record_digest=CR,ordered_step_ids=STEPS);req(not rr['ok'] and rr['status']=='recovery_blocked_uncertain_side_effect' and rr['campaign_recovery']['decisions'][0]['decision']=='stop_no_replay','uncertain');P+=1;req(not rr['automatic_replay_authorized'],'no replay');P+=1;req(persist_step_checkpoint(runtime_root=td,checkpoint=side)['status']=='step_checkpoint_already_stored','duplicate');P+=1
print({'ok':P==7,'passed':P,'total':7,'suite':'v1372-reliability'})
