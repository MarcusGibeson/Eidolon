from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1344_data_schema_test_support import *
from data_schema_implementation import *
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,pres,git=source_fixture(Path(td));before=manifest(src);r=run_data_schema_implementation(**args(src,runtime,grant,pres,git,relative_path='db/schema.sql'));row=r['data_schema_implementation'];req(r['ok'] and row['implementation_state']=='completed','campaign');req(row['test_process_id'] and row['test_reconciliation_id'] and row['git_commit_operation_id'],'evidence_chain');req(row['workspace_cleaned'] and row['host_recoverable'] and manifest(src)==before,'cleanup_source');req(not row['raw_schema_content_exposed'] and not row['schema_identifiers_exposed'] and not row['database_contacted'],'minimized')
 req(all(not DATA_SCHEMA_DENIED_AUTHORITY[k] for k in ('database_mutation_authorized','migration_application_authorized','source_application_authorized','release_authorized','independent_authority_granted')),'authority')
 print({'ok':True,'suite':'v1344.9-data-schema-checkpoint','passed':p[0],'total':5})
if __name__=='__main__':main()
