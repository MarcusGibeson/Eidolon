from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from provider_fallback_model_governance_checkpoint import build_provider_fallback_model_governance_checkpoint
x=build_provider_fallback_model_governance_checkpoint(source_root=R)
print(json.dumps({'ok':x['ok'],'passed':x['passed'],'total':x['total'],'status':x['status']},sort_keys=True));raise SystemExit(0 if x['ok'] else 1)
