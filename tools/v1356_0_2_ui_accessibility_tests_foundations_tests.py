from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from ui_accessibility_verification import analyze_accessibility_structure
from v1356_test_support import HTML,req
P=0
r=analyze_accessibility_structure(HTML);req(r['ok'],'structure');P+=1
req(r['checks']['controls_labeled'] and r['checks']['landmark_present'],'semantics');P+=1
req(r['checks']['focus_visible_signal'] and r['checks']['reduced_motion_signal'],'motion focus');P+=1
req(r['checks']['viewport_declared'] and r['checks']['narrow_layout_signal'],'responsive');P+=1
req(r['structural_evidence_only'] and not r['screen_reader_runtime_validated'],'truthful');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1356.0-2-ui-accessibility-foundations'})
