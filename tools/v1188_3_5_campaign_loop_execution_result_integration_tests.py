from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.campaign_loop_execution_result_integration_checkpoint import build_campaign_loop_execution_result_integration_checkpoint
r=build_campaign_loop_execution_result_integration_checkpoint(source_root=ROOT)
print(json.dumps(r,sort_keys=True))
raise SystemExit(0 if r.get("ok") else 1)
