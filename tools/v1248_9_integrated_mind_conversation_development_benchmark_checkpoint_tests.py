from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from integrated_mind_conversation_development_benchmark_checkpoint import build_integrated_mind_conversation_development_benchmark_checkpoint
row=build_integrated_mind_conversation_development_benchmark_checkpoint(source_root=R)
print(json.dumps({'ok':row.get('ok') is True,'passed':row.get('passed',0),'total':row.get('total',0),'internal':row},sort_keys=True));raise SystemExit(0 if row.get('ok') else 1)
