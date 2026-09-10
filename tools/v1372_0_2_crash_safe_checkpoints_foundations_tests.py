import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from crash_safe_campaign_checkpoints import *
from v1372_test_support import *
P=0;r=build_step_checkpoint(campaign_id=C,campaign_record_digest=CR,step_id='s1',attempt_id='a1',state='prepared');req(r['ok'],'prepare');P+=1;v=r['step_checkpoint'];req(v['exactly_once_required'] and v['content_free'],'contract');P+=1;req(not v['automatic_replay_authorized'],'authority');P+=1
with tempfile.TemporaryDirectory() as td:req(persist_step_checkpoint(runtime_root=td,checkpoint=v)['ok'],'persist');P+=1;rr=assess_campaign_recovery(runtime_root=td,campaign_id=C,campaign_record_digest=CR,ordered_step_ids=STEPS);req(rr['ok'] and rr['campaign_recovery']['resume_step_digest']==D('s1'),'resume');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1372-foundations'})
