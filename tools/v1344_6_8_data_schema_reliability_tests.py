from __future__ import annotations
import shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1344_data_schema_test_support import *
from data_schema_implementation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);pa=patch(src,'config/settings.json','"retries":3,','');r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,patches=pa));req(not r['ok'] and r['data_schema_implementation']['failure_stage']=='breaking_schema_change' and manifest(src)==before,'removed_key_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patch(src,'config/settings.toml','port = 8000','port = "8000"');r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path='config/settings.toml',patches=pa));req(not r['ok'] and r['data_schema_implementation']['failure_stage']=='breaking_schema_change','type_change_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patch(src,'db/schema.sql','CREATE INDEX idx_users_name ON users(name);','');r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path='db/schema.sql',patches=pa));req(not r['ok'] and r['data_schema_implementation']['failure_stage']=='index_compatibility_regression','index_removal_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patch(src,'db/schema.sql','name TEXT NOT NULL','name INTEGER NOT NULL');r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path='db/schema.sql',patches=pa));req(not r['ok'] and r['data_schema_implementation']['failure_stage']=='breaking_schema_change','column_type_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path='db/migrations/001_notes.sql'));req(not r['ok'] and r['data_schema_implementation']['failure_stage']=='undeclared_migration_change','migration_declaration_required')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path='db/migrations/001_notes.sql',migration_change_declared=True));req(r['ok'] and r['data_schema_implementation']['migration_like'],'declared_migration_candidate')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));pa=patch(src,'db/schema.sql','CREATE TABLE users','ATTACH DATABASE \'/tmp/x.db\' AS x;\nCREATE TABLE users');r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path='db/schema.sql',patches=pa));req(not r['ok'] and r['data_schema_implementation']['failure_stage']=='unsafe_sql_schema_construct','filesystem_sql_blocked')
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));bad=[sys.executable,'-c','raise SystemExit(7)'];r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,test_argv=bad));req(not r['ok'] and r['data_schema_implementation']['failure_stage']=='data_schema_tests_failed' and r['data_schema_implementation']['workspace_cleaned'],'test_failure_cleans')
 req(not DATA_SCHEMA_DENIED_AUTHORITY['database_mutation_authorized'] and not DATA_SCHEMA_DENIED_AUTHORITY['migration_application_authorized'],'no_db_migration_authority')
 print({'ok':True,'suite':'v1344.6-8-data-schema-reliability','passed':p[0],'total':9})
if __name__=='__main__':main()
