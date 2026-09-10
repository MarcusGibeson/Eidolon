from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_signals import ReadOnlyPerceptionSignalStore
from conscious_agent.read_only_perception_candidates import ReadOnlyPerceptionCandidateStore
from conscious_agent.read_only_perception_deliberation_sessions import ReadOnlyPerceptionDeliberationSessionStore
from conscious_agent.read_only_perception_arbitration import ReadOnlyPerceptionArbitrationStore
from conscious_agent.read_only_perception_outcome_lineage import ReadOnlyPerceptionOutcomeLineageStore
root=Path(tempfile.mkdtemp()); s=ReadOnlyPerceptionSignalStore(root); r=s.register('s1',category='failure',origin_ids=['x'],structural_digest='d',importance=.9,uncertainty=.7); sid=r['result']['signal_id']; c=ReadOnlyPerceptionCandidateStore(root); cid=c.register('c1',signal_ids=[sid],scope_digest='scope')['result']['candidate_id']; ds=ReadOnlyPerceptionDeliberationSessionStore(root); sess=ds.open('d1',candidate_id=cid)['session_id']; a=ReadOnlyPerceptionArbitrationStore(root); aid=a.arbitrate('a1',session_id=sess,relevance=.9,importance=.9)['arbitration_id']; o=ReadOnlyPerceptionOutcomeLineageStore(root); out=o.record('o1',arbitration_id=aid); snap=o.inspection_summary(); checks=[out['ok'],snap['contract_version']=='v1131.6',snap['outcome_count']==1,snap['recent_outcomes'][0]['scope_digest']=='scope',not snap['raw_file_content_exposed'],not snap['filesystem_modified']]
print(f"v1131.6 perception outcome lineage tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
