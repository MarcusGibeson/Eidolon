from __future__ import annotations

"""Short provider-free mixed-load contention benchmark for v1253.9.1."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from hermetic_verification_runtime import run_bounded_command

CONTRACT_VERSION = "v1253.9.1"

_SCRIPT = r'''
import json, statistics, threading, time
import conversation_runtime as cr
from dashboard_fast_status import build_fast_runtime_status
from proactive_communication import CognitiveInitiativeService

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

service=CognitiveInitiativeService(poll_seconds=60.0)
stop=threading.Event(); cadence_errors=[]; cadence_ticks=0

def cadence_loop():
    global cadence_ticks
    while not stop.is_set():
        try:
            service.tick(); cadence_ticks += 1
        except Exception as exc:
            cadence_errors.append(type(exc).__name__)
        # Exercise repeated cadence work far more often than the production
        # 60-second poll without turning the fixture into a continuous I/O loop.
        stop.wait(0.25)

thread=threading.Thread(target=cadence_loop,daemon=True); thread.start()
pre=[]; total=[]; status=[]; provider_counts=[]
try:
    for i in range(12):
        t=time.perf_counter(); payload=build_fast_runtime_status(); status.append((time.perf_counter()-t)*1000.0)
        r=cr.run_conversation_turn(f"Ordinary contention turn {i}.",source="v1253.9.1-contention",use_ai=True)
        if not r.success: raise RuntimeError("conversation_failed")
        pre.append(float(r.timings_ms.get("pre_provider") or 0)); total.append(float(r.timings_ms.get("total") or 0)); provider_counts.append(float(r.provider_request_count))
finally:
    stop.set(); thread.join(2)

def summary(values):
    values=sorted(values); n=len(values); idx=max(0,min(n-1,__import__('math').ceil(n*.95)-1))
    return {"count":n,"median":round(statistics.median(values),4),"p95":round(values[idx],4),"maximum":round(max(values),4)}
print(json.dumps({"ok":not cadence_errors and all(v==1.0 for v in provider_counts),"warm_pre_provider_ms":summary(pre[4:]),"next_input_ready_ms":summary(total[4:]),"dashboard_fast_status_ms":summary(status),"provider_request_count":summary(provider_counts),"cadence_ticks":cadence_ticks,"cadence_errors":cadence_errors,"provider_contacted":False,"fake_provider":True}))
'''


def benchmark_runtime_contention(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="eidolon-v1253-contention-") as runtime:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["EIDOLON_DATA_DIR"] = runtime
        env["PYTHONPATH"] = str(root / "conscious_agent")
        result = run_bounded_command([sys.executable, "-c", _SCRIPT], cwd=root, env=env, timeout_seconds=45)
        payload = dict(result.parsed_json or {})
        payload.update({
            "contract_version": CONTRACT_VERSION,
            "runner_status": result.status,
            "runner_elapsed_seconds": result.elapsed_seconds,
            "temporary_runtime_cleanup_scoped": True,
            "release_authorized": False,
            "independent_authority_granted": False,
        })
        payload["ok"] = bool(result.ok) and bool(payload.get("ok"))
        return payload


__all__ = ["CONTRACT_VERSION", "benchmark_runtime_contention"]
