from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from ui_accessibility_verification import *
from v1356_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 src,runtime,grant,wid,candidate,pre=fixture(Path(td));r=run_ui_accessibility_verification(wid,html_relative_path='ui.html',active_grant=grant,browser_precondition_record_id=pre,runtime_root=runtime,now_unix=101,interactions=INTER,checks=CHECK);v=r['ui_accessibility_verification'];req(r['ok'],'checkpoint');P+=1
 req(v['structural_passed'] and v['real_browser_evidence'],'evidence');P+=1
 req(v['browser_checks_failed']==0 and v['browser_checks_passed']==3,'checks');P+=1
 req(v['content_free'] and not v['screen_reader_runtime_validated'],'truth');P+=1
 req(not r['release_authorized'] and not r['network_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1356.9-ui-accessibility-checkpoint'})
