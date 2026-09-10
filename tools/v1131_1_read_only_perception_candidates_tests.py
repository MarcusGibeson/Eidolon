import tempfile
from conscious_agent.read_only_perception_signals import ReadOnlyPerceptionSignalStore
from conscious_agent.read_only_perception_candidates import ReadOnlyPerceptionCandidateStore
root=tempfile.mkdtemp(); s=ReadOnlyPerceptionSignalStore(root); c=ReadOnlyPerceptionCandidateStore(root)
r=s.register('e1',origin_ids=['failure:1'],category='failure',project_id='p1',event_class='test_failure',status_class='open',importance=.9,uncertainty=.4)
sid=r['result']['signal_id']; a=c.register('c1',signal_ids=[sid],perception_purpose='failure_review',scope_digest='a'*64,semantic_overlap_key='failure:p1'); b=c.register('c2',signal_ids=[sid],perception_purpose='failure_review',scope_digest='a'*64,semantic_overlap_key='failure:p1'); rows=c.snapshot()['candidates']; checks=[a['result']['state']=='active',b['status']=='duplicate_candidate_ignored',len(rows)==1,rows[0]['categories']==['failure'],not c.inspection_summary()['filesystem_modified'],not any(c.inspection_summary()['authority_boundary'].values())]
print(f"v1131.1 read-only perception candidates tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
