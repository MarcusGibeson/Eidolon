from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from causal_diagnostic_reasoning_foundations import *
from calibrated_uncertainty import *
from calibrated_uncertainty_foundations import validate_uncertainty_claim
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
a=build_causal_hypothesis(hypothesis_code='env',cause_class='environment',symptom_codes=['fail'],probe_code='p',expected_if_true='env',expected_if_false='code',confidence='high');b=build_causal_hypothesis(hypothesis_code='code',cause_class='implementation',symptom_codes=['fail'],probe_code='p',expected_if_true='code',expected_if_false='env',confidence='medium');m=build_causal_diagnostic_model(symptom_codes=['fail'],hypotheses=[a,b]);m=apply_probe_outcome(m,probe_code='p',observed_outcome='code',evidence_code='probe');r=calibrated_causal_claims(m);req(r['ok'] and r['claim_count']==2,'causal_claims');states={x['claim_code']:x['epistemic_state'] for x in r['claims']};req(states['causal_env']=='suspended','falsified_suspended');req(states['causal_code']=='inferred','supported_inferred');req(all(validate_uncertainty_claim(x)['ok'] for x in r['claims']),'valid_claims')
o=uncertainty_claim_from_environment_fact({'fact_code':'os_family','epistemic_state':'observed','evidence_code':'platform_probe'});req(o['epistemic_state']=='observed' and o['confidence_band'] in {'very_high','high'},'env_observed');u=uncertainty_claim_from_environment_fact({'fact_code':'port_state','epistemic_state':'unknown'});req(u['epistemic_state']=='unverified' and u['confidence']<=20,'unknown_not_false');st=uncertainty_claim_from_environment_fact({'fact_code':'python_env','epistemic_state':'observed','evidence_code':'probe','stale':True});req(st['freshness']=='stale' and st['confidence']<85,'stale_env');pub=public_uncertainty_summary(o);req(pub['ok'] and not pub['raw_content_exposed'],'public')
print(json.dumps({'ok':True,'suite':'v1282.3-5-calibrated-uncertainty-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
