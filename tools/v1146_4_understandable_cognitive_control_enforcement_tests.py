import json,tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_configuration import create_cognitive_control_configuration_preview
from conscious_agent.understandable_cognitive_control_activation import activate_cognitive_control_preview,CONFIRMATION_PHRASE
from conscious_agent.understandable_cognitive_control_enforcement import *
checks=[]
def req(x):
 if not x: raise AssertionError
 checks.append(True)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime'
 x=evaluate_cognitive_control(runtime_root=r,domain='development_proposals',event_id='e0',consumer_id='dev',requested_intensity=.2);req(x['receipt']['decision']=='deny');req(x['receipt']['control_source']=='safe_default')
 p=create_cognitive_control_configuration_preview({'domain':'resource_use','mode':'minimal','intensity':.2},runtime_root=r)
 activate_cognitive_control_preview(runtime_root=r,preview_id=p['configuration_id'],preview_digest=p['structural_digest'],confirmation=CONFIRMATION_PHRASE,operator_id='op',request_id='a1')
 y=evaluate_cognitive_control(runtime_root=r,domain='resource_use',event_id='e1',consumer_id='worker',requested_intensity=.1,resource_cost=.8);req(y['receipt']['decision']=='deny');req(not y['receipt']['execution_performed']);req(not y['receipt']['cognition_mutated']);req(y['receipt']['activation_id'])
 z=evaluate_cognitive_control(runtime_root=r,domain='resource_use',event_id='e2',consumer_id='worker',requested_intensity=.8,resource_cost=.1);req(z['receipt']['decision']=='constrain');req(z['receipt']['effective_intensity']==.2)
 idem=evaluate_cognitive_control(runtime_root=r,domain='resource_use',event_id='e2',consumer_id='worker',requested_intensity=.8);req(idem['idempotent'])
 ins=build_cognitive_control_enforcement_inspection(r);req(ins['receipt_count']==3);req(ins['content_free'])
print(json.dumps({'passed':len(checks),'total':11,'suite':'v1146.4'}))
