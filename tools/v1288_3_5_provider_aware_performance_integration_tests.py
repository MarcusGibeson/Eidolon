from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent'))
from local_model import LocalModelConfig, GenerationSettings
from provider_aware_performance import build_configured_provider_performance_plan, apply_provider_aware_performance_config, provider_aware_performance_prompt, provider_aware_performance_authority

checks=[]
def ck(n,v): checks.append((n,bool(v)))
config=LocalModelConfig(provider='ollama',endpoint='http://localhost:11434',model='arbitrary-model-a',embed_model='embed',context_size=2048,read_timeout_seconds=100,retry_limit=3,generation=GenerationSettings(max_tokens=600)).validated()
cap={'streaming':{'support':'supported'}}
p=build_configured_provider_performance_plan(config,streaming_requested=True,capability_evidence=cap,performance_evidence={'latency_tier':'high','observed_context_window':1536})
adapted=apply_provider_aware_performance_config(config,p)
ck('context_adapted',adapted.context_size==1536); ck('output_adapted',adapted.generation.max_tokens==192); ck('timeout_not_expanded',adapted.read_timeout_seconds<=config.read_timeout_seconds); ck('retry_adapted',adapted.retry_limit==0); ck('original_immutable',config.context_size==2048 and config.generation.max_tokens==600 and config.retry_limit==3)
# Model labels do not enter the policy inputs or alter the plan.
config_b=LocalModelConfig(provider='ollama',endpoint='http://localhost:11434',model='completely-different-label',embed_model='embed',context_size=2048,read_timeout_seconds=100,retry_limit=3,generation=GenerationSettings(max_tokens=600)).validated()
pb=build_configured_provider_performance_plan(config_b,streaming_requested=True,capability_evidence=cap,performance_evidence={'latency_tier':'high','observed_context_window':1536})
for key in ('effective_context_window','effective_max_tokens','effective_read_timeout_seconds','effective_retry_limit','generation_strategy','verification_cadence','transport_fallback'):
    ck('name_neutral_'+key,p[key]==pb[key])
unsupported=build_configured_provider_performance_plan(config,streaming_requested=True,capability_evidence={'streaming':{'support':'unsupported'}}); ck('capability_drives_strategy',unsupported['generation_strategy']=='bounded_non_streaming')
prompt=provider_aware_performance_prompt(p); ck('prompt_has_strategy','bounded_streaming' in prompt); ck('prompt_preserves_verification','mandatory verification' in prompt); ck('prompt_no_model_label','arbitrary-model-a' not in prompt)
for k,v in provider_aware_performance_authority().items(): ck('authority_'+k,v is False)
source=(ROOT/'conscious_agent/conversation_runtime.py').read_text(encoding='utf-8')
ck('runtime_import','build_configured_provider_performance_plan' in source); ck('runtime_applies_config',source.count('apply_provider_aware_performance_config(config, provider_performance_plan)')==2); ck('runtime_capabilities',source.count('provider_capabilities(config.provider)')==2); ck('runtime_prompt',source.count('provider_aware_performance_prompt(provider_performance_plan)')==2); ck('runtime_public_projection',source.count('public_provider_aware_performance_plan(provider_performance_plan)')==2); ck('runtime_sync_mode','streaming_requested=False' in source); ck('runtime_stream_mode','streaming_requested=True' in source)
failed=[n for n,v in checks if not v]; out={'suite':'v1288.3-v1288.5-provider-aware-performance-integration','ok':not failed,'passed':len(checks)-len(failed),'failed':len(failed),'failed_checks':failed}; print(json.dumps(out,sort_keys=True)); raise SystemExit(0 if out['ok'] else 1)
