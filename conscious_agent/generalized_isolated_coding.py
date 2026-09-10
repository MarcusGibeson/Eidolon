from __future__ import annotations

"""v1494 generalized structured coding inside an already-authorized isolated workspace.

This module applies a bounded, reviewable edit contract across common text files.
It never edits the authoritative source, contacts a provider, installs, promotes,
or derives authority from plan text.
"""

import hashlib, json, os
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from development_authority import private_scope_digest, validate_operator_authorization

CONTRACT_VERSION='v1494.9'
ALLOWED_SUFFIXES={'.py','.js','.css','.html','.json','.md','.txt','.toml','.cfg','.ini'}
DENIED_PARTS={'data','.git','.venv','venv','__pycache__','secrets','private','runtime'}
MAX_FILES=8;MAX_EDITS=24;MAX_CHANGED_BYTES=2*1024*1024


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _file_digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ''
def _safe_rel(value:str)->str:
 raw=str(value or '').replace('\\','/').strip();p=PurePosixPath(raw)
 if not raw or p.is_absolute() or '..' in p.parts or any(part.casefold() in DENIED_PARTS for part in p.parts) or p.suffix.casefold() not in ALLOWED_SUFFIXES:raise ValueError('coding_path_rejected')
 return p.as_posix()

def validate_edit_contract(plan:Mapping[str,Any],edits:Iterable[Mapping[str,Any]])->dict[str,Any]:
 allowed={_safe_rel(str(plan.get('source_module') or '')),_safe_rel(str(plan.get('destination_module') or ''))}
 rows=[dict(x or {}) for x in edits]
 errors=[]
 if not bool(plan.get('operator_selected')) or not plan.get('plan_digest'):errors.append('authorized_plan_required')
 if len(rows)>MAX_FILES:errors.append('too_many_files')
 normalized=[]
 for row in rows:
  try:rel=_safe_rel(str(row.get('path') or ''))
  except ValueError:errors.append('path_rejected');continue
  if rel not in allowed:errors.append('path_outside_plan');continue
  action=str(row.get('action') or '').casefold()
  if action not in {'create','modify'}:errors.append('action_rejected');continue
  replacements=[dict(x or {}) for x in row.get('replacements') or ()]
  content=row.get('content')
  if action=='create' and not isinstance(content,str):errors.append('create_requires_content')
  if action=='modify' and (not replacements or len(replacements)>MAX_EDITS):errors.append('modify_requires_bounded_replacements')
  normalized.append({'path':rel,'action':action,'content':content if isinstance(content,str) else None,'replacements':replacements})
 return {'contract_version':CONTRACT_VERSION,'ok':not errors,'errors':sorted(set(errors)),'normalized_edits':normalized,'plan_digest':str(plan.get('plan_digest') or ''),'content_free':True}

def _contained_path(root:Path,rel:str)->Path:
 path=(root/rel).resolve(strict=False)
 if path==root or root not in path.parents:raise ValueError('workspace_escape_rejected')
 cursor=root
 for part in PurePosixPath(rel).parts[:-1]:
  cursor=cursor/part
  if cursor.exists() and cursor.is_symlink():raise ValueError('workspace_symlink_rejected')
 if path.exists() and path.is_symlink():raise ValueError('workspace_symlink_rejected')
 return path


def apply_structured_edits(workspace_root:str|Path,plan:Mapping[str,Any],edits:Iterable[Mapping[str,Any]],*,workspace_authorization_receipt:Mapping[str,Any]|None)->dict[str,Any]:
 root=Path(workspace_root).expanduser().resolve()
 validation=validate_edit_contract(plan,edits)
 authorization=validate_operator_authorization(workspace_authorization_receipt,stage='workspace_implementation',subject_id=str(plan.get('candidate_id') or ''),subject_digest=str(plan.get('plan_digest') or ''),scope_digest=private_scope_digest(str(root)))
 if not authorization['ok']:return {'contract_version':CONTRACT_VERSION,'status':'blocked','reason':'workspace_authorization_required','source_modified':False,'provider_contacted':False,'installation_authorized':False,'content_free':True}
 if not validation['ok']:return {'contract_version':CONTRACT_VERSION,'status':'blocked','reason':'invalid_edit_contract','errors':validation['errors'],'source_modified':False,'provider_contacted':False,'installation_authorized':False,'content_free':True}
 paths={row['path']:_contained_path(root,row['path']) for row in validation['normalized_edits']}
 before={rel:_file_digest(path) for rel,path in paths.items()}
 changed=[];bytes_changed=0
 staged=[]
 for row in validation['normalized_edits']:
  path=paths[row['path']]
  if row['action']=='create':
   if path.exists():return {'contract_version':CONTRACT_VERSION,'status':'blocked','reason':'create_destination_exists','source_modified':False,'content_free':True}
   new=str(row['content']);old=''
  else:
   if not path.is_file():return {'contract_version':CONTRACT_VERSION,'status':'blocked','reason':'modify_source_missing','source_modified':False,'content_free':True}
   old=path.read_bytes().decode('utf-8');new=old
   for replacement in row['replacements']:
    find=str(replacement.get('find') or '');replace=str(replacement.get('replace') or '')
    if not find or new.count(find)!=1:return {'contract_version':CONTRACT_VERSION,'status':'blocked','reason':'replacement_not_unique','source_modified':False,'content_free':True}
    new=new.replace(find,replace,1)
  bytes_changed+=abs(len(new.encode())-len(old.encode()))+sum(1 for a,b in zip(old,new) if a!=b)
  staged.append((path,new.encode('utf-8'),row['path'],path.read_bytes() if path.is_file() else None))
 if bytes_changed>MAX_CHANGED_BYTES:return {'contract_version':CONTRACT_VERSION,'status':'blocked','reason':'change_budget_exceeded','source_modified':False,'content_free':True}
 # Apply only after every edit validates, and roll back the entire workspace batch on error.
 applied=[]
 try:
  for index,(path,new_bytes,rel,old_bytes) in enumerate(staged):
   path.parent.mkdir(parents=True,exist_ok=True)
   temp=path.with_name(f'.{path.name}.eidolon-{index}.tmp')
   temp.write_bytes(new_bytes);os.replace(temp,path);applied.append((path,old_bytes));changed.append(rel)
 except Exception:
  for path,old_bytes in reversed(applied):
   if old_bytes is None:
    path.unlink(missing_ok=True)
   else:
    path.write_bytes(old_bytes)
  raise
 after={rel:_file_digest(root/rel) for rel in changed}
 receipt={'contract_version':CONTRACT_VERSION,'status':'workspace_changed','plan_digest':str(plan.get('plan_digest') or ''),'workspace_authorization_id':authorization['authorization_id'],'workspace_authorization_receipt_digest':authorization['receipt_digest'],'changed_files':sorted(changed),'changed_file_count':len(changed),'before_digests':before,'after_digests':after,'workspace_only':True,'provider_contacted':False,'active_source_modified':False,'installation_authorized':False,'promotion_authorized':False,'content_free':True}
 receipt['change_digest']=_digest(receipt);return receipt

__all__=['CONTRACT_VERSION','validate_edit_contract','apply_structured_edits']
