from __future__ import annotations
from developer_project_rehearsal_history_v2660 import build_rehearsal_history
from developer_project_rehearsal_comparison_v2665 import compare_project_rehearsals
from developer_project_rehearsal_drift_v2666 import build_rehearsal_drift_review

def build_checkpoint()->dict:
 h=build_rehearsal_history([{'project_id':'p','project_digest':'a'*64,'state':'nominal','scenario_count':2,'failure_modes':[]},{'project_id':'p','project_digest':'a'*64,'state':'attention','scenario_count':3,'failure_modes':['x']}]);c=compare_project_rehearsals(h,'p');d=build_rehearsal_drift_review(c)
 checks={'history':h['ok'],'comparison':c['ok'],'two_rehearsals':c['rehearsal_count']==2,'drift_visible':c['trend'] in {'worsening','unstable'},'review_required':d['operator_review_required'],'synthetic_only':d['synthetic_evidence_only'],'no_strategy_mutation':not d['real_strategy_weights_mutated'],'no_start':not d['project_started'],'no_authority':not d['authority_granted']}
 return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
