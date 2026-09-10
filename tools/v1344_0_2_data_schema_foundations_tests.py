from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1344_data_schema_test_support import *
from data_schema_implementation import *
import data_schema_implementation as d
def main():
 p=[0]
 def req(x,n):assert x,n;p[0]+=1
 with tempfile.TemporaryDirectory() as td:
  src,*_=source_fixture(Path(td));r=inspect_data_schema_project(src);req(r['json_file_count']==1 and r['yaml_file_count']==1 and r['toml_file_count']==1 and r['sql_file_count']==2,'formats');req(r['migration_file_count']==1 and r['sql_index_count']==1,'migration_index');req(r['invalid_or_unsupported_file_count']==0 and r['inspection_only'],'valid_inspection')
 req(all(not DATA_SCHEMA_DENIED_AUTHORITY[k] for k in ('database_mutation_authorized','migration_application_authorized','dependency_installation_authorized','network_authorized','release_authorized')),'denied_authority')
 try:d._safe_relative('../data.json');raise AssertionError('unsafe path allowed')
 except ValueError:req(True,'unsafe_path')
 print({'ok':True,'suite':'v1344.0-2-data-schema-foundations','passed':p[0],'total':5})
if __name__=='__main__':main()
