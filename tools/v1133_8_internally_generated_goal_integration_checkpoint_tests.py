from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.internally_generated_goal_integration_checkpoint import build_internally_generated_goal_integration_checkpoint
ROOT=Path(__file__).resolve().parents[1]
with TemporaryDirectory() as td:
 out=build_internally_generated_goal_integration_checkpoint(Path(td),source_root=ROOT); assert out['ok']; assert len(out['checks'])==15; assert not out['runtime_mutated'] and not out['source_modified']; assert not out['external_action_executed'] and not out['raw_content_exposed']
print('v1133.8 checks: 6/6')
