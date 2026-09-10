from __future__ import annotations
from pathlib import Path
from typing import Any,Mapping
from development_memory_relevance_foundations import AUTHORITY_FLAGS
CONTRACT_VERSION="v1283.8"
def inspect_development_memory_relevance_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();checks={"foundations_present":(root/'conscious_agent/development_memory_relevance_foundations.py').is_file(),"integration_present":(root/'conscious_agent/development_memory_relevance.py').is_file(),"v1166_relevance_lineage":(root/'conscious_agent/memory_retrieval_relevance.py').is_file(),"v1245_project_lineage":(root/'conscious_agent/cross_session_project_understanding.py').is_file(),"v1235_lesson_lineage":(root/'conscious_agent/evidence_backed_development_outcome_lessons.py').is_file(),"v1282_uncertainty_lineage":(root/'conscious_agent/calibrated_uncertainty_foundations.py').is_file()};return {"ok":all(checks.values()),"checks":checks,"read_only":True,**AUTHORITY_FLAGS}
def compare_development_memory_retrievals(before:Mapping[str,Any],after:Mapping[str,Any])->dict[str,Any]:return {"ok":bool(before.get("ok") and after.get("ok")),"selected_count_delta":int(after.get("selected_count") or 0)-int(before.get("selected_count") or 0),"selection_changed":before.get("selected")!=after.get("selected"),"authority_changed":False,"raw_content_exposed":False,**AUTHORITY_FLAGS}
def build_development_memory_relevance_handoff(*,source_root:str|Path|None=None)->dict[str,Any]:
 h=inspect_development_memory_relevance_health(source_root=source_root);return {"ok":h["ok"],"status":"development_memory_relevance_handoff_ready" if h["ok"] else "development_memory_relevance_handoff_blocked","next_bounded_unit":"v1284 Experiential Learning","v1284_started":False,"native_windows_review":["restart_retrieval_stability","long_path_runtime_store","stale_memory_suppression","bounded_projection_after_many_sessions"],**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","inspect_development_memory_relevance_health","compare_development_memory_retrievals","build_development_memory_relevance_handoff"]
