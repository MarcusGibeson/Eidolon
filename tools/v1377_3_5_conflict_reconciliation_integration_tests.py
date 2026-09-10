import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from conflict_reconciliation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1377_test_support import *
P=0
r=assess_campaign_conflicts(campaign_record_digest=C,candidate_digest=A,baseline_source_digest=S0,current_source_digest=S1,baseline_workspace_digest=W0,current_workspace_digest=W1,expected_upstream_digest=U0,current_upstream_digest=U1,owner_session_digest=OWNER,active_session_digests=[OWNER,OTHER],observed_changes=[change('operator','operator'),change('remote','upstream'),change('other','other_session')]);req(r['ok'],'assessment');P+=1
x=r['conflict_assessment'];req(x['conflict_detected'] and x['operator_edit_detected'] and x['upstream_drift_detected'] and x['competing_session_detected'],'detect');P+=1
d=prepare_reconciliation_disposition(conflict_assessment=x,expected_assessment_digest=x['assessment_digest'],disposition='rebuild_candidate',operator_reviewed=True);req(d['ok'] and d['reconciliation']['candidate_requires_rebuild'],'disposition');P+=1
c=process_ordinary_chat_development_turn('show conflict reconciliation',project_state={'conflict_reconciliation':x});req(c.get('active') and c.get('ok'),'chat');P+=1
req(not c['action_executed'] and not c['source_mutation_authorized'],'no execute');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1377-integration'})
