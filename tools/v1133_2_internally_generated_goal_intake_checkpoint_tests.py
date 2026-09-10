from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.internally_generated_goal_intake_checkpoint import build_internally_generated_goal_intake_checkpoint
ROOT=Path(__file__).resolve().parents[1]
def main():
 with TemporaryDirectory() as d:
  out=build_internally_generated_goal_intake_checkpoint(Path(d),source_root=ROOT)
  assert out['ok'] and len(out['checks'])==17 and not out['runtime_mutated'] and not out['source_modified']
  assert not out['provider_contacted'] and not out['external_action_executed'] and out['desktop_verification']=='pending'
 print('v1133.2: 7/7')
if __name__=='__main__': main()
