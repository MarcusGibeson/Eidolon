from __future__ import annotations
"""v1317 read-only local change-history understanding with content-minimized evidence."""
import subprocess,re
from pathlib import Path
from project_evidence_store import *
from repository_inventory import build_repository_inventory
CONTRACT_VERSION='v1317.8';MAX_COMMITS=80;DEBT_MARKERS=('deprecated','legacy','compatibility','temporary','migration','workaround','debt')
def _path(wid,runtime_root=None):return evidence_root('change_history',runtime_root)/'records'/f'{wid}.json'
def _local_git(root:Path):
 if not (root/'.git').exists():return []
 try:r=subprocess.run(['git','-C',str(root),'log','--no-decorate','--format=%H%x09%s','-n',str(MAX_COMMITS)],capture_output=True,text=True,timeout=8,check=False)
 except (OSError,subprocess.TimeoutExpired):return []
 if r.returncode:return []
 out=[]
 for line in r.stdout.splitlines():
  if '\t' not in line:continue
  sha,sub=line.split('\t',1);low=sub.lower();out.append({'commit_digest':digest(sha),'subject_digest':digest(sub),'reason_codes':sorted({m for m in DEBT_MARKERS if m in low}),'source':'local_git','confidence':'observed','raw_subject_persisted':False})
 return out
def _release_history(root:Path):
 p=root/'README_RELEASE_HISTORY.md'
 try:text=p.read_text(encoding='utf-8')
 except OSError:return []
 rows=[]
 for line in text.splitlines():
  if line.startswith('## '):rows.append({'entry_digest':digest(line),'source':'release_history','confidence':'inferred_from_release_evidence','raw_entry_persisted':False})
 return rows[:MAX_COMMITS]
def build_change_history_understanding(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None):
 root=Path(source_root).resolve();inv=build_repository_inventory(root,runtime_root=runtime_root,now_unix=now_unix)['inventory'];wid=inv['workspace_digest'];git=_local_git(root);rel=[] if git else _release_history(root);evidence=git or rel;source='local_git' if git else ('release_history' if rel else 'none');confidence='observed' if git else ('inferred_from_release_evidence' if rel else 'unverified');debt=sorted({c for x in git for c in x.get('reason_codes',[])})
 row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':inv['source_manifest_digest'],'history_source':source,'confidence':confidence,'evidence_count':len(evidence),'evidence':evidence,'historical_debt_markers':debt,'network_contacted':False,'repository_modified':False,'raw_commit_messages_persisted':False,'history_is_explanation_not_proof':True,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'change_history_ready','change_history':public_change_history(row),'action_executed':False,**DENIED_AUTHORITY}
def public_change_history(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'history_source':row.get('history_source'),'confidence':row.get('confidence'),'evidence_count':int(row.get('evidence_count',0)),'historical_debt_markers':list(row.get('historical_debt_markers') or []),'network_contacted':False,'repository_modified':False,'raw_commit_messages_exposed':False,'history_is_explanation_not_proof':True,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_change_history(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (row if include_private else public_change_history(row)) if row and valid(row) else {}
def process_change_history_control(text:str,*,project_root=None,runtime_root=None):
 if str(text or '').strip().lower() not in {'inspect change history','show change history'}:return {'active':False}
 if not project_root:return {'active':True,'ok':False,'status':'project_root_required','action_executed':False,**DENIED_AUTHORITY}
 return {'active':True,**build_change_history_understanding(project_root,runtime_root=runtime_root)}
__all__=['CONTRACT_VERSION','build_change_history_understanding','load_change_history','process_change_history_control']
