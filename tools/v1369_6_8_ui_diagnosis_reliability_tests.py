from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1369_test_support import *
def main():
 p=0
 r=diagnose_ui({'browser_policy_blocked':True,'product_runtime_observed':False,'render_error':True});req(r['status']=='ui_environment_limited' and not r['ui_diagnosis']['failure_classes'],'policy');p+=1
 r=diagnose_ui({'product_runtime_observed':True});req(r['status']=='ui_evidence_healthy','healthy');p+=1
 req(not diagnose_ui(None)['ok'],'invalid');p+=1
 a=diagnose_ui(CASES['layout']);b=diagnose_ui(CASES['layout']);req(a['ui_diagnosis']['record_digest']==b['ui_diagnosis']['record_digest'],'deterministic');p+=1
 r=diagnose_ui({'product_runtime_observed':True,'late_result_after_cancel':True});req(r['ui_diagnosis']['primary_failure_class']=='request_lifecycle','late');p+=1
 r=diagnose_ui({'product_runtime_observed':True,'visual_check_passed':False});req(r['ui_diagnosis']['primary_failure_class']=='rendering','visual');p+=1
 req(all(v is False for k,v in r.items() if k.endswith('_authorized')),'denials');p+=1
 print({'ok':p==7,'passed':p,'total':7,'suite':'v1369-reliability'})
if __name__=='__main__':main()
