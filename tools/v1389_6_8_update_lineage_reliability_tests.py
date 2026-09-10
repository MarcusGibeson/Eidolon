import sys,tempfile,json;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from update_lineage import *;from v1389_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 req(not record_update_lineage(**{**args(td),'source_digest':'bad'})['ok'],'digest');N+=1
 req(not record_update_lineage(**{**args(td),'candidate_id':'bad'})['ok'],'candidate');N+=1
 req(not record_update_lineage(**{**args(td),'outcome':'unknown'})['ok'],'outcome');N+=1
 q=record_update_lineage(**args(td));req(q['ok'],'record');N+=1
 p=Path(td)/'self_update_lineage'/f'{CID}.json';v=json.loads(p.read_text());v['records'][0]['active_version']='9999.9';p.write_text(json.dumps(v));req(not load_update_lineage(runtime_root=td,candidate_id=CID)['ok'],'tamper record');N+=1
 req(not load_update_lineage(runtime_root=td,candidate_id='bad')['ok'],'bad load');N+=1
 req(not q['update_lineage']['installation_authorized'],'no install');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1389-reliability'})
