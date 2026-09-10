from __future__ import annotations
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from test_debug_performance_intelligence import *
checks=[]
def req(v,n):checks.append(n);assert v,n

def tree(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def fixture(base):
 r=base/'repo';(r/'pkg').mkdir(parents=True);(r/'tests').mkdir();(r/'ui').mkdir();(r/'schema').mkdir()
 (r/'pkg/core.py').write_text('def work(x):\n return x+1\n')
 (r/'pkg/service.py').write_text('from pkg.core import work\ndef serve(x): return work(x)\n')
 (r/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work(): assert work(1)==2\n')
 (r/'ui/dashboard.py').write_text('from pkg.service import serve\napp=object()\n')
 (r/'schema/model.py').write_text('class Record: pass\n')
 return r
with tempfile.TemporaryDirectory(prefix='eidolon-v1675-9-') as td:
 base=Path(td);repo=fixture(base);before=tree(repo);rt=base/'rt'
 plan_result=build_test_intelligence_plan(repo,['pkg/core.py'],runtime_root=rt);plan=plan_result['plan']
 req(plan_result['ok'],'plan_ok')
 req('focused' in plan['selected_test_kinds'] and 'regression' in plan['selected_test_kinds'],'base_test_kinds')
 req('integration' in plan['selected_test_kinds'],'integration_selected')
 req(plan['candidate_test_count']>=1,'candidate_test')
 req(plan['plan_complete'],'plan_complete')
 req(not plan['tests_executed'],'no_test_execution')
 req(not plan['raw_paths_exposed'] and not plan['raw_source_content_exposed'],'plan_privacy')
 req(not plan['action_executed'] and not plan['standing_authority_granted'],'plan_authority')
 uncertain=build_test_intelligence_plan(repo,['missing.py'],runtime_root=rt)
 req(not uncertain['ok'] and uncertain['status']=='test_intelligence_plan_uncertain','uncertain_plan')
 req(not uncertain['plan']['plan_complete'] and uncertain['plan']['uncertainty_count']>0,'uncertainty_preserved')

 debug=create_debugging_evidence(symptom_codes=['verification_failed','timeout'],hypotheses=[
  {'hypothesis_code':'import_cycle','cause_class':'import','supporting_evidence':['trace_import'], 'disproof_probe':'minimal_import'},
  {'hypothesis_code':'timing','cause_class':'timeout','supporting_evidence':['slow_run'],'disconfirming_evidence':['fast_control'], 'disproof_probe':'bounded_timeout_control'},
 ],reproduction_steps=['create fixture','run focused test'],observed_outcomes=['fail','pass'],runtime_root=rt)
 d=debug['debugging_evidence'];req(debug['ok'],'debug_ok')
 req(d['hypothesis_count']==2,'hypothesis_count')
 req(d['counterexamples_preserved'],'counterexample')
 req(d['hypothesis_states']['contested']>=1,'contested')
 req(d['reproduction_step_count']==2 and d['observed_outcome_count']==2,'repro_counts')
 req(not d['root_cause_proven'] and not d['diagnostic_executed'],'root_cause_truth')
 req(not d['raw_reproduction_exposed'] and not d['raw_output_exposed'],'debug_privacy')
 req(not d['action_executed'] and not d['standing_authority_granted'],'debug_authority')
 empty=create_debugging_evidence(symptom_codes=[],hypotheses=[],runtime_root=rt);req(not empty['ok'] and empty['status']=='symptom_evidence_required','symptom_required')

 flake=classify_flakiness(['pass','fail','pass']);req(flake['flaky_observed'] and flake['status']=='flaky_observed','flaky')
 stable=classify_flakiness(['pass','pass']);req(not stable['flaky_observed'] and stable['status']=='stable_observed','stable')
 little=classify_flakiness(['pass']);req(little['status']=='insufficient_repeated_evidence','flaky_insufficient')
 req(not flake['reruns_executed'] and not flake['flaky_root_cause_proven'],'flaky_truth')

 perf=build_before_after_performance_evidence({'chat_first_paint_ms':[11,12,13,12,11]},metrics_before={'chat_first_paint_ms':[10,10,11,10,10]})
 req(perf['metric_count']==1 and perf['median_and_p95_used'],'perf_stats')
 req(perf['measurements_supplied_not_executed'],'perf_no_execution')
 req(not perf['single_sample_release_gate'],'perf_no_single_sample')
 req(not perf['automatic_rollback_authorized'] and not perf['release_authorized'],'perf_authority')
 reg=build_before_after_performance_evidence({'chat_first_paint_ms':[100,110,105]},metrics_before={'chat_first_paint_ms':[10,11,10]})
 req(not reg['ok'] and reg['material_regression_count']==1,'perf_regression')

 cp=run_portable_testing_debugging_checkpoint([{
  'name':'python-case','root':repo,'changed_paths':['pkg/core.py'],'symptom_codes':['verification_failed'],
  'hypotheses':[{'hypothesis_code':'assertion','cause_class':'assertion','supporting_evidence':['failed_assertion']}],
  'reproduction_steps':['focused fixture'],'outcomes':['fail','pass'],
  'metrics_after':{'chat_first_paint_ms':[11,12,11]},'metrics_before':{'chat_first_paint_ms':[10,10,10]},
 }],runtime_root=base/'bench_rt')['checkpoint']
 req(cp['case_count']==1 and cp['aggregate_score']>=0.8,'checkpoint_score')
 req(cp['portable_only'] and cp['native_evidence_deferred'],'checkpoint_deferred')
 req(not cp['native_windows_verified'],'windows_deferred')
 req(not cp['raw_debug_content_exposed'],'checkpoint_privacy')
 req(not cp['action_executed'] and not cp['standing_authority_granted'],'checkpoint_authority')
 req(tree(repo)==before,'source_immutable')
print(json.dumps({'suite':'v1675.9-testing-debugging-performance-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
