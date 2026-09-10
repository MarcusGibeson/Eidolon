from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_deliberation_checkpoint import build_read_only_perception_deliberation_checkpoint
root=Path(tempfile.mkdtemp()); report=build_read_only_perception_deliberation_checkpoint(root,source_root=Path(__file__).resolve().parents[1]); checks=[report['ok'],report['contract_version']=='v1131.5',len(report['checks'])==19,not report['runtime_mutated'],not report['source_modified'],not report['filesystem_modified'],not report['hidden_reasoning_exposed'],report['desktop_verification']=='pending']
print(f"v1131.5 perception deliberation checkpoint tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
