import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_bug_report_task import *;from v1393_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);p=project(r);before=(p/'money.py').read_text();req(not run_bug_report_task(project_root=p,bug_report=REPORT,visual_evidence_digest='bad',operator_authorized=True)['ok'],'visual');N+=1
 req(not run_bug_report_task(project_root=p,bug_report=REPORT,visual_evidence_digest=V,operator_authorized=False)['ok'],'operator');N+=1
 req((p/'money.py').read_text()==before,'no early mutation');N+=1
 fixed=project(r/'fixed',False);req(not run_bug_report_task(project_root=fixed,bug_report=REPORT,visual_evidence_digest=V,operator_authorized=True)['ok'],'not reproduced');N+=1
 broken=project(r/'broken',True,True);req(not run_bug_report_task(project_root=broken,bug_report=REPORT,visual_evidence_digest=V,operator_authorized=True)['ok'],'baseline');N+=1
 req('abs(amount)' in (broken/'money.py').read_text(),'baseline untouched');N+=1
 q=run_bug_report_task(project_root=p,bug_report=REPORT,visual_evidence_digest=V,operator_authorized=True);req(q['ok'],'success');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1393-reliability'})
