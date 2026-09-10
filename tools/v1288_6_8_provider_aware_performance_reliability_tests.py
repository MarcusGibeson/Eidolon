from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from provider_aware_performance_foundations import build_provider_aware_performance_plan
from provider_aware_performance_reliability import assess_provider_aware_performance_reliability
checks=[]
def ck(n,v): checks.append((n,bool(v)))
base=dict(configured_context_window=8192,configured_max_tokens=350,configured_read_timeout_seconds=120,configured_retry_limit=1)
plans=[build_provider_aware_performance_plan(**base,streaming_requested=False,latency_tier=t,health_state=h,streaming_support=s) for t,h,s in [('low','ready','supported'),('medium','degraded','server_dependent'),('high','ready','supported'),('unknown','unavailable','unknown')]]
r=assess_provider_aware_performance_reliability(plans); ck('healthy',r['ok']); ck('no_violations',r['violation_count']==0); ck('ceilings',r['operator_configuration_ceiling_preserved']); ck('verification',r['mandatory_verification_preserved']); ck('switching',r['provider_model_switching_absent']); ck('name_neutral',r['name_specific_product_behavior_absent']); ck('authority',r['authority_preserved']); ck('read_only',r['read_only'])
bad=dict(plans[0]); bad['effective_max_tokens']=9999; rb=assess_provider_aware_performance_reliability([bad]); ck('detect_expansion',not rb['ok'] and any('output_expanded' in x for x in rb['violations']))
bad2=dict(plans[0]); bad2['mandatory_verification_may_be_skipped']=True; rb2=assess_provider_aware_performance_reliability([bad2]); ck('detect_verification_weakening',not rb2['ok'])
bad3=dict(plans[0]); bad3['fallback_changes_model']=True; rb3=assess_provider_aware_performance_reliability([bad3]); ck('detect_hidden_switch',not rb3['ok'])
failed=[n for n,v in checks if not v]; out={'suite':'v1288.6-v1288.8-provider-aware-performance-reliability','ok':not failed,'passed':len(checks)-len(failed),'failed':len(failed),'failed_checks':failed}; print(json.dumps(out,sort_keys=True)); raise SystemExit(0 if out['ok'] else 1)
