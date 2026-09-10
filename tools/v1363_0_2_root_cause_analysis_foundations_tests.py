import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from root_cause_analysis import *
from v1363_test_support import *
P=0;r=analyze_root_cause(source_manifest_digest=S,reproduction_digest=R,localization_digest=L,facts=FACTS);req(r['ok'],'ok');P+=1;v=r['root_cause_analysis'];req(v['root_defect_count']==1 and v['root_cause_resolved'],'root');P+=1;req(v['trigger_count']==1 and v['secondary_symptom_count']==1,'roles');P+=1;req(v['environmental_noise_count']==1,'noise');P+=1;req(not v['symptom_only_fix_recommended'],'repair');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1363.0-2-root-cause-foundations'})
