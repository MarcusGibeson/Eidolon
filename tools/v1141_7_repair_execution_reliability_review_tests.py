from pathlib import Path
import tempfile
from conscious_agent.repair_execution_reliability_review import RepairExecutionReliabilityReviewStore
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 s=RepairExecutionReliabilityReviewStore(Path(td)/'cognition')
 r=s.review('evt-1')
 check('review succeeds',r['ok'] and r['finding']=='insufficient_evidence')
 check('idempotent retry',s.review('evt-1')['idempotent'])
 c=s.review('evt-2',workspace_contamination_digests=['abc'])
 check('contamination structural',c['finding']=='contamination_detected')
 i=s.inspection_summary()
 check('evidence only',i['operator_candidate_evidence_only'] and not i['installation_eligible'])
 check('authority separation',not i['approval_created'] and not i['authorization_created'] and not i['promotion_created'] and not i['certification_created'])
 check('privacy',not i['patch_text_exposed'] and not i['commands_exposed'] and not i['logs_exposed'] and not i['hidden_reasoning_exposed'])
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
