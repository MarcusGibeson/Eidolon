import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from root_cause_analysis import *
from v1363_test_support import *
P=0;r=analyze_root_cause(source_manifest_digest=S,reproduction_digest=R,localization_digest=L,facts=FACTS);v=r['root_cause_analysis'];req(r['status']=='root_cause_resolved','checkpoint');P+=1;req(v['root_defect_count']==1 and not v['root_cause_ambiguous'],'root');P+=1;req(v['unresolved_count']==0,'resolved');P+=1;req(v['read_only'] and v['content_free'],'safe');P+=1;req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1363.9-root-cause-checkpoint'})
