from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_signals import ReadOnlyPerceptionSignalStore
from conscious_agent.read_only_perception_candidates import ReadOnlyPerceptionCandidateStore
from conscious_agent.read_only_perception_deliberation_sessions import ReadOnlyPerceptionDeliberationSessionStore
root=Path(tempfile.mkdtemp()); sig=ReadOnlyPerceptionSignalStore(root); cand=ReadOnlyPerceptionCandidateStore(root); sessions=ReadOnlyPerceptionDeliberationSessionStore(root)
r=sig.register('s1',origin_ids=['project-event-1'],category='failure',project_id='p1',importance=.9,uncertainty=.7,structural_digest='d1'); sid=r['result']['signal_id']; c=cand.register('c1',signal_ids=[sid],scope_digest='scope1'); cid=c['result']['candidate_id']; opened=sessions.open('o1',candidate_id=cid,deliberation_budget=3); reused=sessions.open('o2',candidate_id=cid); snap=sessions.snapshot(); summary=sessions.inspection_summary()
r2=sig.register('s2',origin_ids=['change-1'],category='changed_file',changed_path_digest='abc',importance=.8,sensitivity=.9,structural_digest='d2'); c2=cand.register('c2',signal_ids=[r2['result']['signal_id']],scope_digest='scope2'); paused=sessions.open('o3',candidate_id=c2['result']['candidate_id'],active_conversation_sensitive=True)
checks=[opened['state']=='open',reused['status']=='perception_deliberation_session_reused',len(snap['sessions'])==1,paused['state']=='paused',summary['raw_file_content_exposed'] is False,not any(summary['authority_boundary'].values()),summary['recent_sessions'][0]['scope_digest']=='scope1']
print(f"v1131.3 perception deliberation sessions tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
