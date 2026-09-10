from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1369_test_support import *
def main():
 p=0
 obs={'product_runtime_observed':True,'overlap_detected':True,'focus_visible':False,'duplicate_state_owner':True,'route_resolved':False,'stuck_loading':True,'render_error':True}
 r=diagnose_ui(obs);req(r['ui_diagnosis']['failure_classes']==list(ORDER),'ordering');p+=1
 req(r['ui_diagnosis']['content_free'] and not r['ui_diagnosis']['screenshot_content_persisted'] and not r['ui_diagnosis']['dom_content_persisted'],'privacy');p+=1
 from conscious_agent.ordinary_chat_development_campaign import process_ordinary_chat_development_turn
 c=process_ordinary_chat_development_turn('show ui diagnosis',project_state={'ui_diagnosis':r['ui_diagnosis']});req(c['active'] and c['ok'] and not c['action_executed'],'chat');p+=1
 req(not r['ui_mutation_authorized'] and not r['browser_execution_authorized'],'authority');p+=1
 req(r['ui_diagnosis']['observation_digest'] and r['ui_diagnosis']['record_digest'],'digests');p+=1
 print({'ok':p==5,'passed':p,'total':5,'suite':'v1369-integration'})
if __name__=='__main__':main()
