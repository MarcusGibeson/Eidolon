from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from bounded_capability_evidence import bounded_float, bounded_int, digest, sealed, valid_seal


def capability_registry(configured: Sequence[Mapping[str, Any]], *, version: str = "1461.9") -> dict[str, Any]:
    rows=[]
    for raw in configured:
        provider=str(raw.get("provider") or "unknown").lower()
        model=str(raw.get("model") or "unknown")
        endpoint=str(raw.get("endpoint") or "")
        caps=sorted({str(x) for x in raw.get("capabilities") or []})
        rows.append({
            "provider":provider,"model":model,"endpoint_digest":digest(endpoint),
            "context_tokens":bounded_int(raw.get("context_tokens"),lo=0,hi=10_000_000),
            "streaming":"stream" in caps or bool(raw.get("streaming")),
            "tools":"tools" in caps or bool(raw.get("tools")),
            "structured_output":"structured_output" in caps or bool(raw.get("structured_output")),
            "embeddings":"embeddings" in caps or bool(raw.get("embeddings")),
            "capabilities":caps,
            "measured_latency_ms":bounded_int(raw.get("latency_ms"),lo=0,hi=600_000),
            "available":bool(raw.get("available", True)),
        })
    rows.sort(key=lambda x:(x["provider"],x["model"]))
    return sealed("provider_capability_registry",{"providers":rows,"count":len(rows),"model_management_performed":False,"provider_contacted":False},version=version)


def native_certification(observations: Mapping[str, Any], *, version: str = "1462.9") -> dict[str, Any]:
    provider=str(observations.get("provider") or "unknown").lower()
    checks={
        "health":bool(observations.get("health_ok")),
        "generation":bool(observations.get("generation_ok")),
        "streaming":bool(observations.get("streaming_ok")),
        "restart":bool(observations.get("restart_ok")),
    }
    if observations.get("embeddings_supported"):
        checks["embeddings"]=bool(observations.get("embeddings_ok"))
    timing={
        "first_token_ms":bounded_int(observations.get("first_token_ms"),hi=600_000),
        "total_ms":bounded_int(observations.get("total_ms"),hi=600_000),
    }
    return sealed("native_provider_certification",{
        "provider":provider,"checks":checks,"passed":sum(checks.values()),"total":len(checks),
        "certified_from_observed_evidence":all(checks.values()),"timing":timing,
        "raw_prompt_or_response_retained":False,"model_management_performed":False,
        "provider_contact_performed_by_this_function":False,
    },version=version)


def task_aware_routing(task: Mapping[str, Any], registry: Mapping[str, Any], preferences: Mapping[str, Any] | None=None, *, version: str = "1463.9") -> dict[str, Any]:
    preferences=dict(preferences or {})
    required=set(str(x) for x in task.get("required_capabilities") or [])
    privacy=str(task.get("privacy") or "local").lower()
    min_context=bounded_int(task.get("context_tokens"),lo=0,hi=10_000_000)
    candidates=[]
    for row in registry.get("payload",{}).get("providers",[]):
        caps=set(row.get("capabilities") or [])
        local_ok = privacy != "local" or str(row.get("provider")) in {"ollama","llama.cpp","llamacpp","local","fixture-local"}
        capability_ok=required.issubset(caps)
        context_ok=int(row.get("context_tokens") or 0)>=min_context
        available=bool(row.get("available"))
        latency=int(row.get("measured_latency_ms") or 0)
        reliability=bounded_float((preferences.get("reliability") or {}).get(row.get("model"),.8),.8)
        preferred=1.0 if row.get("model")==preferences.get("preferred_model") else 0.0
        score=(reliability*.55)+(preferred*.2)+(0.2 if local_ok else -1)+(0.05 if latency and latency<1000 else 0)
        candidates.append({**row,"eligible":available and local_ok and capability_ok and context_ok,"score":round(score,4)})
    eligible=[x for x in candidates if x["eligible"]]
    eligible.sort(key=lambda x:(-x["score"],x["measured_latency_ms"],x["provider"],x["model"]))
    selected=eligible[0] if eligible else None
    return sealed("task_aware_routing",{
        "required_capabilities":sorted(required),"privacy":privacy,"minimum_context_tokens":min_context,
        "candidate_count":len(candidates),"eligible_count":len(eligible),
        "selected_provider":selected.get("provider") if selected else None,"selected_model":selected.get("model") if selected else None,
        "selection_reason":"best_eligible_calibrated_candidate" if selected else "no_eligible_provider",
        "fallback_required":selected is None,
    },version=version)


