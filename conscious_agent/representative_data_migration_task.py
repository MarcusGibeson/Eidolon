from __future__ import annotations
"""v1395 representative transactional persisted-state migration task."""
import hashlib,json,re,sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any,Mapping
CONTRACT_VERSION='v1395.8'
DENIED={'eidolon_source_mutation_authorized':False,'release_authorized':False,'promotion_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _version(con:sqlite3.Connection)->int:
 row=con.execute("SELECT version FROM schema_meta LIMIT 1").fetchone();return int(row[0]) if row else 0
def _columns(con:sqlite3.Connection)->list[str]:return [str(r[1]) for r in con.execute('PRAGMA table_info(profiles)').fetchall()]
def _rows(con:sqlite3.Connection)->list[dict[str,Any]]:
 cols=_columns(con)
 if 'display_name' in cols:return [{'id':int(r[0]),'name':str(r[1]),'timezone':str(r[2])} for r in con.execute('SELECT id,display_name,timezone FROM profiles ORDER BY id')]
 if 'name' in cols:return [{'id':int(r[0]),'name':str(r[1])} for r in con.execute('SELECT id,name FROM profiles ORDER BY id')]
 return []
def _schema(con:sqlite3.Connection)->dict[str,Any]:return {'version':_version(con),'columns':_columns(con),'tables':sorted(str(r[0]) for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall())}
def _db_state(path:Path)->dict[str,Any]:
 with closing(sqlite3.connect(path)) as con:
  schema=_schema(con);rows=_rows(con);return {'schema':schema,'schema_digest':_d(schema),'rows':rows,'data_digest':_d(rows),'row_count':len(rows)}
def read_profiles_compatible(*,db_path:str|Path)->dict[str,Any]:
 path=Path(db_path).expanduser().resolve()
 try:
  st=_db_state(path);return {'ok':st['schema']['version'] in {1,2},'status':'profile_state_read','schema_version':st['schema']['version'],'profiles':st['rows'],'data_digest':st['data_digest'],'compatibility_reader':True,'action_executed':False,**DENIED}
 except Exception as e:return {'ok':False,'status':'profile_state_unreadable','reason_digest':_d(type(e).__name__),'action_executed':False,**DENIED}
def run_data_migration_task(*,db_path:str|Path,operator_authorized:bool,simulate_interrupt_at:str='')->dict[str,Any]:
 path=Path(db_path).expanduser().resolve();active=Path(__file__).resolve().parents[1]
 if not operator_authorized or not path.is_file() or path.is_symlink() or simulate_interrupt_at not in {'','after_copy'}:return {'ok':False,'status':'data_migration_not_authorized_or_invalid','action_executed':False,**DENIED}
 try:path.relative_to(active);return {'ok':False,'status':'data_migration_eidolon_source_blocked','action_executed':False,**DENIED}
 except ValueError:pass
 try:before=_db_state(path)
 except Exception as e:return {'ok':False,'status':'data_migration_state_invalid','reason_digest':_d(type(e).__name__),'action_executed':False,**DENIED}
 if before['schema']!={'version':1,'columns':['id','name'],'tables':['profiles','schema_meta']}:return {'ok':False,'status':'data_migration_v1_schema_required','action_executed':False,**DENIED}
 interrupted=False
 con=sqlite3.connect(path)
 try:
  con.execute('BEGIN IMMEDIATE')
  if _version(con)!=1:raise RuntimeError('stale migration version')
  con.execute('CREATE TABLE profiles_v2 (id INTEGER PRIMARY KEY, display_name TEXT NOT NULL, timezone TEXT NOT NULL DEFAULT "UTC")')
  con.execute('INSERT INTO profiles_v2(id,display_name,timezone) SELECT id,name,"UTC" FROM profiles')
  if simulate_interrupt_at=='after_copy':raise InterruptedError('simulated interruption')
  con.execute('DROP TABLE profiles');con.execute('ALTER TABLE profiles_v2 RENAME TO profiles');con.execute('UPDATE schema_meta SET version=2');con.commit()
 except InterruptedError:
  interrupted=True;con.rollback()
 except Exception as e:
  con.rollback();con.close();return {'ok':False,'status':'data_migration_failed_rolled_back','failure_digest':_d(type(e).__name__),'action_executed':True,**DENIED}
 finally:
  try:con.close()
  except Exception:pass
 after=_db_state(path)
 if interrupted:
  recovered=after==before
  return {'ok':False,'status':'data_migration_interrupted_safely' if recovered else 'data_migration_interrupted_state_uncertain','interrupted_recovery':{'transaction_rolled_back':recovered,'schema_version':after['schema']['version'],'partial_table_absent':'profiles_v2' not in after['schema']['tables'],'before_data_digest':before['data_digest'],'after_data_digest':after['data_digest'],'recovery_safe':recovered},'action_executed':True,**DENIED}
 compatibility=read_profiles_compatible(db_path=path);transformed=all(row.get('timezone')=='UTC' for row in after['rows']) and [x['name'] for x in after['rows']]==[x['name'] for x in before['rows']]
 core={'contract_version':CONTRACT_VERSION,'db_path_digest':_d(str(path)),'from_version':1,'to_version':2,'before_schema_digest':before['schema_digest'],'after_schema_digest':after['schema_digest'],'before_data_digest':before['data_digest'],'after_data_digest':after['data_digest'],'row_count':after['row_count'],'forward_migration_complete':after['schema']['version']==2 and transformed,'compatibility_check_passed':bool(compatibility.get('ok')),'interrupted_run_recovery_supported':True,'rollback_requires_unchanged_post_migration_state':True,'action_executed':True,**DENIED};core['migration_digest']=_d(core)
 return {'ok':core['forward_migration_complete'] and core['compatibility_check_passed'],'status':'data_migration_complete','data_migration':core,'action_executed':True,**DENIED}
def rollback_data_migration(*,db_path:str|Path,migration:Mapping[str,Any],expected_migration_digest:str,operator_authorized:bool)->dict[str,Any]:
 path=Path(db_path).expanduser().resolve();row=dict(migration or {});sup=str(row.pop('migration_digest',''))
 if not operator_authorized or sup!=expected_migration_digest or sup!=_d(row):return {'ok':False,'status':'data_migration_rollback_not_authorized_or_tampered','action_executed':False,**DENIED}
 try:current=_db_state(path)
 except Exception:return {'ok':False,'status':'data_migration_rollback_state_invalid','action_executed':False,**DENIED}
 if current['schema']['version']!=2 or current['data_digest']!=migration.get('after_data_digest') or current['schema_digest']!=migration.get('after_schema_digest'):
  return {'ok':False,'status':'data_migration_rollback_blocked_by_drift','action_executed':False,**DENIED}
 con=sqlite3.connect(path)
 try:
  con.execute('BEGIN IMMEDIATE');con.execute('CREATE TABLE profiles_v1 (id INTEGER PRIMARY KEY, name TEXT NOT NULL)');con.execute('INSERT INTO profiles_v1(id,name) SELECT id,display_name FROM profiles');con.execute('DROP TABLE profiles');con.execute('ALTER TABLE profiles_v1 RENAME TO profiles');con.execute('UPDATE schema_meta SET version=1');con.commit()
 except Exception as e:
  con.rollback();con.close();return {'ok':False,'status':'data_migration_rollback_failed','failure_digest':_d(type(e).__name__),'action_executed':True,**DENIED}
 finally:
  try:con.close()
  except Exception:pass
 final=_db_state(path);ok=final['schema']['version']==1 and final['data_digest']==migration.get('before_data_digest')
 core={'contract_version':CONTRACT_VERSION,'migration_digest':expected_migration_digest,'rollback_complete':ok,'restored_schema_version':final['schema']['version'],'restored_data_digest':final['data_digest'],'expected_data_digest':migration.get('before_data_digest'),'compatibility_check_passed':bool(read_profiles_compatible(db_path=path).get('ok')),'action_executed':True,**DENIED};core['rollback_digest']=_d(core)
 return {'ok':ok,'status':'data_migration_rollback_complete' if ok else 'data_migration_rollback_unverified','data_migration_rollback':core,'action_executed':True,**DENIED}
def process_data_migration_task_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show data migration task','inspect data migration task','show gamma migration'}:return {'active':False}
 rec=dict((project_state or {}).get('data_migration') or {});return {'active':True,'ok':bool(rec),'status':'data_migration_found' if rec else 'data_migration_missing','data_migration':rec,'action_executed':False,**DENIED}
