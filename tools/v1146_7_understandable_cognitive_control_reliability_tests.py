import json,tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_continuity import record_cognitive_control_continuity
from conscious_agent.understandable_cognitive_control_reliability import review_cognitive_control_reliability,build_cognitive_control_reliability_inspection
checks=[]
def req(x):
 if not x: raise AssertionError
 checks.append(True)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime';record_cognitive_control_continuity(runtime_root=r,cycle_id='c1',operator_correction_id='corr1');a=review_cognitive_control_reliability(runtime_root=r,review_id='r1');b=review_cognitive_control_reliability(runtime_root=r,review_id='r1');x=build_cognitive_control_reliability_inspection(r);row=a['review'];req(a['ok']);req(b['idempotent']);req(x['contract_version']=='v1146.7');req(x['review_count']==1);req(0<=row['reliability_score']<=1);req(0<=row['uncertainty']<=1);req(row['state'] in {'reliable','review_required'});req(row['correction_effective_count']==1);req(not row['execution_performed']);req(not row['proposal_created'])
print(json.dumps({'passed':len(checks),'total':10,'suite':'v1146.7'}))