def construct_context(items: Sequence[Mapping[str, Any]], *, token_budget: int=4096, version: str = "1464.9") -> dict[str, Any]:
    budget=bounded_int(token_budget,lo=128,hi=1_000_000)
    ranked=[]
    for item in items:
        tokens=bounded_int(item.get("tokens"),lo=1,hi=1_000_000)
        relevance=bounded_float(item.get("relevance"),.5)
        freshness=bounded_float(item.get("freshness"),.5)
        evidence=bounded_float(item.get("evidence_quality"),.5)
        score=(relevance*.5)+(freshness*.2)+(evidence*.3)
        ranked.append({"id":str(item.get("id") or ""),"tokens":tokens,"score":round(score,4),"digest":str(item.get("digest") or digest(item.get("id")))})
    ranked.sort(key=lambda x:(-x["score"],x["tokens"],x["id"]))
    selected=[];used=0
    for row in ranked:
        if used+row["tokens"]>budget: continue
        selected.append(row);used+=row["tokens"]
    return sealed("context_construction",{
        "budget_tokens":budget,"used_tokens":used,"selected":selected,"selected_count":len(selected),
        "omitted_count":len(ranked)-len(selected),"full_history_dumped":False,"evidence_ranked":True,
    },version=version)


def structured_output_recovery(raw: str, schema: Mapping[str, Any], *, max_repairs: int=2, version: str = "1465.9") -> dict[str, Any]:
    text=str(raw or "").strip(); attempts=0; value=None; error=""
    candidates=[text]
    if text.startswith("```"):
        body=re.sub(r"^```(?:json)?\s*|\s*```$","",text,flags=re.I|re.S).strip(); candidates.append(body)
    candidates.append(re.sub(r",\s*([}\]])",r"\1",candidates[-1]))
    for candidate in candidates[:max_repairs+1]:
        attempts+=1
        try:
            value=json.loads(candidate); error=""; break
        except Exception as exc: error=type(exc).__name__
    required=[str(x) for x in schema.get("required") or []]
    types=dict(schema.get("types") or {})
    semantic_ok=isinstance(value,dict) and all(k in value for k in required)
    if semantic_ok:
        for key,typename in types.items():
            expected={"string":str,"integer":int,"number":(int,float),"boolean":bool,"object":dict,"array":list}.get(str(typename))
            if expected and key in value and not isinstance(value[key],expected): semantic_ok=False
    return sealed("structured_output_recovery",{
        "parse_succeeded":value is not None,"semantic_valid":semantic_ok,"attempts":attempts,
        "last_error":error,"value_digest":digest(value) if value is not None else None,
        "bounded_repair":attempts<=max_repairs+1,"tool_execution_authorized_from_output":False,
    },version=version)


def streaming_quality(events: Sequence[Mapping[str, Any]], *, cancel_requested: bool=False, version: str = "1466.9") -> dict[str, Any]:
    ordered=sorted(events,key=lambda x:int(x.get("sequence") or 0))
    sequences=[int(x.get("sequence") or 0) for x in ordered]
    duplicate_count=len(sequences)-len(set(sequences))
    visible=[bounded_int(x.get("elapsed_ms"),hi=600_000) for x in ordered if x.get("kind") in {"delta","first_token"}]
    terminal=[x for x in ordered if x.get("kind") in {"done","cancelled","error"}]
    late_results=sum(bool(x.get("late_after_cancel")) for x in ordered)
    tool_requests=[str(x.get("tool_request_id")) for x in ordered if x.get("tool_request_id")]
    return sealed("streaming_quality",{
        "event_count":len(ordered),"first_visible_token_ms":min(visible) if visible else None,
        "duplicate_event_count":duplicate_count,"duplicate_tool_request_count":len(tool_requests)-len(set(tool_requests)),
        "terminal_event_count":len(terminal),"cancel_requested":bool(cancel_requested),"late_results_reconciled":late_results,
        "single_terminal_state":len(terminal)<=1,"stream_integrity":duplicate_count==0 and len(tool_requests)==len(set(tool_requests)) and len(terminal)<=1,
    },version=version)


