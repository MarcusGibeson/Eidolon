from pathlib import Path
import tempfile,json
from conscious_agent.developer_project_queue_snapshot_v2635 import commit_project_queue_snapshot
from conscious_agent.developer_project_queue_snapshot_recovery_v2636 import recover_committed_project_queue_snapshot
from conscious_agent.developer_project_queue_operator_review_v2633 import build_recovered_queue_operator_review
from conscious_agent.developer_project_queue_review_decision_v2637 import build_project_queue_review_decision
checks=[]
with tempfile.TemporaryDirectory() as td:
 q={'entries':[{'project_id':'x','project_digest':'a'*64,'status':'review'}],'queue_digest':'q'*64};r={'ready_project_ids':[],'queue_digest':'q'*64};h={'transitions':[]}
 c=commit_project_queue_snapshot(queue=q,readiness=r,history=h,runtime_root=td,generation=7);checks += [c['ok'],c['committed'],not c['authority_granted']]
 rec=recover_committed_project_queue_snapshot(runtime_root=td);checks += [rec['ok'],rec['generation']==7,not rec['operator_review_required']]
 review=build_recovered_queue_operator_review(rec);d=build_project_queue_review_decision(review=review,decision='acknowledge',operator_selection_digest='b'*64);checks += [d['ok'],not d['decision_applied'],not d['project_started'],not d['authority_granted']]
 Path(td,'developer_project_queue_snapshots','7','queue.json').write_text('{}',encoding='utf-8');bad=recover_committed_project_queue_snapshot(runtime_root=td);checks += [not bad['ok'],bad['operator_review_required'],'queue_digest_mismatch' in bad['failure_reasons']]
print(json.dumps({'ok':all(checks),'passed':sum(bool(x) for x in checks),'total':len(checks)}));raise SystemExit(0 if all(checks) else 1)
