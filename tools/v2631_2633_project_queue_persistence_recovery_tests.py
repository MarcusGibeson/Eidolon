from pathlib import Path
import tempfile, json
from conscious_agent.developer_project_queue_persistence_v2631 import persist_project_queue_state
from conscious_agent.developer_project_queue_recovery_v2632 import recover_project_queue_state
from conscious_agent.developer_project_queue_operator_review_v2633 import build_recovered_queue_operator_review

def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  q={'entries':[{'project_id':'p','project_digest':'a'*64,'status':'selected','depends_on':[],'blockers':[]}],'queue_digest':'q'*64};r={'ready_project_ids':['p'],'queue_digest':'q'*64,'readiness_digest':'r'*64};h={'transitions':[],'history_digest':'h'*64}
  p=persist_project_queue_state(queue=q,readiness=r,history=h,runtime_root=td); checks += [p['ok'],p['runtime_only'],not p['source_mutated'],not p['authority_granted']]
  rec=recover_project_queue_state(runtime_root=td); checks += [rec['ok'],not rec['operator_review_required'],not rec['automatic_repair_permitted'],rec['queue_digest']=='q'*64]
  review=build_recovered_queue_operator_review(rec); checks += [review['project_count']==1,review['operator_review_required'],review['content_minimized'],not review['authority_granted']]
  Path(td,'developer_project_queue.json').write_text('{bad',encoding='utf-8'); bad=recover_project_queue_state(runtime_root=td); checks += [not bad['ok'],bad['operator_review_required']]
 print(json.dumps({'ok':all(checks),'passed':sum(bool(x) for x in checks),'total':len(checks)})); return 0 if all(checks) else 1
if __name__=='__main__': raise SystemExit(main())
