from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_signals import ReadOnlyPerceptionSignalStore
root=Path(tempfile.mkdtemp()); s=ReadOnlyPerceptionSignalStore(root)
a=s.register('e1',origin_ids=['work:1'],category='completed_work',project_id='p1',event_class='completed',status_class='verified',importance=.8,uncertainty=.1,structural_digest='a'*64)
b=s.register('e2',origin_ids=['file:1'],category='changed_file',project_id='p1',changed_path_digest='b'*64,change_kind='modified',importance=.7,uncertainty=.2)
c=s.register('e3',origin_ids=['novel:1'],category='system_event',novelty_only=True,importance=.9)
d=s.register('e1',origin_ids=['work:1'],category='completed_work',importance=.8)
rows=s.snapshot()['signals']; checks=[a['result']['state']=='active',b['result']['state']=='active',c['result']['state']=='suppressed',d['idempotent'],len(rows)==3,not s.inspection_summary()['raw_file_content_exposed'],not any(s.inspection_summary()['authority_boundary'].values())]
print(f"v1131.0 read-only perception signals tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
