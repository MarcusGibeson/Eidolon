from __future__ import annotations
"""v1351 acceptance traceability: content-minimized requirement-to-evidence mapping."""
import hashlib, json, re
from pathlib import Path
from typing import Any, Mapping, Sequence
CONTRACT_VERSION='v1351.8'
DENIED={'source_mutation_authorized':False,'test_execution_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False}
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _root(r=None)->Path:
 p=Path(r or '.').resolve()/ 'phase6_acceptance_traceability';p.mkdir(parents=True,exist_ok=True);return p
def _safe_id(v:str)->bool:return bool(re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}',v))
def build_acceptance_traceability(*,source_manifest_digest:str,requirements:Sequence[Mapping[str,Any]],runtime_root=None)->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')):return {'ok':False,'status':'traceability_source_lineage_required','action_executed':False,**DENIED}
 if not requirements or len(requirements)>512:return {'ok':False,'status':'traceability_requirement_count_invalid','action_executed':False,**DENIED}
 rows=[];seen=set();invalid=False
 for raw in requirements:
  rid=str(raw.get('requirement_id') or '')
  if not _safe_id(rid) or rid in seen:invalid=True;continue
  seen.add(rid);impl=[str(x) for x in raw.get('implementation_evidence') or [] if re.fullmatch(r'[a-f0-9]{64}',str(x))];methods=[str(x) for x in raw.get('verification_methods') or [] if str(x).strip()]
  covered=bool(impl and methods)
  rows.append({'requirement_id_digest':_digest(rid),'non_goal':bool(raw.get('non_goal')),'implementation_evidence_digests':impl,'verification_method_digests':[_digest(x) for x in methods],'covered':covered})
 if invalid:return {'ok':False,'status':'traceability_requirement_identity_invalid','action_executed':False,**DENIED}
 missing=[r['requirement_id_digest'] for r in rows if not r['covered']];record={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'requirement_count':len(rows),'covered_count':len(rows)-len(missing),'uncovered_count':len(missing),'uncovered_requirement_digests':missing,'rows':rows,'traceability_complete':not missing,'content_free':True,'action_executed':False,**DENIED};record['record_digest']=_digest(record)
 tid='trace_'+record['record_digest'][:24];path=_root(runtime_root)/(tid+'.json');path.write_text(json.dumps(record,sort_keys=True),encoding='utf-8')
 return {'ok':not missing,'status':'acceptance_traceability_complete' if not missing else 'acceptance_traceability_incomplete','traceability_id':tid,'traceability':public_traceability(record),'action_executed':False,**DENIED}
def public_traceability(r:Mapping[str,Any])->dict[str,Any]:
 allowed=('contract_version','source_manifest_digest','requirement_count','covered_count','uncovered_count','uncovered_requirement_digests','rows','traceability_complete','content_free','record_digest','action_executed');return {k:r.get(k) for k in allowed}|DENIED
def load_acceptance_traceability(traceability_id:str,*,runtime_root=None)->dict[str,Any]:
 if not re.fullmatch(r'trace_[a-f0-9]{24}',str(traceability_id or '')):return {}
 p=_root(runtime_root)/(traceability_id+'.json')
 if not p.is_file():return {}
 try:r=json.loads(p.read_text(encoding='utf-8'))
 except Exception:return {}
 d=r.pop('record_digest',None)
 if d!=_digest(r):return {}
 r['record_digest']=d;return public_traceability(r)
def process_acceptance_traceability_control(text:str,*,project_state=None,runtime_root=None,**_):
 if str(text or '').strip().lower() not in {'show acceptance traceability','inspect acceptance traceability','show requirement traceability'}:return {'active':False}
 i=str((project_state or {}).get('acceptance_traceability_id') or '');r=load_acceptance_traceability(i,runtime_root=runtime_root) if i else {};return {'active':True,'ok':bool(r),'status':'acceptance_traceability_found' if r else 'acceptance_traceability_missing','traceability':r,'action_executed':False,**DENIED}