def provider_recovery(error: Mapping[str, Any], registry: Mapping[str, Any], *, version: str = "1467.9") -> dict[str, Any]:
    kind=str(error.get("kind") or "unknown").lower()
    mapping={
        "unreachable":"check_endpoint_and_provider_process","missing_model":"select_existing_model_or_request_install_separately",
        "timeout":"reduce_context_or_retry_within_budget","unsupported_capability":"route_to_capable_provider",
        "configuration_drift":"revalidate_configuration","malformed_stream":"restart_stream_without_duplicate_turn",
    }
    action=mapping.get(kind,"surface_diagnostic_and_stop")
    available=sum(bool(x.get("available")) for x in registry.get("payload",{}).get("providers",[]))
    return sealed("provider_recovery",{
        "failure_kind":kind,"recommended_action":action,"available_provider_count":available,
        "automatic_model_installation":False,"automatic_model_deletion":False,"duplicate_turn_allowed":False,
        "operator_guidance_required":kind in {"missing_model","configuration_drift","unknown"},
    },version=version)


def quality_calibration(results: Sequence[Mapping[str, Any]], *, version: str = "1468.9") -> dict[str, Any]:
    by_model: dict[str,list[Mapping[str,Any]]]={}
    for row in results: by_model.setdefault(str(row.get("model") or "unknown"),[]).append(row)
    profiles=[]
    for model,rows in sorted(by_model.items()):
        task_scores={}
        for task in {str(x.get("task_class") or "unknown") for x in rows}:
            vals=[bounded_float(x.get("score"),0) for x in rows if str(x.get("task_class") or "unknown")==task]
            task_scores[task]=round(sum(vals)/len(vals),4) if vals else 0.0
        honesty=[bounded_float(x.get("honesty"),1) for x in rows]
        profiles.append({"model":model,"task_scores":task_scores,"honesty":round(sum(honesty)/len(honesty),4),"sample_count":len(rows),"private_examples_retained":False})
    return sealed("quality_calibration",{
        "profiles":profiles,"profile_count":len(profiles),"private_eval_content_exposed":False,"calibration_only":True,
    },version=version)


def resource_policy(machine: Mapping[str, Any], task: Mapping[str, Any], *, version: str = "1469.9") -> dict[str, Any]:
    gaming=bool(machine.get("gaming_or_interactive_load")); memory=bounded_float(machine.get("memory_pressure")); cpu=bounded_float(machine.get("cpu_pressure")); power=str(machine.get("power_mode") or "normal")
    high=gaming or memory>.8 or cpu>.85 or power in {"battery_saver","critical"}
    base_ctx=bounded_int(task.get("desired_context_tokens"),4096,lo=512,hi=1_000_000)
    return sealed("provider_resource_policy",{
        "resource_pressure_high":high,"context_token_budget":max(512,int(base_ctx*(.5 if high else 1))),
        "max_parallel_requests":1 if high else 2,"max_retries":1 if high else 2,"background_work_deferred":high,
        "operator_interactive_load_priority":True,"model_management_performed":False,
    },version=version)


def build_provider_checkpoint(*, registry: Mapping[str,Any], certification: Mapping[str,Any], routing: Mapping[str,Any], context: Mapping[str,Any], structured: Mapping[str,Any], stream: Mapping[str,Any], recovery: Mapping[str,Any], calibration: Mapping[str,Any], resource: Mapping[str,Any], version: str="1470.9") -> dict[str,Any]:
    inputs=[registry,certification,routing,context,structured,stream,recovery,calibration,resource]
    checks={
        "all_evidence_sealed":all(valid_seal(x) for x in inputs),
        "provider_registered":registry.get("payload",{}).get("count",0)>=1,
        "native_evidence_calibrated":certification.get("payload",{}).get("certified_from_observed_evidence") is True,
        "routing_selected":routing.get("payload",{}).get("selected_model") is not None,
        "context_bounded":context.get("payload",{}).get("full_history_dumped") is False,
        "structured_valid":structured.get("payload",{}).get("semantic_valid") is True,
        "stream_integrity":stream.get("payload",{}).get("stream_integrity") is True,
        "recovery_bounded":recovery.get("payload",{}).get("automatic_model_installation") is False,
        "quality_calibrated":calibration.get("payload",{}).get("profile_count",0)>=1,
        "resources_bounded":resource.get("payload",{}).get("max_parallel_requests",0)<=2,
    }
    return sealed("provider_intelligence_checkpoint",{
        "checks":checks,"passed":sum(checks.values()),"total":len(checks),"provider_intelligence_ready":all(checks.values()),
        "model_management_side_effects":False,"provider_contact_authorized":False,
    },version=version)

__all__=["capability_registry","native_certification","task_aware_routing","construct_context","structured_output_recovery","streaming_quality","provider_recovery","quality_calibration","resource_policy","build_provider_checkpoint"]
