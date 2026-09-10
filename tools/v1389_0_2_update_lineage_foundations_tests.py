import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from update_lineage import *;from v1389_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 q=record_update_lineage(**args(td));req(q['ok'],'record');N+=1
 r=load_update_lineage(runtime_root=td,candidate_id=CID);req(r['ok'] and r['record_count']==1,'load');N+=1
 x=r['records'][0];req(x['source_digest']==D('source') and x['finding_digest']==D('finding'),'chain');N+=1
 req(x['content_free'],'privacy');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1389-foundations'})
