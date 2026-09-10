from __future__ import annotations
"""Revision-bound provider generation of validated, structured code proposals.

v1200.7-v1200.9 may contact the configured local provider only after exact
approval and grounded planning. Output is persisted in external runtime data,
but is never applied, executed, or written into a project/workspace here.
"""
import ast, hashlib, json, re
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from grounded_development_planning import load_grounded_plan

CONTRACT_VERSION='v1200.9'; SCHEMA_VERSION='1'
MAX_FILES=24; MAX_FILE_BYTES=240*1024; MAX_TOTAL_BYTES=240*1024; MAX_RESPONSE_BYTES=240*1024
ALLOWED_OPS={'create','modify','delete'}

class _HTML(HTMLParser): pass

def _path(pid:str, rev:int, runtime_root=None)->Path:
    return _store_root(runtime_root)/'generation'/pid/f'revision-{int(rev)}.json'

def _raw_path(pid:str, rev:int, runtime_root=None)->Path:
    return _store_root(runtime_root)/'generation_private'/pid/f'revision-{int(rev)}-provider.json'

def _safe_relative(value:str)->str:
    if not isinstance(value,str) or not value or '\\' in value or '\x00' in value or len(value)>240:
        raise ValueError('invalid_relative_path')
    p=PurePosixPath(value)
    if p.is_absolute() or any(x in {'','.', '..'} for x in p.parts): raise ValueError('unsafe_relative_path')
    if ':' in p.parts[0]: raise ValueError('unsafe_relative_path')
    return p.as_posix()

def _syntax(path:str, content:str)->str:
    suffix=PurePosixPath(path).suffix.lower()
    try:
        if suffix=='.py': ast.parse(content)
        elif suffix=='.json': json.loads(content)
        elif suffix in {'.html','.htm'}: parser=_HTML(); parser.feed(content); parser.close()
        elif suffix in {'.js','.mjs','.cjs'}:
            if '\x00' in content: raise ValueError('nul')
            pairs={'(':')','[':']','{':'}'}; stack=[]; quote=None; esc=False
            for ch in content:
                if quote:
                    if esc: esc=False
                    elif ch=='\\': esc=True
                    elif ch==quote: quote=None
                    continue
                if ch in "'\"`": quote=ch
                elif ch in pairs: stack.append(pairs[ch])
                elif ch in pairs.values():
                    if not stack or stack.pop()!=ch: raise ValueError('unbalanced')
            if quote or stack: raise ValueError('unbalanced')
    except Exception as exc: raise ValueError(f'syntax_invalid:{path}') from exc
    return suffix.lstrip('.') or 'text'

def _extract(raw:str)->dict[str,Any]:
    if not isinstance(raw,str) or not raw.strip(): raise ValueError('empty_provider_output')
    if len(raw.encode('utf-8'))>MAX_RESPONSE_BYTES: raise ValueError('provider_output_too_large')
    text=raw.strip()
    if text.startswith('```'):
        text=re.sub(r'^```(?:json)?\s*','',text,flags=re.I); text=re.sub(r'\s*```$','',text)
    try: data=json.loads(text)
    except json.JSONDecodeError as exc: raise ValueError('provider_output_not_json') from exc
    if not isinstance(data,dict): raise ValueError('provider_output_not_object')
    return data

def _prompt(plan:Mapping[str,Any])->str:
    allowed=[x.get('relative_path') for x in plan.get('file_plan') or []]
    return json.dumps({
      'task':'Return ONLY one JSON object containing structured file changes. Do not use markdown.',
      'contract':{'schema_version':'1','files':[{'path':'relative/posix/path','operation':'create|modify|delete','content':'full file content; empty only for delete'}]},
      'authority':{'proposal_id':plan.get('proposal_id'),'revision':plan.get('proposal_revision'),'revision_digest':plan.get('proposal_revision_digest'),'planning_digest':plan.get('planning_digest'),'project_snapshot_digest':plan.get('project_snapshot_digest')},
      'specification':plan.get('specification'),'planned_paths':allowed,'constraints':{'only_planned_paths':True,'max_files':MAX_FILES,'max_file_bytes':MAX_FILE_BYTES,'max_total_bytes':MAX_TOTAL_BYTES,'no_commands':True,'no_external_paths':True}
    },sort_keys=True,separators=(',',':'))

