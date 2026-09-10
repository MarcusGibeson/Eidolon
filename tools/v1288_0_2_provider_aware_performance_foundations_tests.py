from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from provider_aware_performance_foundations import AUTHORITY_FLAGS, build_provider_aware_performance_plan, public_provider_aware_performance_plan

checks=[]
def ck(name,v): checks.append((name,bool(v)))

def plan(**kw):
    base=dict(configured_context_window=8192,configured_max_tokens=350,configured_read_timeout_seconds=120,configured_retry_limit=2,streaming_requested=False)
    base.update(kw); return build_provider_aware_performance_plan(**base)

p=plan(); ck('contract',p['contract_version']=='v1288.2'); ck('context_kept',p['effective_context_window']==8192); ck('max_ceiling',p['effective_max_tokens']<=350); ck('timeout_ceiling',p['effective_read_timeout_seconds']<=120); ck('retry_ceiling',p['effective_retry_limit']<=2)
small=plan(configured_context_window=1024,configured_max_tokens=900); ck('small_output_cap',small['effective_max_tokens']==128); ck('small_input_positive',small['input_budget_tokens']>=256)
obs=plan(configured_context_window=16384,observed_context_window=4096); ck('observed_context_caps',obs['effective_context_window']==4096); ck('observed_never_expands',obs['effective_context_window']<=obs['configured_context_window'])
low=plan(latency_tier='low'); ck('low_timeout_reduced',low['effective_read_timeout_seconds']==78.0); ck('low_retry_bounded',low['effective_retry_limit']==1)
medium=plan(latency_tier='medium'); ck('medium_timeout_reduced',medium['effective_read_timeout_seconds']==102.0)
high=plan(latency_tier='high'); ck('high_timeout_ceiling',high['effective_read_timeout_seconds']==120.0); ck('high_retry_zero',high['effective_retry_limit']==0); ck('high_verification_batched_not_skipped','keep_all_mandatory_gates' in high['verification_cadence'])
stream=plan(streaming_requested=True,streaming_support='supported'); ck('stream_eligible',stream['streaming_eligible']); ck('stream_strategy',stream['generation_strategy']=='bounded_streaming'); ck('stream_retry_zero',stream['effective_retry_limit']==0)
unsupported=plan(streaming_requested=True,streaming_support='unsupported'); ck('unsupported_not_streaming',not unsupported['streaming_eligible']); ck('unsupported_strategy',unsupported['generation_strategy']=='bounded_non_streaming'); ck('same_provider_transport_fallback','same_provider_non_streaming' in unsupported['transport_fallback']); ck('fallback_no_provider_switch',not unsupported['fallback_changes_provider']); ck('fallback_no_model_switch',not unsupported['fallback_changes_model'])
unavailable=plan(health_state='unavailable'); ck('unavailable_operator_review',unavailable['transport_fallback']=='operator_review_provider_or_configuration'); ck('unavailable_provider_independent_verification',unavailable['verification_cadence'].startswith('provider_independent'))
degraded=plan(health_state='degraded'); ck('degraded_optional_context_first',degraded['transport_fallback'].startswith('degrade_optional_context'))
for k,v in AUTHORITY_FLAGS.items(): ck('authority_'+k, v is False and p[k] is False)
ck('verification_never_skippable',p['mandatory_verification_may_be_skipped'] is False)
ck('provider_name_not_behavior',p['provider_name_drives_behavior'] is False); ck('model_name_not_behavior',p['model_name_drives_behavior'] is False)
pub=public_provider_aware_performance_plan(p); ck('public_content_free',pub['content_free'] is True); ck('public_no_configured_raw','configured_context_window' not in pub); ck('digest_present',len(pub['plan_digest'])==64)
failed=[n for n,v in checks if not v]; out={'suite':'v1288.0-v1288.2-provider-aware-performance-foundations','ok':not failed,'passed':len(checks)-len(failed),'failed':len(failed),'failed_checks':failed}; print(json.dumps(out,sort_keys=True)); raise SystemExit(0 if out['ok'] else 1)
