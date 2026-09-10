from __future__ import annotations
"""v2643 cumulative project start-preflight checkpoint."""
from developer_project_start_preflight_v2640 import build_project_start_preflight
from developer_project_start_review_v2641 import build_project_start_review
from developer_project_start_handoff_v2642 import build_project_start_handoff_candidate

def build_checkpoint()->dict:
 q={'entries':[{'project_id':'p','project_digest':'a'*64,'status':'selected','blockers':[]} ]};rec={'ok':True,'queue':q};ready={'ready_project_ids':['p']};stale={'stale_project_ids':[]};health={'state':'nominal'}
 p=build_project_start_preflight(project_id='p',project_digest='a'*64,recovery=rec,readiness=ready,staleness=stale,verification_health=health);r=build_project_start_review(p);h=build_project_start_handoff_candidate(r)
 checks={'preflight':p.get('eligible_for_operator_start_review') is True,'review':r.get('eligible') is True,'handoff':h.get('ok') is True,'trial_boundary':h.get('next_boundary')=='operator_selected_project_start_trial','no_start':not h.get('project_started'),'no_mutation':not h.get('source_mutation_authorized'),'no_authority':not h.get('authority_granted')}
 return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
