from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.background_cognition_policy_v2505 import build_background_cognition_policy,evaluate_background_cognition_admission
from conscious_agent.background_cognitive_runtime_v2505 import BackgroundCognitiveRuntime
checks=[]
def req(v,n):checks.append(n);assert v,n
policy=build_background_cognition_policy();req(policy['ok'],'policy_ok');req('CONTINUE_THOUGHT' in policy['safe_operations'],'continuation_safe');req(not policy['authority_boundary']['can_execute_tool'],'policy_no_tool')
req(not evaluate_background_cognition_admission(operation='REST')['admitted'],'rest_not_work');req(not evaluate_background_cognition_admission(operation='REFLECT',foreground_busy=True)['admitted'],'foreground_suppresses');req(not evaluate_background_cognition_admission(operation='REFLECT',resource_pressure='critical')['admitted'],'pressure_suppresses')
with tempfile.TemporaryDirectory(prefix='eidolon-v2505-0-2-') as td:
 rt=BackgroundCognitiveRuntime(Path(td))
 off=rt.tick('off-1');req(off['status']=='background_cognition_suppressed','disabled_suppresses')
 cfg=rt.configure('cfg',enabled=True,minimum_interval_seconds=5,max_cycles_per_hour=2);req(cfg['enabled'],'enabled')
 idle=rt.tick('idle-1');req(idle['status']=='background_cognition_suppressed','idle_rest_suppressed');req('deliberate_inactivity' in idle['record']['suppression_reasons'],'idle_reason')
 busy=rt.tick('busy-1',new_experience=True,subject_ref='experience-1',foreground_busy=True);req('foreground_busy' in busy['record']['suppression_reasons'],'busy_reason')
 opened=rt.tick('open-1',new_experience=True,subject_ref='experience-1');req(opened['status']=='background_cognitive_work_opened','work_opened');req(opened['record']['selected_operation']=='INTEGRATE_EXPERIENCE','experience_operation')
 ins=rt.inspection_summary();req(ins['open_cycle_count']==1,'one_open');req(not ins['provider_contacted'] and not ins['message_sent'],'no_external_io');req(not ins['authority_boundary']['can_apply_candidate'],'no_apply')
print(json.dumps({'ok':True,'contract':'v2505.0-v2505.2','passed':len(checks),'checks':checks},sort_keys=True))
