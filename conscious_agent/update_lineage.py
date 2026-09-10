from __future__ import annotations
"""v1389 content-free self-update lineage ledger."""
import hashlib,json,os,re,tempfile
from pathlib import Path
from typing import Any,Mapping
CONTRACT_VERSION='v1389.8';DIGEST=re.compile(r'^[a-f0-9]{64}$');CID=re.compile(r'^selfc_[A-Za-z0-9_-]{3,64}$');OUTCOMES={'installed','rolled_back','rejected','canary_failed'}
DENIED={'source_mutation_authorized':False,'installation_authorized':False,'promotion_authorized':False,'release_authorized':False,'independent_authority_granted':False}
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _path(runtime:Path,cid:str)->Path:return runtime/'self_update_lineage'/f'{cid}.json'
def _read(p:Path)->dict[str,Any]:
 if not p.is_file():return {'schema':'eidolon.self-update-lineage.v1','records':[]}
 v=json.loads(p.read_text(encoding='utf-8'));return v if isinstance(v,dict) else {}
def _write(p:Path,v:Mapping[str,Any]):
 p.parent.mkdir(parents=True,exist_ok=True);data=(json.dumps(dict(v),indent=2,sort_keys=True)+'\n').encode();
 if len(data)>512*1024:raise ValueError('lineage ledger too large')
 tmp=None
 try:
  with tempfile.NamedTemporaryFile('wb',delete=False,dir=p.parent,suffix='.tmp') as h:h.write(data);h.flush();os.fsync(h.fileno());tmp=Path(h.name)
  os.replace(tmp,p);tmp=None
 finally:
  if tmp:tmp.unlink(missing_ok=True)
def record_update_lineage(*,runtime_root:str|Path,candidate_id:str,source_digest:str,finding_digest:str,repair_digest:str,test_digest:str,canary_digest:str,transaction_digest:str,active_version:str,outcome:str,rollback_ancestor_digest:str='')->dict[str,Any]:
 vals=[source_digest,finding_digest,repair_digest,test_digest,canary_digest,transaction_digest]
 if not CID.fullmatch(str(candidate_id or '')) or any(not DIGEST.fullmatch(str(x or '')) for x in vals) or (rollback_ancestor_digest and not DIGEST.fullmatch(rollback_ancestor_digest)) or outcome not in OUTCOMES or not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}',str(active_version or '')):
  return {'ok':False,'status':'update_lineage_request_invalid','action_executed':False,**DENIED}
 runtime=Path(runtime_root).expanduser().resolve();p=_path(runtime,candidate_id);ledger=_read(p);rows=list(ledger.get('records') or [])
 if len(rows)>=256:return {'ok':False,'status':'update_lineage_generation_limit','action_executed':False,**DENIED}
 previous=str(rows[-1].get('lineage_digest') or '') if rows else ''
 record={'contract_version':CONTRACT_VERSION,'candidate_id':candidate_id,'generation':len(rows)+1,'source_digest':source_digest,'finding_digest':finding_digest,'repair_digest':repair_digest,'test_digest':test_digest,'canary_digest':canary_digest,'transaction_digest':transaction_digest,'active_version':active_version,'outcome':outcome,'previous_lineage_digest':previous,'rollback_ancestor_digest':rollback_ancestor_digest,'content_free':True,'action_executed':False,**DENIED};record['lineage_digest']=_d(record)
 rows.append(record);new={'schema':'eidolon.self-update-lineage.v1','candidate_id':candidate_id,'records':rows};new['ledger_digest']=_d(new);_write(p,new)
 return {'ok':True,'status':'update_lineage_recorded','update_lineage':record,'ledger_digest':new['ledger_digest'],'action_executed':False,**DENIED}
def load_update_lineage(*,runtime_root:str|Path,candidate_id:str)->dict[str,Any]:
 if not CID.fullmatch(str(candidate_id or '')):return {'ok':False,'status':'update_lineage_candidate_invalid','action_executed':False,**DENIED}
 ledger=_read(_path(Path(runtime_root).expanduser().resolve(),candidate_id));rows=list(ledger.get('records') or []);prev='';valid=True
 for i,row in enumerate(rows,1):
  x=dict(row);sup=str(x.pop('lineage_digest',''));valid=valid and row.get('generation')==i and row.get('previous_lineage_digest')==prev and sup==_d(x);prev=sup
 core=dict(ledger);sup_ledger=str(core.pop('ledger_digest',''));valid=valid and (not rows or sup_ledger==_d(core))
 return {'ok':valid,'status':'update_lineage_verified' if valid else 'update_lineage_tampered','candidate_id':candidate_id,'record_count':len(rows),'records':rows if valid else [],'ledger_digest':sup_ledger if valid else '','content_free':True,'action_executed':False,**DENIED}
def process_update_lineage_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show update lineage','inspect update lineage','show self update lineage'}:return {'active':False}
 cid=str((project_state or {}).get('self_change_candidate_id') or '')
 if not runtime_root or not cid:return {'active':True,'ok':False,'status':'update_lineage_context_missing','action_executed':False,**DENIED}
 r=load_update_lineage(runtime_root=runtime_root,candidate_id=cid);r['active']=True;return r
