import sys,tempfile,sqlite3;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_data_migration_task import *;from v1395_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);p=db(r);req(not run_data_migration_task(db_path=p,operator_authorized=False)['ok'],'operator');N+=1
 i=run_data_migration_task(db_path=p,operator_authorized=True,simulate_interrupt_at='after_copy');req(not i['ok'] and i['interrupted_recovery']['recovery_safe'],'interrupt');N+=1
 req(read_profiles_compatible(db_path=p)['schema_version']==1,'still v1');N+=1
 q=run_data_migration_task(db_path=p,operator_authorized=True);x=q['data_migration'];req(q['ok'],'retry');N+=1
 con=sqlite3.connect(p);con.execute('UPDATE profiles SET display_name="Changed" WHERE id=1');con.commit();con.close();req(not rollback_data_migration(db_path=p,migration=x,expected_migration_digest=x['migration_digest'],operator_authorized=True)['ok'],'drift');N+=1
 t=dict(x);t['row_count']=9;req(not rollback_data_migration(db_path=p,migration=t,expected_migration_digest=x['migration_digest'],operator_authorized=True)['ok'],'tamper');N+=1
 missing=r/'missing.db';req(not run_data_migration_task(db_path=missing,operator_authorized=True)['ok'],'missing');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1395-reliability'})
