from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from calibrated_uncertainty_foundations import *
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
for state,score,cap in [('observed',90,99),('inferred',70,80),('assumed',90,40),('unverified',80,20),('suspended',80,30)]:
 c=build_uncertainty_claim(claim_code='x_'+state,epistemic_state=state,confidence=score,evidence_codes=['e']);req(validate_uncertainty_claim(c)['ok'],'valid_'+state);req(c['confidence']<=cap,'cap_'+state)
c=build_uncertainty_claim(claim_code='runtime_available',epistemic_state='unverified',confidence=10);s=apply_uncertainty_evidence(c,evidence_kind='observed_support',evidence_code='probe1');req(s['epistemic_state']=='observed' and s['confidence']>=75,'observed_raise');x=apply_uncertainty_evidence(s,evidence_kind='observed_contradiction',evidence_code='probe2');req(x['confidence']<s['confidence'],'contradiction_lowers');req(x['epistemic_state']=='suspended','contradiction_suspends');d=apply_uncertainty_evidence(x,evidence_kind='observed_contradiction',evidence_code='probe2');req(d['confidence']==x['confidence'],'duplicate_no_double');st=apply_uncertainty_evidence(s,evidence_kind='stale_evidence',evidence_code='stale');req(st['confidence']<s['confidence'] and st['freshness']=='stale','stale_lowers')
for k,v in AUTHORITY_FLAGS.items():req(st.get(k) is v,'auth_'+k)
print(json.dumps({'ok':True,'suite':'v1282.0-2-calibrated-uncertainty-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
