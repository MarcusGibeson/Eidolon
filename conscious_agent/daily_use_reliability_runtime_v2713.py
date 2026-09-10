from __future__ import annotations
"""v2713 runtime bridge for daily-use reliability, read-only except its own history."""
from pathlib import Path
from typing import Any
import os
try:
    from unified_cognitive_state_frame import build_unified_cognitive_state_frame
    from conversation_health_v2694 import build_conversation_health
    from response_quality_observability_v2705 import build_response_quality_observability
    from memory_retrieval_observability_v2576 import load_memory_retrieval_observability
    from conversation_context_observability_v2590 import load_conversation_context_observability
    from cognitive_observability_signals_v2539 import build_cognitive_observability_signals
    from daily_use_reliability_v2710 import build_daily_use_reliability
    from daily_use_reliability_history_v2711 import append_daily_use_reliability, load_daily_use_reliability_history, build_daily_use_reliability_trend
    from daily_use_reliability_review_v2712 import build_daily_use_reliability_review
except ImportError:
    from unified_cognitive_state_frame import build_unified_cognitive_state_frame
    from conversation_health_v2694 import build_conversation_health
    from response_quality_observability_v2705 import build_response_quality_observability
    from memory_retrieval_observability_v2576 import load_memory_retrieval_observability
    from conversation_context_observability_v2590 import load_conversation_context_observability
    from cognitive_observability_signals_v2539 import build_cognitive_observability_signals
    from daily_use_reliability_v2710 import build_daily_use_reliability
    from daily_use_reliability_history_v2711 import append_daily_use_reliability, load_daily_use_reliability_history, build_daily_use_reliability_trend
    from daily_use_reliability_review_v2712 import build_daily_use_reliability_review
CONTRACT_VERSION='v2713.0'
def _root(runtime_root=None)->Path:
    if runtime_root is not None:return Path(runtime_root).expanduser().resolve()
    return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def build_daily_use_runtime_reliability(*,operation_id:str,runtime_root=None)->dict[str,Any]:
    root=_root(runtime_root);frame=build_unified_cognitive_state_frame(root,trigger_type='daily_use_reliability',trigger_ref=str(operation_id)[:80])
    home=frame.get('homeostasis') if isinstance(frame.get('homeostasis'),dict) else {}
    snapshot={'now':{'pressure':float(home.get('pressure') or 0.0),'recovery_margin':float(home.get('recovery_margin') or 0.0)},
              'conversation_health':build_conversation_health(root),'response_quality':build_response_quality_observability(root),
              'memory_retrieval':load_memory_retrieval_observability(root),'conversation_context':load_conversation_context_observability(root)}
    snapshot['signals']=build_cognitive_observability_signals({'ok':True,'now':snapshot['now'],'recent_count':0})
    reliability=build_daily_use_reliability(snapshot);append_daily_use_reliability(reliability,operation_id=operation_id,runtime_root=root)
    trend=build_daily_use_reliability_trend(load_daily_use_reliability_history(root).get('rows') or [])
    review=build_daily_use_reliability_review(reliability,trend)
    return {'ok':True,'contract_version':CONTRACT_VERSION,'reliability':reliability,'trend':trend,'review':review,'read_only_except_history':True,'automatic_action':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','build_daily_use_runtime_reliability']
