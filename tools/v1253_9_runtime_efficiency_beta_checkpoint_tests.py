from __future__ import annotations
import json, os, statistics, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1253-9-')
from checkpoint_registry import checkpoint_registry_manifest,lookup_checkpoint,validate_checkpoint_report
from release_authority import release_authority_record,validate_release_authority
from release_metadata_consolidation import validate_release_metadata_consolidation
from runtime_efficiency_beta import runtime_efficiency_beta_contract
from runtime_efficiency_beta_checkpoint import build_runtime_efficiency_beta_checkpoint
from runtime_efficiency_benchmark import benchmark_runtime_efficiency
from performance_budgets import DEFAULT_BUDGETS,evaluate_budget
checks=[]
def req(v): checks.append(bool(v)); assert v
contract=runtime_efficiency_beta_contract(source_root=ROOT); req(contract['ok']); req(contract['passed']==contract['total']); req(len(contract['versions'])==9)
bench=benchmark_runtime_efficiency(source_root=ROOT,include_persistent_scale=True); req(bench['ok']); req(bench['persistent_state_medium_scale']['latency_ok']); req(float(bench['measurements']['terminal_cold_start_seconds']['median'])>0); req(float(bench['measurements']['conversation_runtime_import_seconds']['median'])>0); req(bench['measurements']['dashboard_fast_status_ms']['median']<25.0)
for name in ('trusted_action_ack_build_ms','dashboard_fast_status_ms'):
    req(evaluate_budget(name,bench['measurements'][name])['ok'])
req(DEFAULT_BUDGETS['terminal_cold_start_seconds']['hardware_sensitive'] is True); req(DEFAULT_BUDGETS['conversation_runtime_import_seconds']['hardware_sensitive'] is True)
# Exercise the ordinary conversation critical path with a zero-latency local fake provider.
import conversation_runtime as cr
class FakeClient:
    prompts=[]
    def __init__(self,config,cancel_event=None): self.config=config; self.last_retry_count=0; self.last_metrics={'prompt_eval_count':1,'eval_count':1}; self.provider=self
    def generate(self,prompt): type(self).prompts.append(prompt); return 'A concise local response.'
    def stream(self,prompt): type(self).prompts.append(prompt); yield 'A concise local response.'
    def close(self): pass
    def cancel(self): pass
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
cr.LocalModelClient=FakeClient
pre=[]; deferred=[]
for message in ('Hi!','Hello again.','Thanks for explaining that.','Nice, that makes sense.','Hello there.','Thanks again.','That makes sense.','Nice to chat.'):
    result=cr.run_conversation_turn(message,source='v1253-checkpoint',use_ai=True)
    req(result.success); req(result.cognitive_context['critical_path']['goal_planning_deferred'] is True); req(result.cognitive_context['critical_path']['deferred_goal_planning_completed'] is True)
    pre.append(float(result.timings_ms['pre_provider'])); deferred.append(float(result.timings_ms.get('deferred_goal_planning') or 0))
warm_pre=pre[3:]; warm_measurement={'median':statistics.median(warm_pre),'p95':max(warm_pre)}; warm_budget=evaluate_budget('warm_pre_provider_ms',warm_measurement)
if not warm_budget['ok']: print(json.dumps({'warm_pre_provider_ms':warm_pre,'warm_budget':warm_budget},sort_keys=True),file=sys.stderr)
req(warm_budget['ok']); req(statistics.median(deferred[3:])<50.0)
actual_prompt_estimates=[len(value)//4 for value in FakeClient.prompts]; req(max(actual_prompt_estimates)<3000)
cp=build_runtime_efficiency_beta_checkpoint(source_root=ROOT); req(cp['ok']); req(cp['checkpoint_version']=='1253.9'); req(cp['status']=='runtime_efficiency_beta_checkpoint_ready'); req(validate_checkpoint_report(cp,source_root=ROOT)['ok'])
reg=checkpoint_registry_manifest(source_root=ROOT); req(reg['ok']); req(reg['record_count']>=90); req(lookup_checkpoint('1253.9') is not None); req(lookup_checkpoint('1253.9').title=='Runtime Efficiency Beta Checkpoint')
auth=release_authority_record(); req(auth['history_count']>=90); req(any(row['version']=='1253.9' and row['title']=='Runtime Efficiency Beta Checkpoint' for row in auth['history'])); req(isinstance(auth['codex_review_state'],str) and bool(auth['codex_review_state'].strip())); req(validate_release_authority(source_root=ROOT)['ok']); req(validate_release_metadata_consolidation(source_root=ROOT)['ok'])
for k in ('installation_authorized','promotion_authorized','certification_authorized','release_authorized','provider_contact_authorized','tool_execution_authorized','project_mutation_authorized','source_mutation_authorized','approval_granted','independent_authority_granted'): req(auth[k] is False)
r={'suite':'v1253.9-runtime-efficiency-beta-checkpoint','ok':all(checks),'passed':sum(checks),'total':len(checks),'warm_pre_provider_ms':warm_pre,'deferred_goal_planning_ms':deferred[1:],'prompt_estimated_tokens':actual_prompt_estimates,'benchmark_measurements':bench['measurements'],'persistent_medium_ms':bench['persistent_state_medium_scale']['measured_ms']}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