def generate_or_resume_structured_output(proposal_id:str,*,expected_revision:int,expected_revision_digest:str,expected_planning_digest:str,runtime_root=None,provider_generate:Callable[[str],str]|None=None)->dict[str,Any]:
    with _proposal_lock(proposal_id,runtime_root):
        plan=load_grounded_plan(proposal_id,expected_revision,runtime_root=runtime_root)
        if not plan or plan.get('planning_digest')!=expected_planning_digest: return {'ok':False,'status':'stale_or_missing_plan'}
        if plan.get('proposal_revision_digest')!=expected_revision_digest: return {'ok':False,'status':'stale_proposal_revision'}
        if plan.get('planning_status')!='grounded_plan_ready': return {'ok':False,'status':'grounded_plan_required'}
        outpath=_path(proposal_id,expected_revision,runtime_root); existing=_read_json(outpath)
        if existing:
            supplied=existing.get('generation_digest'); calc=_digest({k:v for k,v in existing.items() if k!='generation_digest'})
            return ({**existing,'operation_status':'resumed'} if supplied==calc else {'ok':False,'status':'generation_record_invalid'})
        if provider_generate is None:
            from local_model import LocalModelClient
            provider_generate=LocalModelClient().generate
        prompt=_prompt(plan); prompt_digest=hashlib.sha256(prompt.encode()).hexdigest()
        try: raw=provider_generate(prompt)
        except Exception as exc:
            return {'ok':False,'status':'provider_failed','error_digest':hashlib.sha256((type(exc).__name__+':'+str(exc)).encode()).hexdigest(),'provider_contacted':True}
        try: data=_extract(raw)
        except ValueError as exc: return {'ok':False,'status':'structured_output_rejected','reason':str(exc),'provider_contacted':True}
        _atomic_json(_raw_path(proposal_id,expected_revision,runtime_root),{'schema_version':'1','prompt':prompt,'raw_output':raw,'prompt_digest':prompt_digest,'raw_digest':hashlib.sha256(raw.encode()).hexdigest()})
        authority=data.get('authority') or {}
        expected={'proposal_id':proposal_id,'revision':int(expected_revision),'revision_digest':expected_revision_digest,'planning_digest':expected_planning_digest,'project_snapshot_digest':plan.get('project_snapshot_digest')}
        if any(authority.get(k)!=v for k,v in expected.items()): return {'ok':False,'status':'authority_binding_rejected','provider_contacted':True}
        rows=data.get('files')
        if not isinstance(rows,list) or not rows or len(rows)>MAX_FILES: return {'ok':False,'status':'file_count_rejected','provider_contacted':True}
        allowed={x.get('relative_path'):x.get('operation') for x in plan.get('file_plan') or []}; seen=set(); total=0; validated=[]
        try:
            for row in rows:
                if not isinstance(row,dict): raise ValueError('file_entry_invalid')
                path=_safe_relative(row.get('path')); folded=path.casefold()
                if folded in seen: raise ValueError('duplicate_path')
                seen.add(folded); op=row.get('operation')
                if op not in ALLOWED_OPS or path not in allowed or op!=allowed[path]: raise ValueError('unplanned_or_mismatched_change')
                content=row.get('content','')
                if not isinstance(content,str) or (op=='delete' and content): raise ValueError('content_contract_invalid')
                size=len(content.encode()); total+=size
                if size>MAX_FILE_BYTES or total>MAX_TOTAL_BYTES: raise ValueError('content_budget_exceeded')
                syntax=_syntax(path,content) if op!='delete' else 'deleted'
                validated.append({'relative_path':path,'relative_path_digest':hashlib.sha256(path.encode()).hexdigest(),'operation':op,'content':content,'content_digest':hashlib.sha256(content.encode()).hexdigest(),'size_bytes':size,'syntax':syntax})
        except (TypeError,ValueError) as exc: return {'ok':False,'status':'structured_output_rejected','reason':str(exc),'provider_contacted':True}
        record={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'ok':True,'status':'validated_generation_ready','proposal_id':proposal_id,'proposal_revision':expected_revision,'proposal_revision_digest':expected_revision_digest,'planning_digest':expected_planning_digest,'project_snapshot_digest':plan.get('project_snapshot_digest'),'approval_receipt_digest':plan.get('approval_receipt_digest'),'prompt_digest':prompt_digest,'provider_raw_digest':hashlib.sha256(raw.encode()).hexdigest(),'files':validated,'file_count':len(validated),'total_bytes':total,'provider_contacted':True,'implementation_applied':False,'workspace_created':False,'command_executed':False,'selected_project_modified':False,'source_modified':False,'authority_granted':False}
        record['generation_digest']=_digest(record); _atomic_json(outpath,record); return {**record,'operation_status':'created'}

def public_structured_output(record:Mapping[str,Any])->dict[str,Any]:
    return {'ok':bool(record.get('ok')),'status':record.get('status',''),'proposal_id':record.get('proposal_id',''),'proposal_revision':record.get('proposal_revision',0),'planning_digest':record.get('planning_digest',''),'generation_digest':record.get('generation_digest',''),'file_count':record.get('file_count',0),'total_bytes':record.get('total_bytes',0),'path_digests':[x.get('relative_path_digest','') for x in record.get('files') or []],'content_digests':[x.get('content_digest','') for x in record.get('files') or []],'operations':[x.get('operation','') for x in record.get('files') or []],'syntax_kinds':[x.get('syntax','') for x in record.get('files') or []],'provider_contacted':bool(record.get('provider_contacted')),'provider_payload_exposed':False,'private_content_exposed':False,'implementation_applied':False,'workspace_created':False,'command_executed':False,'selected_project_modified':False,'source_modified':False,'authority_granted':False}
