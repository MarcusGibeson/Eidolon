from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from causal_diagnostic_reasoning_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
h1=build_causal_hypothesis(hypothesis_code='runtime_missing',cause_class='environment',symptom_codes=['tests_failed'],supporting_evidence=['runtime_error'],probe_code='runtime_probe',expected_if_true='runtime_missing',expected_if_false='runtime_available',confidence='medium')
h2=build_causal_hypothesis(hypothesis_code='code_defect',cause_class='implementation',symptom_codes=['tests_failed'],supporting_evidence=['test_failure'],probe_code='runtime_probe',expected_if_true='runtime_available',expected_if_false='runtime_missing',confidence='medium')
m=build_causal_diagnostic_model(symptom_codes=['tests_failed'],hypotheses=[h1,h2]);req(validate_causal_diagnostic_model(m)['ok'],'model');req(m['selected_probe_code']=='runtime_probe','discriminator');req(m['selected_probe_can_falsify_competing_explanation'],'falsifiable');req(not m['root_cause_proven'],'not_proven')
a=apply_probe_outcome(m,probe_code='runtime_probe',observed_outcome='runtime_available',evidence_code='runtime_observed_available');req(validate_causal_diagnostic_model(a)['ok'],'updated');status={x['hypothesis_code']:x['causal_status'] for x in a['hypotheses']};req(status['runtime_missing']=='falsified','env_falsified');req(status['code_defect']=='supported','code_supported');req(not a['root_cause_proven'],'single_probe_not_proven')
for k,v in AUTHORITY_FLAGS.items():req(a.get(k) is v,'auth_'+k)
tam=dict(a);tam['root_cause_proven']=True;req(not validate_causal_diagnostic_model(tam)['digest_valid'],'tamper')
print(json.dumps({'ok':True,'suite':'v1281.0-2-causal-diagnostic-reasoning-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
