from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):sys.path.insert(0,str(p)) if str(p) not in sys.path else None
from unified_operator_dashboard_checkpoint import build_unified_operator_dashboard_checkpoint
x=build_unified_operator_dashboard_checkpoint(source_root=R);print(json.dumps({'ok':x['ok'],'passed':x['passed'],'total':x['total'],'status':x['status']},sort_keys=True));raise SystemExit(0 if x['ok'] else 1)
