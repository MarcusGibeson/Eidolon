from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from diagnostic_repair_reasoning_foundations import form_competing_explanations
from causal_diagnostic_reasoning import *
from causal_diagnostic_reasoning_foundations import apply_probe_outcome,validate_causal_diagnostic_model
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
obs={'verification_status':'python_runtime_unavailable','failed_phase_classes':['test'],'failed_exit_classes':['runtime_missing'],'environment_blocker_observed':True,'cleanup_confirmed':True}
old=form_competing_explanations(obs);req(len(old)>=2,'v1257_competing');m=causal_model_from_v1257(obs,old);req(validate_causal_diagnostic_model(m)['ok'],'bridge');req(m['hypothesis_count']>=2,'count');sel=choose_discriminating_diagnostic(m);req(sel['ok'] and sel['can_falsify_competing_explanation'],'selected');req(not sel['diagnostic_executed'] and not sel['provider_contacted'] and not sel['tests_executed'],'selection_no_execution')
# Choose the predicted implementation outcome to falsify an environment explanation.
updated=apply_probe_outcome(m,probe_code='cause_class_discriminator',observed_outcome='supports_implementation',evidence_code='bounded_runtime_probe');summary=causal_diagnostic_public_summary(updated);req(summary['ok'],'summary');req(summary['content_minimized'],'summary_private');req(summary['root_cause_proven'] is False,'summary_not_proven');req(any(x['causal_status']=='falsified' for x in summary['hypotheses']),'some_falsified');req(any(x['causal_status']=='supported' for x in summary['hypotheses']),'some_supported')
print(json.dumps({'ok':True,'suite':'v1281.3-5-causal-diagnostic-reasoning-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
