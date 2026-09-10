import tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_configuration import *
checks=[]
def req(x):
    if not x: raise AssertionError
    checks.append(True)
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    a=create_cognitive_control_configuration_preview({'domain':'attention','mode':'focused','intensity':.7},runtime_root=root,operator_id='operator-1',source_event_id='event-1')
    b=create_cognitive_control_configuration_preview({'domain':'attention','mode':'bounded','intensity':.4},runtime_root=root,operator_id='operator-1',source_event_id='event-2')
    i=build_cognitive_control_configuration_inspection(root)
    req(a['state']=='preview_only' and not a['applied']); req(b['prior_configuration_id']==a['configuration_id'])
    req(i['contract_version']=='v1146.1'); req(i['record_count']==2); req(i['preview_only']); req(not i['mutation_route_available']); req(not i['apply_authority_available'])
    req(all(v is False for v in i['authority_boundary'].values())); req(i['structural_digest'])
    try: create_cognitive_control_configuration_preview({'domain':'privacy','mode':'strict','text':'secret'},runtime_root=root)
    except ValueError: checks.append(True)
    else: raise AssertionError
print({'passed':len(checks),'total':10,'suite':'v1146.1'})
