from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from feature_freeze_final_hardening_checkpoint import build_feature_freeze_final_hardening_checkpoint
row=build_feature_freeze_final_hardening_checkpoint(source_root=R)
print(json.dumps({'ok':row['ok'],'passed':row['passed'],'total':row['total'],'internal':row},sort_keys=True));raise SystemExit(0 if row['ok'] else 1)
