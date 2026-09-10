import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from fault_localization import *
from v1362_test_support import *
P=0;r=localize_fault(source_manifest_digest=S,reproduction_digest=R,candidates=C);req(r['ok'],'ok');P+=1;v=r['fault_localization'];req(v['ranked_candidates'][0]['direct_failure_link'],'rank');P+=1;req(v['confidence']=='high','confidence');P+=1;req(not v['single_cause_asserted'] and not v['speculative_edit_performed'],'honesty');P+=1;req(not r['repair_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1362.0-2-fault-localization-foundations'})
