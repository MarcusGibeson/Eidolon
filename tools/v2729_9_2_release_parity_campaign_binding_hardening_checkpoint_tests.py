import json
from conscious_agent.release_parity_campaign_binding_checkpoint_v2729_9_2 import build_checkpoint
r = build_checkpoint()
print(json.dumps(r, sort_keys=True))
raise SystemExit(0 if r['ok'] else 1)
