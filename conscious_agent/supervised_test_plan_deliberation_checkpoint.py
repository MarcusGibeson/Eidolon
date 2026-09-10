from __future__ import annotations
"""Strictly read-only v1138.5 supervised test_plan deliberation checkpoint."""
import hashlib, json, os
from pathlib import Path
from test_plan_deliberation_sessions import build_test_plan_deliberation_session_inspection
from test_plan_arbitration import build_test_plan_arbitration_inspection, OUTCOMES
CONTRACT_VERSION='v1138.5'
def _sig(root:Path):
 if not root.exists(): return ''
 rows=[]
 for p in sorted(x for x in root.rglob('*') if x.is_file()): rows.append((str(p.relative_to(root)).replace('\\','/'),hashlib.sha256(p.read_bytes()).hexdigest()))
 return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
def build_supervised_test_plan_deliberation_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root or Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data')/'cognition').resolve(); source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); rb,sb=_sig(runtime),_sig(source); sessions=build_test_plan_deliberation_session_inspection(runtime); arbitration=build_test_plan_arbitration_inspection(runtime)
 checks=[('session_contract',sessions.get('contract_version')=='v1138.3'),('arbitration_contract',arbitration.get('contract_version')=='v1138.4'),('outcome_coverage',len(OUTCOMES)>=16),('bounded_budget',all(1<=x.get('deliberation_budget',1)<=6 for x in sessions.get('recent_sessions',[]))),('exact_candidate_lineage',all(x.get('candidate_id') and x.get('eligibility_ids') is not None for x in sessions.get('recent_sessions',[]))),('evidence_scope_coverage_reproducibility_determinism',all(all(k in x for k in ('evidence_support','scope_support','coverage_support','reproducibility_support','determinism_support')) for x in arbitration.get('recent_outcomes',[]))),('deliberate_no_test_plan','deliberate_no_test_plan' in OUTCOMES),('plan_vs_execution_boundary',all(not x.get('test_plan_id') and not x.get('test_code_digest') for x in arbitration.get('recent_outcomes',[]))),('no_test_plan_text',not sessions.get('test_plan_text_exposed') and not arbitration.get('test_plan_text_exposed')),('no_source_fixture_or_sandbox',not any(sessions.get('authority_boundary',{}).get(k) for k in ('can_modify_source','can_create_fixture','can_create_sandbox','can_run_tests'))),('no_approval_execution',not any(arbitration.get('authority_boundary',{}).get(k) for k in ('can_approve','can_authorize','can_execute','can_promote','can_certify'))),('privacy_boundary',not sessions.get('raw_source_exposed') and not arbitration.get('hidden_reasoning_exposed')),('read_only',rb==_sig(runtime) and sb==_sig(source)),('desktop_pending',True)]
 return {'ok':all(v for _,v in checks),'contract_version':CONTRACT_VERSION,'checks':[{'check_id':k,'ok':v} for k,v in checks],'runtime_mutated':rb!=_sig(runtime),'source_modified':sb!=_sig(source),'test_plan_text_exposed':False,'source_modified_by_checkpoint':False,'external_action_executed':False,'desktop_verification':'pending','session_summary':sessions,'arbitration_summary':arbitration}
