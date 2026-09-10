import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from fault_localization import *
from v1362_test_support import *
P=0;r=localize_fault(source_manifest_digest=S,reproduction_digest=R,candidates=C);v=r['fault_localization'];req(r['ok'],'checkpoint');P+=1;req(v['top_tie_count']==1,'rank');P+=1;req(v['source_manifest_digest']==S and v['reproduction_digest']==R,'lineage');P+=1;req(v['read_only'] and v['content_free'],'safe');P+=1;req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1362.9-fault-localization-checkpoint'})
