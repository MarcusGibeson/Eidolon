from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from ui_accessibility_verification import *
from v1356_test_support import *
P=0
for bad,key in [
 (HTML.replace(' lang="en"',''),'document_language_present'),
 (HTML.replace('<meta name="viewport" content="width=device-width,initial-scale=1">',''),'viewport_declared'),
 (HTML.replace('<label for="ime">Text</label>',''),'controls_labeled'),
 (HTML.replace(':focus-visible{outline:2px solid currentColor}',''),'focus_visible_signal'),
 (HTML.replace('@media (prefers-reduced-motion: reduce){*{transition:none!important}}',''),'reduced_motion_signal')]:
 r=analyze_accessibility_structure(bad);req(not r['checks'][key],key);P+=1
with tempfile.TemporaryDirectory() as td:
 src,runtime,grant,wid,candidate,pre=fixture(Path(td));(candidate/'ui.html').write_text(HTML.replace('<label for="ime">Text</label>',''),encoding='utf-8');r=run_ui_accessibility_verification(wid,html_relative_path='ui.html',active_grant=grant,browser_precondition_record_id=pre,runtime_root=runtime,now_unix=101);req(not r['ok'] and not r['browser_validation_performed'],'static blocks browser');P+=1
with tempfile.TemporaryDirectory() as td:
 src,runtime,grant,wid,candidate,pre=fixture(Path(td));r=run_ui_accessibility_verification(wid,html_relative_path='../secret.html',active_grant=grant,browser_precondition_record_id=pre,runtime_root=runtime,now_unix=101);req(not r['ok'],'path');P+=1
req(not r.get('release_authorized',False) and not r.get('source_mutation_authorized',False),'authority');P+=1
print({'ok':P==8,'passed':P,'total':8,'suite':'v1356.6-8-ui-accessibility-reliability'})
