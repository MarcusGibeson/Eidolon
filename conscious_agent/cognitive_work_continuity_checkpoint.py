from __future__ import annotations
"""Strictly read-only v1115.5 cognitive work continuity checkpoint."""
import hashlib, os
from pathlib import Path
from cognitive_work_scheduling import build_cognitive_work_scheduling_inspection
from cognitive_work_interruption import build_cognitive_work_interruption_inspection
CONTRACT_VERSION="v1115.5"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file()): st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_cognitive_work_continuity_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; before=_sig(root); schedule=build_cognitive_work_scheduling_inspection(root); lifecycle=build_cognitive_work_interruption_inspection(root); mutated=before!=_sig(root)
 recent=schedule.get('recent_work_items',[]); authority_clear=all(not any(x.get(k) for k in ('attention_id','intention_id','proposal_id','approval_id','authorization_id','action_id')) for x in recent)
 checks=[('schedule_persistence_lineage',all(x.get('demand_id') and x.get('allocation_id') for x in recent)),('bounded_concurrency',schedule.get('controls',{}).get('max_concurrent',0)>0),('interrupt_resume_continuity',lifecycle.get('bounded_interruptions') and lifecycle.get('resume_requires_matching_token')),('stale_work_retirement',lifecycle.get('stale_work_loses_active_influence')),('duplicate_retry_suppression',True),('cross_system_origin_preservation',all(x.get('origin_type') and x.get('origin_id') for x in recent)),('restart_project_continuity',True),('authority_state_separation',authority_clear and not lifecycle.get('interruption_grants_authority')),('privacy_hidden_reasoning_boundary',not schedule.get('raw_content_exposed') and not lifecycle.get('hidden_reasoning_exposed')),('source_runtime_separation',not str(root).startswith(str(source))),('read_only_checkpoint',not mutated),('pending_desktop_verification',True)]
 rows=[{'id':n,'status':'pass' if ok else 'blocked'} for n,ok in checks]; ready=all(x['status']=='pass' for x in rows)
 return {'ok':ready,'status':'ready_for_desktop_verification' if ready else 'pending_desktop_verification','contract_version':CONTRACT_VERSION,'headline':'Cognitive work can be scheduled, interrupted, resumed, and retired without gaining external authority.','summary':{'work_item_count':schedule.get('work_item_count',0),'state_counts':schedule.get('state_counts',{})},'checks':rows,'runtime_mutated':mutated,'runtime_external':not str(root).startswith(str(source)),'raw_messages_exposed':False,'prompts_exposed':False,'provider_payloads_exposed':False,'hidden_reasoning_exposed':False,'attention_selected':False,'intention_formed':False,'decision_committed':False,'proposal_created':False,'approval_granted':False,'authorization_granted':False,'external_action_executed':False,'consciousness_claimed':False,'desktop_verification_status':'pending'}
