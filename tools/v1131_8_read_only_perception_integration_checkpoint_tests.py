from pathlib import Path
import tempfile
from conscious_agent.read_only_perception_integration_checkpoint import build_read_only_perception_integration_checkpoint
root=Path(tempfile.mkdtemp()); report=build_read_only_perception_integration_checkpoint(root,source_root=Path(__file__).resolve().parents[1]); checks=[report['ok'],report['contract_version']=='v1131.8',len(report['checks'])==12,not report['runtime_mutated'],not report['source_modified'],not report['filesystem_modified'],not report['hidden_reasoning_exposed'],report['desktop_verification']=='pending']
print(f"v1131.8 perception integration checkpoint tests: {sum(checks)}/{len(checks)} passed"); raise SystemExit(0 if all(checks) else 1)
