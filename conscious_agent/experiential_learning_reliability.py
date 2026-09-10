from __future__ import annotations
from pathlib import Path
from typing import Any,Mapping
from experiential_learning_foundations import AUTHORITY_FLAGS
CONTRACT_VERSION="v1284.8"
def inspect_experiential_learning_health(*,source_root:str|Path|None=None)->dict[str,Any]:
 root=Path(source_root or Path(__file__).resolve().parents[1]).resolve();checks={"foundations":(root/'conscious_agent/experiential_learning_foundations.py').is_file(),"integration":(root/'conscious_agent/experiential_learning.py').is_file(),"v1168_lineage":(root/'conscious_agent/bounded_experiential_lessons.py').is_file(),"v1235_lineage":(root/'conscious_agent/evidence_backed_development_outcome_lessons.py').is_file(),"v1283_relevance":(root/'conscious_agent/development_memory_relevance_foundations.py').is_file(),"v1282_uncertainty":(root/'conscious_agent/calibrated_uncertainty_foundations.py').is_file()};return {"ok":all(checks.values()),"checks":checks,"read_only":True,**AUTHORITY_FLAGS}
def compare_lessons(before:Mapping[str,Any],after:Mapping[str,Any])->dict[str,Any]:return {"ok":bool(before.get("ok") and after.get("ok")),"state_changed":before.get("state")!=after.get("state"),"confidence_delta":int(after.get("confidence") or 0)-int(before.get("confidence") or 0),"authority_changed":False,"raw_content_exposed":False,**AUTHORITY_FLAGS}
def build_experiential_learning_handoff(*,source_root=None)->dict[str,Any]:
 h=inspect_experiential_learning_health(source_root=source_root);return {"ok":h["ok"],"next_bounded_unit":"v1285 Hierarchical Goal Management","v1285_started":False,"native_windows_review":["restart_preserves_lesson_state","stale_lesson_suppression","contradiction_after_restart","bounded_lesson_selection"],**AUTHORITY_FLAGS}
__all__=["CONTRACT_VERSION","inspect_experiential_learning_health","compare_lessons","build_experiential_learning_handoff"]
