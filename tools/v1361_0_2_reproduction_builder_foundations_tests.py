import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from reproduction_builder import *
from v1361_test_support import *
P=0;r=build_reproduction(source_manifest_digest=S,evidence_inputs=EVID,candidates=CANDS,environment_digest=ENV);req(r['ok'],'ok');P+=1;v=r['reproduction'];req(v['reproduction_found'] and v['step_count']==3,'minimal');P+=1;req(v['deterministic'] and v['minimal_among_supplied_candidates'],'deterministic');P+=1;req(not v['raw_report_persisted'] and not v['raw_screenshot_persisted'],'privacy');P+=1;req(not r['reproduction_execution_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1361.0-2-reproduction-builder-foundations'})
