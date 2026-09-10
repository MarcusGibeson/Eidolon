import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from conflict_reconciliation import *
from v1377_test_support import *
P=0
base=dict(campaign_record_digest=C,candidate_digest=A,baseline_source_digest=S0,current_source_digest=S0,baseline_workspace_digest=W0,current_workspace_digest=W0,expected_upstream_digest=U0,current_upstream_digest=U0,owner_session_digest=OWNER)
req(not assess_campaign_conflicts(**{**base,'campaign_record_digest':'bad'})['ok'],'lineage');P+=1
req(not assess_campaign_conflicts(**base,active_session_digests=['bad'])['ok'],'session');P+=1
req(not assess_campaign_conflicts(**base,observed_changes=[{'path_digest':'bad','change_digest':D('x'),'origin':'operator','kind':'modified'}])['ok'],'change');P+=1
x=assess_campaign_conflicts(**{**base,'current_workspace_digest':W1})['conflict_assessment'];req(x['stale_worktree_detected'] and x['conflict_detected'],'stale worktree');P+=1
x2=assess_campaign_conflicts(**base,active_session_digests=[OWNER,OTHER])['conflict_assessment'];req(x2['competing_session_detected'],'competing');P+=1
t=dict(x2);t['operator_change_count']=99;req(not prepare_reconciliation_disposition(conflict_assessment=t,expected_assessment_digest=x2['assessment_digest'],disposition='defer',operator_reviewed=True)['ok'],'tamper');P+=1
req(not prepare_reconciliation_disposition(conflict_assessment=x2,expected_assessment_digest=x2['assessment_digest'],disposition='rebuild_candidate',operator_reviewed=False)['ok'],'review');P+=1
print({'ok':P==7,'passed':P,'total':7,'suite':'v1377-reliability'})
