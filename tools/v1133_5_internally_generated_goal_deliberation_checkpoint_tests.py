from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.internally_generated_goal_deliberation_checkpoint import build_internally_generated_goal_deliberation_checkpoint
def main():
 with tempfile.TemporaryDirectory() as td:
  out=build_internally_generated_goal_deliberation_checkpoint(Path(td),source_root=ROOT); assert out['ok'] and len(out['checks'])==21; assert not out['runtime_mutated'] and not out['source_modified']
 assert out['desktop_verification']=='pending' and not out['provider_contacted'] and not out['external_action_executed']
 print('v1133.5 internally generated goal deliberation checkpoint: 3/3 passed')
if __name__=='__main__': main()
