import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from update_lineage import *;from v1389_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 a=record_update_lineage(**args(td));b=record_update_lineage(**args(td,'rolled_back',a['update_lineage']['lineage_digest']));r=load_update_lineage(runtime_root=td,candidate_id=CID);req(r['ok'],'checkpoint');N+=1
 req(r['record_count']==2,'generations');N+=1
 req(r['records'][1]['rollback_ancestor_digest']==r['records'][0]['lineage_digest'],'rollback ancestry');N+=1
 req(all(x['content_free'] for x in r['records']),'privacy');N+=1
 req(all(not x['release_authorized'] for x in r['records']),'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1389-checkpoint'})
