import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_bug_report_task import *;from v1393_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_bug_report_task(project_root=p,bug_report=REPORT,visual_evidence_digest=V,operator_authorized=True);x=q['bug_report_task'];req(q['ok'],'checkpoint');N+=1
 req(x['baseline_tests']['passed'],'baseline');N+=1
 req(x['post_repair_reproduction']['observed_output_digest']==x['post_repair_reproduction']['expected_output_digest'],'fixed repro');N+=1
 req(x['final_tests']['passed'],'suite');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1393-checkpoint'})
