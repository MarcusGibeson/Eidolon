from __future__ import annotations
from developer_portfolio_rehearsal_risk_v2668 import annotate_portfolio_rehearsal_risk
from developer_portfolio_rehearsal_review_v2669 import build_portfolio_rehearsal_review
from developer_portfolio_rehearsal_sensitivity_v2670 import build_rehearsal_selection_sensitivity

def build_checkpoint()->dict:
 c=[{'project_id':'a','project_digest':'a'*64,'operator_priority':1.0},{'project_id':'b','project_digest':'b'*64,'operator_priority':.8}];comps={'a':{'trend':'stable','failure_counts':[0,0]},'b':{'trend':'worsening','failure_counts':[0,2]}};a=annotate_portfolio_rehearsal_risk(c,comps);r=build_portfolio_rehearsal_review(a);s=build_rehearsal_selection_sensitivity(a,r)
 checks={'annotations':a['ok'],'elevated':'b' in r['elevated_risk_project_ids'],'review':r['operator_review_required'],'fragile':s['state']=='fragile','selection_required':s['operator_selection_still_required'],'priority_preserved':not r['operator_priority_overridden'],'no_reorder':not a['portfolio_order_changed'],'no_auto_select':not s['automatic_project_selection_permitted'],'no_authority':not s['authority_granted']}
 return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
