from __future__ import annotations

"""Integrated read-only runtime efficiency benchmark for v1253.9.1.

The benchmark separates fresh-data startup, established-runtime startup, Python
process startup, incremental conversation-runtime import cost, and a first real
message path with a zero-latency fake provider. Temporary runtimes are scoped
and removed after measurement. No real provider is contacted.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from performance_regression import summarize_samples
from hermetic_verification_runtime import run_bounded_command
from response_time_runtime import build_compact_cognitive_projection, trusted_action_acknowledgement
from dashboard_fast_status import build_fast_runtime_status
from persistent_state_performance import benchmark_persistent_state_scaling
from performance_baseline import coarse_host_profile, load_same_host_baseline

CONTRACT_VERSION = "v1253.8"
RUNTIME_REPAIR_VERSION = "v1253.9.1"
BENCHMARK_SUBPROCESS_TIMEOUT_SECONDS = 30.0


def _timed_ms(fn: Callable[[], Any], repeat: int = 9) -> tuple[dict[str, Any], Any]:
    samples=[]; value=None
    for _ in range(max(1, repeat)):
        start=time.perf_counter(); value=fn(); samples.append((time.perf_counter()-start)*1000.0)
    return summarize_samples(samples), value


def _subprocess_seconds(
    command: list[str], *, cwd: Path, env: dict[str, str], input_text: str | None = None, repeat: int = 3,
    timeout_seconds: float = BENCHMARK_SUBPROCESS_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    samples=[]
    for _ in range(max(1, repeat)):
        command_env=dict(env)
        if input_text is None:
            result=run_bounded_command(command,cwd=cwd,env=command_env,timeout_seconds=timeout_seconds)
        else:
            wrapper=(
                "import subprocess,sys; "
                f"p=subprocess.run({command!r}, input={input_text!r}, text=True, "
                "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
                "raise SystemExit(p.returncode)"
            )
            result=run_bounded_command([sys.executable,"-c",wrapper],cwd=cwd,env=command_env,timeout_seconds=timeout_seconds)
        if not result.ok:
            raise RuntimeError(f"benchmark subprocess failed: {result.status}:{result.returncode}")
        samples.append(float(result.elapsed_seconds))
    return summarize_samples(samples)


def _fresh_data_chat_startup(*, root: Path, base_env: dict[str, str], repeat: int = 3) -> dict[str, Any]:
    samples=[]
    for _ in range(max(1, repeat)):
        with tempfile.TemporaryDirectory(prefix="eidolon-v1253-fresh-start-") as runtime:
            env=dict(base_env); env["EIDOLON_DATA_DIR"]=runtime
            row=_subprocess_seconds([sys.executable,str(root/"eidolon.py"),"chat"],cwd=root,env=env,input_text="q\n",repeat=1)
            samples.append(float(row["median"]))
    return summarize_samples(samples)


def _first_message_samples(*, root: Path, base_env: dict[str, str], repeat: int = 3) -> dict[str, Any]:
    pre=[]; total=[]; providers=[]
    script = r'''
import json
import conversation_runtime as cr
class FakeClient:
    def __init__(self,config,cancel_event=None):
        self.config=config; self.last_retry_count=0; self.last_metrics={}; self.provider=self
    def generate(self,prompt): return "A concise local response."
    def stream(self,prompt): yield "A concise local response."
    def close(self): pass
    def cancel(self): pass
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
cr.LocalModelClient=FakeClient
r=cr.run_conversation_turn("Hi!",source="v1253.9.1-first-message-benchmark",use_ai=True)
print(json.dumps({"ok":bool(r.success),"pre_provider_ms":r.timings_ms.get("pre_provider"),"next_input_ready_ms":r.timings_ms.get("total"),"provider_request_count":r.provider_request_count}))
'''
    for _ in range(max(1,repeat)):
        with tempfile.TemporaryDirectory(prefix="eidolon-v1253-first-message-") as runtime:
            env=dict(base_env); env["EIDOLON_DATA_DIR"]=runtime; env["PYTHONPATH"]=str(root/"conscious_agent")
            result=run_bounded_command([sys.executable,"-c",script],cwd=root,env=env,timeout_seconds=20)
            row=result.parsed_json or {}
            if not result.ok or not row.get("ok"):
                raise RuntimeError(f"first-message benchmark failed: {result.status}:{result.returncode}")
            pre.append(float(row.get("pre_provider_ms") or 0)); total.append(float(row.get("next_input_ready_ms") or 0)); providers.append(float(row.get("provider_request_count") or 0))
    return {
        "pre_provider_ms": summarize_samples(pre),
        "next_input_ready_ms": summarize_samples(total),
        "provider_request_count": summarize_samples(providers),
        "fake_provider": True,
    }


def benchmark_runtime_efficiency(*, source_root: str | Path | None = None, include_persistent_scale: bool = True) -> dict[str, Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    fixture=lambda name,chars=900:{"prompt_section":f"<{name}>"+("x"*chars)+f"</{name}>"}
    social_projection,social_diag=build_compact_cognitive_projection(
        "Hi!",action_projection={},development_campaign={},cognitive=fixture("cognition"),conversation_policy=fixture("policy"),
        conversation_discourse=fixture("discourse"),memory_retrieval=fixture("memory"),natural_continuity=fixture("continuity"),
        natural_follow_up=fixture("followup"),governed_speech=fixture("speech"),daily_companion=fixture("companion"),
    )
    ordinary_projection,ordinary_diag=build_compact_cognitive_projection(
        "Tell me what you think about this idea",action_projection={},development_campaign={},cognitive=fixture("cognition"),conversation_policy=fixture("policy"),
        conversation_discourse=fixture("discourse"),memory_retrieval=fixture("memory"),natural_continuity=fixture("continuity"),
        natural_follow_up=fixture("followup"),governed_speech=fixture("speech"),daily_companion=fixture("companion"),
    )
    ack_timing,_=_timed_ms(lambda:trusted_action_acknowledgement({"grounding":{"capability_id":"run_diagnostics"}}),repeat=25)
    fast_status_timing,fast_status=_timed_ms(build_fast_runtime_status,repeat=15)
    base_env=dict(os.environ); base_env["PYTHONDONTWRITEBYTECODE"]="1"
    with tempfile.TemporaryDirectory(prefix="eidolon-v1253-established-start-") as runtime:
        established_env=dict(base_env); established_env["EIDOLON_DATA_DIR"]=runtime
        established_cold=_subprocess_seconds([sys.executable,str(root/"eidolon.py"),"chat"],cwd=root,env=established_env,input_text="q\n",repeat=3)
        import_env=dict(established_env); import_env["PYTHONPATH"]=str(root/"conscious_agent")
        bare_python=_subprocess_seconds([sys.executable,"-c","pass"],cwd=root,env=import_env,repeat=3)
        runtime_process=_subprocess_seconds([sys.executable,"-c","import conversation_runtime"],cwd=root,env=import_env,repeat=3)
    fresh_cold=_fresh_data_chat_startup(root=root,base_env=base_env,repeat=3)
    incremental_samples=[]
    if bare_python["count"] and runtime_process["count"]:
        # A same-host process-level estimate, not a universal import constant.
        incremental_samples=[max(0.0,float(runtime_process["median"])-float(bare_python["median"]))]
    incremental_import=summarize_samples(incremental_samples)
    first_message=_first_message_samples(root=root,base_env=base_env,repeat=3)
    persistent=None
    if include_persistent_scale:
        persistent=benchmark_persistent_state_scaling(memory_count=5_000,session_count=200,action_count=5_000)
    persistent_latency_ok=True
    if persistent is not None:
        measured=persistent.get("measured_ms") or {}; budgets=persistent.get("budgets_ms") or {}
        persistent_latency_ok=all(isinstance(measured.get(name),(int,float)) and float(measured[name])<=float(limit) for name,limit in budgets.items())
        # The underlying v1252.9 benchmark's historical ``ok`` means that its
        # *full* 20K/1K/20K stress scale was reached.  That is intentionally
        # false for this bounded medium profile, so carrying it forward beside
        # ``profile_ok=True`` produces a self-contradictory receipt.  Preserve
        # the historical meaning explicitly instead of overloading ``ok``.
        persistent["full_scale_ok"]=bool(persistent.pop("ok", False))
        persistent["benchmark_profile"]="medium"
        persistent["profile_ok"]=persistent_latency_ok
        persistent["full_scale_reached"]=False
        persistent["latency_ok"]=persistent_latency_ok
    baseline=load_same_host_baseline()
    return {
        "contract_version":CONTRACT_VERSION,
        "ok":bool(fast_status.get("ok")) and persistent_latency_ok and float(first_message["provider_request_count"]["median"] or 0)==1.0,
        "measurements":{
            "trusted_action_ack_build_ms":ack_timing,
            "dashboard_fast_status_ms":fast_status_timing,
            # Compatibility alias: established-runtime cold process startup.
            "terminal_cold_start_seconds":established_cold,
            "terminal_cold_start_established_runtime_seconds":established_cold,
            "terminal_cold_start_fresh_data_seconds":fresh_cold,
            # Compatibility alias retained, now explicitly process-inclusive.
            "conversation_runtime_import_seconds":runtime_process,
            "python_process_start_seconds":bare_python,
            "conversation_runtime_process_start_seconds":runtime_process,
            "conversation_runtime_incremental_import_seconds":incremental_import,
            "first_message_pre_provider_ms":first_message["pre_provider_ms"],
            "first_message_next_input_ready_ms":first_message["next_input_ready_ms"],
            "first_message_provider_request_count":first_message["provider_request_count"],
            "social_prompt_tokens":{"value":social_diag["estimated_projection_tokens"]},
            "ordinary_prompt_tokens":{"value":ordinary_diag["estimated_projection_tokens"]},
        },
        "projection_chars":{"social":len(social_projection),"ordinary":len(ordinary_projection)},
        "persistent_state_medium_scale":persistent,
        "same_host_profile":coarse_host_profile(),
        "accepted_same_host_baseline_present":baseline is not None,
        "provider_contacted":False,
        "fake_provider_used_for_first_message":True,
        "temporary_runtime_cleanup_scoped":True,
        "project_mutated":False,
        "release_authorized":False,
        "independent_authority_granted":False,
    }


__all__=["CONTRACT_VERSION","BENCHMARK_SUBPROCESS_TIMEOUT_SECONDS","benchmark_runtime_efficiency"]
