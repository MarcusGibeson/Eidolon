import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_bug_report_task import *;from v1393_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=project(Path(td));q=run_bug_report_task(project_root=p,bug_report=REPORT,visual_evidence_digest=V,operator_authorized=True);req(q['ok'],'repair');N+=1
 x=q['bug_report_task'];req(x['defect_reproduced_before_repair'],'repro');N+=1
 req(x['repair_verified'] and x['final_tests']['passed'],'verify');N+=1
 req(x['natural_language_grounded'] and x['visual_evidence_bound'],'evidence');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1393-foundations'})
