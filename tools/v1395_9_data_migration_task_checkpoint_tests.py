import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from representative_data_migration_task import *;from v1395_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 p=db(Path(td));i=run_data_migration_task(db_path=p,operator_authorized=True,simulate_interrupt_at='after_copy');req(i['interrupted_recovery']['transaction_rolled_back'],'interrupted recovery');N+=1
 q=run_data_migration_task(db_path=p,operator_authorized=True);x=q['data_migration'];req(q['ok'] and x['compatibility_check_passed'],'forward');N+=1
 req(x['interrupted_run_recovery_supported'],'recovery contract');N+=1
 rb=rollback_data_migration(db_path=p,migration=x,expected_migration_digest=x['migration_digest'],operator_authorized=True);req(rb['ok'] and rb['data_migration_rollback']['compatibility_check_passed'],'rollback');N+=1
 req(not x['release_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1395-checkpoint'})
