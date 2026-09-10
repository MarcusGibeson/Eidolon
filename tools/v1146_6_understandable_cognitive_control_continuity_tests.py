import json,tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_configuration import create_cognitive_control_configuration_preview
from conscious_agent.understandable_cognitive_control_activation import activate_cognitive_control_preview,CONFIRMATION_PHRASE
from conscious_agent.understandable_cognitive_control_continuity import record_cognitive_control_continuity,build_cognitive_control_continuity_inspection
checks=[]
def req(x):
 if not x: raise AssertionError
 checks.append(True)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime';p=create_cognitive_control_configuration_preview({'domain':'attention','mode':'focused','intensity':.5},runtime_root=r)
 activate_cognitive_control_preview(runtime_root=r,preview_id=p['configuration_id'],preview_digest=p['structural_digest'],confirmation=CONFIRMATION_PHRASE,operator_id='op',request_id='a1')
 a=record_cognitive_control_continuity(runtime_root=r,cycle_id='c1');b=record_cognitive_control_continuity(runtime_root=r,cycle_id='c2',prior_cycle_id='c1',operator_correction_id='corr1');dup=record_cognitive_control_continuity(runtime_root=r,cycle_id='c2')
 x=build_cognitive_control_continuity_inspection(r);req(a['ok']);req(b['record']['prior_cycle_id']=='c1');req(b['record']['correction_present']);req(dup['idempotent']);req(x['contract_version']=='v1146.6');req(x['record_count']==2);req(x['content_free']);req(not b['record']['execution_performed']);req(not b['record']['message_sent']);req(set(b['record']['safe_default_domains']))
print(json.dumps({'passed':len(checks),'total':10,'suite':'v1146.6'}))
