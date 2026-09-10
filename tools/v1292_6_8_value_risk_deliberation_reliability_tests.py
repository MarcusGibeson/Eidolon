from __future__ import annotations
import copy,json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from value_risk_deliberation import deliberate_value_and_risk
from value_risk_deliberation_foundations import DENIED_AUTHORITY
from value_risk_deliberation_reliability import assess_value_risk_deliberation_reliability
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
good=deliberate_value_and_risk([{'proposal_id':'a','proposal_digest':d('a'),'expected_value':90,'risk':20,'reversibility':90,'cost':20,'uncertainty':10,'urgency':80}]);req(assess_value_risk_deliberation_reliability([good])['ok'],'good')
def catch(mut,t):
 x=copy.deepcopy(good);mut(x);r=assess_value_risk_deliberation_reliability([x]);return any(t in v for v in r['violations'])
req(catch(lambda x:x.__setitem__('recommendation_is_priority_mutation',True),'priority_mutation_claim'),'priority')
req(catch(lambda x:x.__setitem__('recommendation_is_authorization',True),'authorization_claim'),'authority_claim')
req(catch(lambda x:x['ranked'][0].__setitem__('blocked',True),'blocked_candidate_recommended'),'blocked')
req(catch(lambda x:x.__setitem__('operator_decision_required',False),'operator_decision_missing'),'operator')
req(catch(lambda x:x.__setitem__('release_authorized',True),'authority_expansion'),'authority_expansion')
r=assess_value_risk_deliberation_reliability([good,good]);req(r['ok'] and r['deliberation_count']==2,'batch');req(r['content_free'] and r['read_only'],'readonly');req(all(r[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1292.6-v1292.8-value-risk-deliberation-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
