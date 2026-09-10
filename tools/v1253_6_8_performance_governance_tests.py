from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['PYTHONDONTWRITEBYTECODE']='1'; os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1253-6-8-')
from performance_budgets import DEFAULT_BUDGETS,evaluate_budget,performance_budgets
from performance_regression import summarize_samples,compare_metric,build_performance_regression_receipt
from runtime_efficiency_benchmark import benchmark_runtime_efficiency
from runtime_efficiency_beta import runtime_efficiency_beta_contract
checks=[]
def req(v): checks.append(bool(v)); assert v
bud=performance_budgets(); req(bud['contract_version']=='v1253.6'); req(len(DEFAULT_BUDGETS)>=10); req(bud['release_authorized'] is False); req(bud['independent_authority_granted'] is False)
s=summarize_samples([1,2,3,4,100]); req(s['median']==3.0); req(s['p95']==100.0); req(s['count']==5)
passrow=evaluate_budget('dashboard_fast_status_ms',{'median':2.0,'p95':4.0}); req(passrow['ok'])
failrow=evaluate_budget('dashboard_fast_status_ms',{'median':30.0,'p95':80.0}); req(not failrow['ok'])
reg=compare_metric('warm_pre_provider_ms',[20,21,22],baseline_samples=[10,10,11]); req(reg['material_regression']); req(not reg['ok']); req(reg['automatic_rollback_authorized'] is False)
receipt=build_performance_regression_receipt({'warm_pre_provider_ms':[10,11,12,13,14]}); req(receipt['ok']); req(receipt['median_and_p95_used']); req(receipt['single_sample_release_gate'] is False)
contract=runtime_efficiency_beta_contract(source_root=ROOT); req(contract['ok']); req(contract['passed']==contract['total']); req(len(contract['versions'])==9)
bench=benchmark_runtime_efficiency(source_root=ROOT,include_persistent_scale=False); req(bench['ok']); req(DEFAULT_BUDGETS['terminal_cold_start_seconds']['hardware_sensitive'] is True and float(bench['measurements']['terminal_cold_start_seconds']['median'])>0); req(DEFAULT_BUDGETS['conversation_runtime_import_seconds']['hardware_sensitive'] is True and float(bench['measurements']['conversation_runtime_import_seconds']['median'])>0); req(bench['measurements']['dashboard_fast_status_ms']['median']<25.0); req(bench['measurements']['trusted_action_ack_build_ms']['median']<5.0); req(bench['provider_contacted'] is False); req(bench['release_authorized'] is False)
r={'suite':'v1253.6-v1253.8-performance-governance','ok':all(checks),'passed':sum(checks),'total':len(checks),'measurements':bench['measurements']}; print(json.dumps(r,sort_keys=True)); raise SystemExit(0 if r['ok'] else 1)
