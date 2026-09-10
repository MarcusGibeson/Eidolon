import json,tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_configuration import create_cognitive_control_configuration_preview
from conscious_agent.understandable_cognitive_control_activation import *
checks=[]
def req(x):
 if not x: raise AssertionError
 checks.append(True)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime';p=create_cognitive_control_configuration_preview({'domain':'attention','mode':'focused','intensity':.6},runtime_root=r,operator_id='op',source_event_id='e1')
 bad=activate_cognitive_control_preview(runtime_root=r,preview_id=p['configuration_id'],preview_digest=p['structural_digest'],confirmation='wrong',operator_id='op',request_id='r0');req(not bad['ok'] and bad['receipt']['status']=='rejected')
 a=activate_cognitive_control_preview(runtime_root=r,preview_id=p['configuration_id'],preview_digest=p['structural_digest'],confirmation=CONFIRMATION_PHRASE,operator_id='op',request_id='r1');req(a['ok']);req(a['receipt']['configuration_changed']);req(not a['receipt']['cognition_mutated']);req(not a['receipt']['provider_contacted'])
 idem=activate_cognitive_control_preview(runtime_root=r,preview_id=p['configuration_id'],preview_digest=p['structural_digest'],confirmation=CONFIRMATION_PHRASE,operator_id='op',request_id='r1');req(idem['idempotent'])
 ins=build_cognitive_control_activation_inspection(r);req(ins['active_control_count']==1);req(ins['restart_continuity']);req(ins['active_controls']['attention']['preview_digest']==p['structural_digest'])
 rb=rollback_cognitive_control_activation(runtime_root=r,domain='attention',activation_id=a['receipt']['receipt_id'],confirmation=ROLLBACK_CONFIRMATION_PHRASE,operator_id='op',request_id='r2');req(rb['ok']);req(build_cognitive_control_activation_inspection(r)['active_control_count']==0)
print(json.dumps({'passed':len(checks),'total':11,'suite':'v1146.3'}))
