from __future__ import annotations
"""Bounded browser preview for isolated implementation workspaces.

v1201.3-v1201.5 serves only validated files from the external workspace through
an opaque preview token. It creates content-free evidence and grants no apply,
command, test, source, model, or release authority.
"""
import hashlib, mimetypes
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_implementation_workspace import _record_path, _workspace_root, _verify_record
from structured_development_generation import _safe_relative

SCHEMA_VERSION='1'; CONTRACT_VERSION='v1201.5'
MAX_PREVIEW_ASSET_BYTES=1024*1024
ALLOWED_SUFFIXES={'.html','.htm','.css','.js','.mjs','.json','.svg','.png','.jpg','.jpeg','.gif','.webp','.ico','.txt'}

class _HTMLFacts(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags=0; self.title=False; self.viewport=False; self.local_assets=[]
    def handle_starttag(self, tag, attrs):
        self.tags+=1; values=dict(attrs)
        if tag=='title': self.title=True
        if tag=='meta' and str(values.get('name','')).lower()=='viewport': self.viewport=True
        value=values.get('src') if tag in {'script','img'} else values.get('href') if tag=='link' else None
        if value and not str(value).startswith(('http:','https:','//','data:','#')): self.local_assets.append(str(value).split('?',1)[0].split('#',1)[0])

def _preview_path(pid:str, rev:int, runtime_root=None)->Path:
    return _store_root(runtime_root)/'previews'/pid/f'revision-{int(rev)}.json'
def _token_path(token:str, runtime_root=None)->Path:
    return _store_root(runtime_root)/'preview_tokens'/f'{token}.json'

def _load_workspace(pid:str, rev:int, runtime_root=None):
    rec=_read_json(_record_path(pid,rev,runtime_root))
    if not rec: return None,None
    root=_workspace_root(pid,rev,str(rec.get('generation_digest') or ''),runtime_root)
    return rec,root

def create_or_resume_workspace_preview(proposal_id:str,*,expected_revision:int,expected_revision_digest:str,runtime_root=None)->dict[str,Any]:
    with _proposal_lock(proposal_id,runtime_root):
        rec,root=_load_workspace(proposal_id,expected_revision,runtime_root)
        if not rec or not root: return {'ok':False,'status':'workspace_missing'}
        if rec.get('proposal_revision_digest')!=expected_revision_digest: return {'ok':False,'status':'stale_proposal_revision'}
        if not _verify_record(rec,root): return {'ok':False,'status':'workspace_record_invalid'}
        existing=_read_json(_preview_path(proposal_id,expected_revision,runtime_root))
        if existing:
            valid=existing.get('preview_digest')==_digest({k:v for k,v in existing.items() if k!='preview_digest'}) and existing.get('workspace_digest')==rec.get('workspace_digest')
            return ({**existing,'operation_status':'resumed'} if valid else {'ok':False,'status':'preview_record_invalid'})
        rows=rec.get('files') or []; names={str(x.get('relative_path') or '') for x in rows}
        entry=next((x for x in ('index.html','index.htm') if x in names),None)
        if not entry: return {'ok':False,'status':'preview_unsupported','limitation_code':'html_entrypoint_required','content_free':True}
        path=root/entry
        if path.stat().st_size>MAX_PREVIEW_ASSET_BYTES: return {'ok':False,'status':'preview_budget_exceeded'}
        parser=_HTMLFacts(); parser.feed(path.read_text(encoding='utf-8'))
        missing=[]
        for asset in parser.local_assets:
            try: rel=_safe_relative(unquote(asset))
            except ValueError: missing.append(hashlib.sha256(asset.encode()).hexdigest()); continue
            if rel not in names: missing.append(hashlib.sha256(rel.encode()).hexdigest())
        token=hashlib.sha256(f"{proposal_id}:{expected_revision}:{rec['workspace_digest']}".encode()).hexdigest()
        evidence={'html_tag_count':parser.tags,'has_title':parser.title,'has_viewport':parser.viewport,'local_asset_count':len(parser.local_assets),'missing_asset_count':len(missing),'missing_asset_digests':sorted(missing),'entrypoint_digest':hashlib.sha256(entry.encode()).hexdigest()}
        record={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'ok':True,'status':'browser_preview_ready','proposal_id':proposal_id,'proposal_revision':int(expected_revision),'proposal_revision_digest':expected_revision_digest,'workspace_digest':rec['workspace_digest'],'generation_digest':rec['generation_digest'],'planning_digest':rec['planning_digest'],'preview_token':token,'preview_url':f'/development-preview/{token}/','entrypoint':entry,'workspace_path':str(root),'evidence':evidence,'selected_project_modified':False,'source_modified':False,'command_executed':False,'tests_executed':False,'apply_authorized':False,'release_authorized':False,'authority_granted':False}
        record['preview_digest']=_digest(record)
        _atomic_json(_preview_path(proposal_id,expected_revision,runtime_root),record)
        _atomic_json(_token_path(token,runtime_root),{'preview_digest':record['preview_digest'],'proposal_id':proposal_id,'revision':int(expected_revision),'workspace_digest':rec['workspace_digest']})
        return {**record,'operation_status':'created'}

def resolve_preview_asset(token:str,relative_path:str,runtime_root=None)->dict[str,Any]:
    token=str(token or '').lower()
    if len(token)!=64 or any(c not in '0123456789abcdef' for c in token): return {'ok':False,'status':'invalid_preview_token'}
    index=_read_json(_token_path(token,runtime_root))
    if not index: return {'ok':False,'status':'preview_not_found'}
    record=_read_json(_preview_path(str(index.get('proposal_id') or ''),int(index.get('revision') or 0),runtime_root))
    if not record or record.get('preview_digest')!=index.get('preview_digest') or record.get('preview_digest')!=_digest({k:v for k,v in record.items() if k!='preview_digest'}): return {'ok':False,'status':'preview_record_invalid'}
    requested=unquote(relative_path or '') or str(record.get('entrypoint') or '')
    try: rel=_safe_relative(requested)
    except ValueError: return {'ok':False,'status':'preview_path_rejected'}
    path=Path(str(record.get('workspace_path') or ''))/rel
    root=Path(str(record.get('workspace_path') or '')).resolve()
    try: resolved=path.resolve(strict=True)
    except OSError: return {'ok':False,'status':'preview_asset_missing'}
    if root not in resolved.parents or resolved.is_symlink() or not resolved.is_file(): return {'ok':False,'status':'preview_path_rejected'}
    if resolved.suffix.lower() not in ALLOWED_SUFFIXES or resolved.stat().st_size>MAX_PREVIEW_ASSET_BYTES: return {'ok':False,'status':'preview_asset_rejected'}
    data=resolved.read_bytes(); mime=mimetypes.guess_type(resolved.name)[0] or 'application/octet-stream'
    return {'ok':True,'status':'preview_asset_ready','content':data,'content_type':mime,'content_digest':hashlib.sha256(data).hexdigest(),'size_bytes':len(data)}

def public_preview(record:Mapping[str,Any])->dict[str,Any]:
    return {'ok':bool(record.get('ok')),'status':record.get('status',''),'proposal_id':record.get('proposal_id',''),'proposal_revision':record.get('proposal_revision',0),'workspace_digest':record.get('workspace_digest',''),'preview_digest':record.get('preview_digest',''),'preview_url':record.get('preview_url',''),'evidence':record.get('evidence',{}),'private_path_exposed':False,'private_content_exposed':False,'selected_project_modified':False,'source_modified':False,'command_executed':False,'tests_executed':False,'apply_authorized':False,'release_authorized':False,'authority_granted':False}
