from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.revisable_world_model_integration_checkpoint import build_revisable_world_model_integration_checkpoint
ROOT=Path(__file__).resolve().parents[1]
with TemporaryDirectory() as td:
 out=build_revisable_world_model_integration_checkpoint(Path(td),source_root=ROOT); assert out['ok']; assert len(out['checks'])==14; assert not out['runtime_mutated'] and not out['source_modified']; assert not out['external_action_executed']
print('v1132.8 5/5')
