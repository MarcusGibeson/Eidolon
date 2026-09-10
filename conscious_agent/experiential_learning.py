from __future__ import annotations
"""v1284.3-v1284.5 integration with verified development outcomes and v1283 relevance."""
from typing import Any,Mapping,Sequence
from experiential_learning_foundations import *
CONTRACT_VERSION="v1284.5"
def lesson_from_verified_development_outcome(outcome:Mapping[str,Any])->dict[str,Any]:
 verified=bool(outcome.get("verified") is True or (outcome.get("completed") is True and int(outcome.get("verification_failure_count") or 0)==0 and int(outcome.get("unauthorized_action_count") or 0)==0));return build_experiential_lesson(lesson_code=str(outcome.get("lesson_code") or f"outcome_{outcome.get('outcome_code') or 'lesson'}"),outcome_code=str(outcome.get("outcome_code") or outcome.get("scenario_code") or "development_outcome"),guidance_code=str(outcome.get("guidance_code") or "reuse_verified_approach"),applicability_tags=list(outcome.get("applicability_tags") or outcome.get("context_tags") or []),evidence_codes=list(outcome.get("evidence_codes") or [str(outcome.get("receipt_code") or "verified_outcome")]),verified_outcome=verified,confidence=int(outcome.get("confidence") or 65))
def experiential_lesson_memory_record(lesson:Mapping[str,Any])->dict[str,Any]:
 from development_memory_relevance_foundations import build_development_memory_record
 if not validate_experiential_lesson(lesson).get("ok"):raise ValueError("valid_lesson_required")
 return build_development_memory_record(memory_code=f"experiential_{lesson.get('lesson_code')}",memory_type="lesson",relevance_tags=lesson.get("applicability_tags") or [],semantic_key=str(lesson.get("lesson_code")),confidence=int(lesson.get("confidence") or 0),freshness="current" if lesson.get("state")=="active" else "stale",verification_state="verified",contradicted=lesson.get("state")=="contradicted")
def build_experiential_learning_projection(*,context_tags:Sequence[str],outcomes:Sequence[Mapping[str,Any]])->dict[str,Any]:
 lessons=[lesson_from_verified_development_outcome(x) for x in outcomes];verified=[x for x in lessons if x.get("ok")];selection=select_applicable_lessons(context_tags=context_tags,lessons=verified);selection["outcome_count"]=len(outcomes);selection["verified_lesson_count"]=len(verified);selection["unverified_outcome_count"]=len(outcomes)-len(verified);selection["lesson_candidates_persisted_automatically"]=False;return selection
__all__=["CONTRACT_VERSION","lesson_from_verified_development_outcome","experiential_lesson_memory_record","build_experiential_learning_projection"]
