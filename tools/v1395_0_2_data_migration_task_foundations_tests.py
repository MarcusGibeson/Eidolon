import sys,tempfile,sqlite3;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_data_migration_task import *;from v1395_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=db(Path(td));q=run_data_migration_task(db_path=p,operator_authorized=True);req(q['ok'],'migrate');N+=1
 x=q['data_migration'];req(x['from_version']==1 and x['to_version']==2,'versions');N+=1
 req(x['row_count']==2 and x['forward_migration_complete'],'rows');N+=1
 r=read_profiles_compatible(db_path=p);req(r['ok'] and all(v['timezone']=='UTC' for v in r['profiles']),'compat');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1395-foundations'})
