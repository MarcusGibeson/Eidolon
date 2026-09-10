from pathlib import Path
import tempfile
from tools.v1108_6_surfaced_initiative_reconciliation_tests import run as prior_run

def run():
 root=Path(tempfile.mkdtemp())/'cognition'
 from conscious_agent.initiative_response_reconciliation import InitiativeResponseReconciliationStore
 from conscious_agent.surfaced_initiative_reconciliation import SurfacedInitiativeReconciliationStore
 from conscious_agent.json_storage import write_json_atomic
 s=SurfacedInitiativeReconciliationStore(root); st=s._load(); st['receipts']=[{'receipt_id':'surf-1','proposal_id':'p1','outcome':'shown','active':True}]; write_json_atomic(s.path,st,expected_type=dict,sort_keys=True)
 r=InitiativeResponseReconciliationStore(root); a=r.reconcile('r1',surface_receipt_id='surf-1',outcome='acknowledged',explicit_user_signal=True); dup=r.reconcile('r1',surface_receipt_id='surf-1',outcome='dismissed',explicit_user_signal=True); locked=r.reconcile('r2',surface_receipt_id='surf-1',outcome='dismissed',explicit_user_signal=True); missing=r.reconcile('r3',surface_receipt_id='none',outcome='acknowledged',explicit_user_signal=True)
 checks=[a['status']=='acknowledged',a['outcome']['terminal'] is True,dup['idempotent'] is True,locked['status']=='acknowledged',missing['status']=='retired',r.inspection_summary()['automatic_retry'] is False]
 print('v1108.7',sum(checks),'/',len(checks)); return all(checks)
if __name__=='__main__': raise SystemExit(0 if run() else 1)
