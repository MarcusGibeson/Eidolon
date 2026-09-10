from __future__ import annotations
from developer_project_rehearsal_history_v2660 import build_rehearsal_history
from developer_project_evidence_firewall_v2661 import classify_project_outcome_evidence
from developer_project_rehearsal_review_v2662 import build_rehearsal_learning_review

def build_checkpoint()->dict:
 h=build_rehearsal_history([{'project_id':'p','project_digest':'a'*64,'simulation_health_state':'attention','scenario_count':3,'failure_modes':['x']}]);f=classify_project_outcome_evidence({'synthetic_evidence_only':True});r=build_rehearsal_learning_review(h)
 checks={'history':h['ok'],'synthetic_lane':f['evidence_lane']=='synthetic_rehearsal','not_real_learning':not f['eligible_for_real_strategy_learning'],'no_promotion':not f['automatic_promotion_between_lanes_permitted'],'review':r['ok'],'no_real_lesson':not r['durable_real_strategy_lesson_committed'],'no_strategy_mutation':not r['real_strategy_weights_mutated'],'no_authority':not r['authority_granted']}
 return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
