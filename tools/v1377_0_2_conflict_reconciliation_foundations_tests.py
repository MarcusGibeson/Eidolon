import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from conflict_reconciliation import *
from v1377_test_support import *
P=0
r=assess_campaign_conflicts(campaign_record_digest=C,candidate_digest=A,baseline_source_digest=S0,current_source_digest=S0,baseline_workspace_digest=W0,current_workspace_digest=W0,expected_upstream_digest=U0,current_upstream_digest=U0,owner_session_digest=OWNER,active_session_digests=[OWNER],observed_changes=[change('owned')]);req(r['ok'],'assessment');P+=1
x=r['conflict_assessment'];req(not x['conflict_detected'] and x['apply_guard']=='clear_no_conflict_observed','clear');P+=1
req(x['campaign_owned_change_count']==1 and x['operator_change_count']==0,'classification');P+=1
req(x['content_free'] and not x['raw_paths_persisted'] and not x['raw_content_persisted'],'privacy');P+=1
req(not r['application_authorized'] and not r['project_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1377-foundations'})
