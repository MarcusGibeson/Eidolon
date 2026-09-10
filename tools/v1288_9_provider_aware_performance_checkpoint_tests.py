from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from provider_aware_performance_checkpoint import provider_aware_performance_checkpoint
c=provider_aware_performance_checkpoint(ROOT); checks=[c['ok'],c['contract_version']=='v1288.9',c['status']=='provider_aware_performance_checkpoint_ready',c['next']=='v1289 Product Quality Judgment',c['v1289_started'] is True,c['checks']['v1289_transition_coherent'],c['checks']['provider_neutral'],c['checks']['configured_limits_are_ceilings'],c['checks']['mandatory_verification_preserved'],c['checks']['no_automatic_provider_or_model_switch'],c['checks']['native_windows_provider_validation_pending'],c['read_only']]
out={'suite':'v1288.9-provider-aware-performance-checkpoint','ok':all(checks),'passed':sum(bool(x) for x in checks),'failed':sum(not bool(x) for x in checks)}; print(json.dumps(out,sort_keys=True)); raise SystemExit(0 if out['ok'] else 1)
