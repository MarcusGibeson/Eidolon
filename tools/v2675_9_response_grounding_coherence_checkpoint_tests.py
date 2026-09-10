import json
from conscious_agent.response_grounding_checkpoint_v2675 import build_checkpoint
r=build_checkpoint();print(json.dumps(r));raise SystemExit(0 if r['ok'] else 1)
