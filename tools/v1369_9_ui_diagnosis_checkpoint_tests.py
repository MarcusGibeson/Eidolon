from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1369_test_support import *
def main():
 p=0
 obs={'product_runtime_observed':True,'content_clipped':True,'focus_order_valid':False,'stale_state_rendered':True,'history_consistent':False,'unreconciled_request':True,'required_element_missing':True}
 r=diagnose_ui(obs);req(set(r['ui_diagnosis']['failure_classes'])==set(ORDER),'coverage');p+=1
 req(r['ui_diagnosis']['primary_failure_class']=='layout','priority');p+=1
 req(not r['action_executed'] and not r['source_mutation_authorized'],'boundary');p+=1
 req(r['ui_diagnosis']['content_free'] and r['ui_diagnosis']['read_only'],'readonly');p+=1
 req(len(r['ui_diagnosis']['record_digest'])==64,'digest');p+=1
 print({'ok':p==5,'passed':p,'total':5,'suite':'v1369-checkpoint'})
if __name__=='__main__':main()
