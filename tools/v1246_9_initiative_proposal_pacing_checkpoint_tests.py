from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from initiative_proposal_pacing_checkpoint import build_initiative_proposal_pacing_checkpoint
row=build_initiative_proposal_pacing_checkpoint(source_root=R)
print(json.dumps(row,sort_keys=True));raise SystemExit(0 if row.get('ok') else 1)
