from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from independent_improvement_proposals import generate_improvement_proposals
from value_risk_deliberation import deliberate_value_and_risk,alternatives_from_improvement_proposals
from value_risk_deliberation_foundations import DENIED_AUTHORITY
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
def d(s):return sha256(s.encode()).hexdigest()
def obs(kind,name,impact):return {'kind':kind,'issue_digest':d('i'+name),'evidence_digest':d('e'+name),'relevance':90,'impact':impact,'confidence':90,'actionability':90,'novel':True,'fresh':True,'private':False}
p=generate_improvement_proposals([obs('defect','reliability',95),obs('maintainability','cleanup',70),obs('accessibility','a11y',85)]);ids={x['kind']:x['proposal_id'] for x in p['proposals']};e={ids['defect']:{'expected_value':95,'risk':25,'reversibility':85,'cost':35,'uncertainty':15,'urgency':90},ids['maintainability']:{'expected_value':65,'risk':20,'reversibility':90,'cost':40,'uncertainty':20,'urgency':30},ids['accessibility']:{'expected_value':85,'risk':30,'reversibility':75,'cost':55,'uncertainty':35,'urgency':60}}
alts=alternatives_from_improvement_proposals(p,e);req(len(alts)==3,'proposal_bridge');r=deliberate_value_and_risk(alts);req(r['disposition']=='recommend_for_operator_review','recommend');req(r['recommended_proposal_id']==ids['defect'],'highest_value_selected');req(r['operator_decision_required'],'operator_required');req(r['recommendation_is_priority_mutation'] is False and r['recommendation_is_authorization'] is False,'not_mutation_or_authority');req(r['comparisons'] and all(x['reason_codes'] for x in r['comparisons']),'explainable_comparisons')
blocked=deliberate_value_and_risk([{'proposal_id':'x','proposal_digest':d('x'),'expected_value':100,'risk':90,'reversibility':10,'cost':10,'uncertainty':10,'urgency':100,'critical_risk':True}]);req(blocked['disposition']=='defer_no_viable_candidate' and not blocked['recommended_proposal_id'],'critical_risk_defers')
amb=deliberate_value_and_risk([{'proposal_id':'a','proposal_digest':d('a'),'expected_value':80,'risk':25,'reversibility':80,'cost':30,'uncertainty':60,'urgency':60},{'proposal_id':'b','proposal_digest':d('b'),'expected_value':80,'risk':25,'reversibility':80,'cost':30,'uncertainty':60,'urgency':59}],ambiguity_margin=3);req(amb['disposition']=='defer_ambiguous_tradeoff','ambiguous_defer')
low=deliberate_value_and_risk([{'proposal_id':'l','proposal_digest':d('l'),'expected_value':20,'risk':80,'reversibility':20,'cost':80,'uncertainty':70,'urgency':10}],minimum_score=15);req(low['disposition']=='defer_no_viable_candidate','low_value_defer');req(all(r[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1292.3-v1292.5-value-risk-deliberation-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
