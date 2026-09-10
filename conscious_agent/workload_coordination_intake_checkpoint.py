from __future__ import annotations
"""Strictly read-only v1143.2 Workload Coordination Intake checkpoint."""
import hashlib, os
from pathlib import Path
from workload_budget_eligibility import build_workload_budget_eligibility_inspection, WORKLOAD_KINDS
from workload_coordination_candidates import build_workload_coordination_candidate_inspection, ACTIONS
CONTRACT_VERSION='v1143.2'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _sig(root:Path):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob('*') if x.is_file() and x.suffix not in {'.pyc','.pyo'} and '__pycache__' not in x.parts):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_workload_coordination_intake_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb=_sig(runtime);sb=_sig(source)
 e=build_workload_budget_eligibility_inspection(runtime);c=build_workload_coordination_candidate_inspection(runtime);er=e.get('recent_records',[]);cr=c.get('recent_records',[])
 checks=[('eligibility_contract',e.get('contract_version')=='v1143.0'),('candidate_contract',c.get('contract_version')=='v1143.1'),('all_workload_classes',WORKLOAD_KINDS=={'cognition','conversation','inquiry','development'}),('bounded_budgets',all(all(int(r.get(k) or 0)>=0 for k in ('cpu_budget_ms','memory_budget_mb','latency_budget_ms','token_budget')) for r in er+cr)),('bounded_priority',all(0<=int(r.get('priority') or 0)<=100 for r in er+cr)),('recognized_actions',all(r.get('coordination_action') in ACTIONS for r in cr)),('exact_eligibility_lineage',all(r.get('eligibility_id') and r.get('workload_id') for r in cr)),('advisory_only',all(r.get('advisory_only') for r in cr)),('no_execution',not e.get('execution_started') and not c.get('execution_started') and all(not r.get('execution_started') for r in er+cr)),('no_schedule_mutation',not c.get('schedule_mutated') and all(not r.get('schedule_mutated') for r in cr)),('duplicate_and_lifecycle_visibility',all(r.get('state') for r in er+cr)),('privacy',not e.get('raw_content_exposed') and not c.get('raw_content_exposed') and not e.get('workload_payload_exposed') and not c.get('workload_payload_exposed')),('authority_separation',not any(e.get('authority_boundary',{}).values()) and not any(c.get('authority_boundary',{}).values())),('source_runtime_separation',runtime!=source),('read_only',rb==_sig(runtime) and sb==_sig(source)),('desktop_verification_pending',True)]
 passed=sum(bool(v) for _,v in checks)
 return {'ok':passed==len(checks),'status':'ready_for_desktop_verification' if passed==len(checks) else 'review_required','contract_version':CONTRACT_VERSION,'passed':passed,'total':len(checks),'checks':[{'id':k,'status':'pass' if v else 'fail'} for k,v in checks],'eligibility':e,'candidates':c,'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'raw_content_exposed':False,'workload_payload_exposed':False,'execution_started':False,'schedule_mutated':False,'preemption_executed':False,'approval_created':False,'authorization_created':False,'installation_performed':False,'promotion_performed':False,'certification_performed':False,'consciousness_proven':False,'desktop_verification':'pending'}
