from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from ui_accessibility_verification import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1356_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 src,runtime,grant,wid,candidate,pre=fixture(Path(td));r=run_ui_accessibility_verification(wid,html_relative_path='ui.html',active_grant=grant,browser_precondition_record_id=pre,runtime_root=runtime,now_unix=101,interactions=INTER,checks=CHECK);req(r['ok'],'browser');P+=1
 v=r['ui_accessibility_verification'];req(v['real_browser_evidence'] and v['browser_checks_passed']==3,'real');P+=1
 req(v['screenshot_captured'],'screenshot');P+=1
 req(v['screen_reader_structure_evidence'] and not v['screen_reader_runtime_validated'],'screenreader truth');P+=1
 c=process_ordinary_chat_development_turn('show accessibility tests',project_state={'ui_accessibility_verification':v},runtime_root=runtime);req(c['active'] and c['ok'] and not c['action_executed'],'chat');P+=1
 req(not (src/'out.png').exists(),'source');P+=1
print({'ok':P==6,'passed':P,'total':6,'suite':'v1356.3-5-ui-accessibility-integration'})
