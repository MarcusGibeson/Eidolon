import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from conflict_reconciliation import *
from v1377_test_support import *
P=0
r=assess_campaign_conflicts(campaign_record_digest=C,candidate_digest=A,baseline_source_digest=S0,current_source_digest=S1,baseline_workspace_digest=W0,current_workspace_digest=W1,expected_upstream_digest=U0,current_upstream_digest=U0,owner_session_digest=OWNER,active_session_digests=[OWNER],observed_changes=[change('operator','operator')]);x=r['conflict_assessment'];req(r['ok'],'checkpoint');P+=1
req(x['operator_edit_detected'] and x['apply_guard']=='blocked_reconciliation_required','guard');P+=1
d=prepare_reconciliation_disposition(conflict_assessment=x,expected_assessment_digest=x['assessment_digest'],disposition='reconcile_manually',operator_reviewed=True);req(d['ok'] and d['reconciliation']['manual_reconciliation_required'],'reconcile');P+=1
req(x['content_free'] and x['read_only'],'privacy');P+=1
req(not d['release_authorized'] and not d['independent_authority_granted'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1377-checkpoint'})
