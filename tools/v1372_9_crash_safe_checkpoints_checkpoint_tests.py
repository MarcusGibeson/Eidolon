import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from crash_safe_campaign_checkpoints import *
from v1372_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 for sid,op in [('s1','op1'),('s2','op2')]:
  v=build_step_checkpoint(campaign_id=C,campaign_record_digest=CR,step_id=sid,attempt_id='a-'+sid,state='completed',operation_id=op,result_digest=D(op),result_confirmed=True)['step_checkpoint'];persist_step_checkpoint(runtime_root=td,checkpoint=v)
 rr=assess_campaign_recovery(runtime_root=td,campaign_id=C,campaign_record_digest=CR,ordered_step_ids=STEPS);req(rr['ok'],'ready');P+=1;req(rr['campaign_recovery']['completed_step_count']==2,'completed');P+=1;req(rr['campaign_recovery']['resume_step_digest']==D('s3'),'resume');P+=1;req(not rr['campaign_recovery']['duplicate_side_effect_replay'],'exactly once');P+=1;req(not rr['work_execution_authorized'] and not rr['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1372-checkpoint'})
