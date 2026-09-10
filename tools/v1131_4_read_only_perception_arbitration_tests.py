from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_signals import ReadOnlyPerceptionSignalStore
from conscious_agent.read_only_perception_candidates import ReadOnlyPerceptionCandidateStore
from conscious_agent.read_only_perception_deliberation_sessions import ReadOnlyPerceptionDeliberationSessionStore
from conscious_agent.read_only_perception_arbitration import ReadOnlyPerceptionArbitrationStore
root=Path(tempfile.mkdtemp()); sig=ReadOnlyPerceptionSignalStore(root); cand=ReadOnlyPerceptionCandidateStore(root); ses=ReadOnlyPerceptionDeliberationSessionStore(root); arb=ReadOnlyPerceptionArbitrationStore(root)
def make(n,cat,**kw):
 r=sig.register(f's{n}',origin_ids=[f'o{n}'],category=cat,importance=.9,uncertainty=.6,structural_digest=f'd{n}',**kw); c=cand.register(f'c{n}',signal_ids=[r['result']['signal_id']],scope_digest=f'scope{n}'); return ses.open(f'x{n}',candidate_id=c['result']['candidate_id'])['session_id']
a=arb.arbitrate('a1',session_id=make(1,'failure'),relevance=.9,importance=.9,uncertainty=.6); b=arb.arbitrate('a2',session_id=make(2,'changed_file',changed_path_digest='p'),relevance=.8,importance=.8); c=arb.arbitrate('a3',session_id=make(3,'system_event'),deliberate_no_perception=True); d=arb.arbitrate('a4',session_id=make(4,'project_state'),false_priority=True); summary=arb.inspection_summary()
checks=[a['outcome']=='failure_review_prioritized',b['outcome']=='changed_file_review_prioritized',c['outcome']=='deliberate_no_perception',d['outcome']=='suppress_false_priority',not summary['filesystem_modified'],not summary['browser_contacted'],not any(summary['authority_boundary'].values())]
print(f"v1131.4 perception arbitration tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
