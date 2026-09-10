from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_signals import ReadOnlyPerceptionSignalStore
from conscious_agent.read_only_perception_candidates import ReadOnlyPerceptionCandidateStore
from conscious_agent.read_only_perception_intake_checkpoint import build_read_only_perception_intake_checkpoint
root=Path(tempfile.mkdtemp()); s=ReadOnlyPerceptionSignalStore(root); c=ReadOnlyPerceptionCandidateStore(root)
r=s.register('e1',origin_ids=['project:1'],category='project_state',project_id='p1',status_class='healthy',importance=.8,uncertainty=.1); c.register('c1',signal_ids=[r['result']['signal_id']],scope_digest='a'*64)
report=build_read_only_perception_intake_checkpoint(root,source_root=Path(__file__).resolve().parents[1]); checks=[report['ok'],report['contract_version']=='v1131.2',len(report['checks'])==17,not report['runtime_mutated'],not report['source_modified'],not report['raw_file_content_exposed'],not report['filesystem_modified'],report['desktop_verification']=='pending']
print(f"v1131.2 read-only perception intake checkpoint tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
