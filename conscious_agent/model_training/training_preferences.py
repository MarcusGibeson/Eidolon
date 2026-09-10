from __future__ import annotations
"""Preference-pair derivation from sanitized, verified correction evidence."""
from typing import Any, Mapping
from model_training.training_schema import normalize_training_record
CONTRACT_VERSION="v2503.4.21"
def build_preference_pair(record: Mapping[str,Any])->dict[str,Any]:
    n=normalize_training_record(record)
    if not n["sanitized"]: return {"ok":False,"status":"preference_unsanitized_rejected","model_training_authorized":False}
    if not n["has_preference_pair"] or n["rejected_output"] is None:
        return {"ok":False,"status":"preference_pair_unavailable","model_training_authorized":False}
    if not n["validation_passed"]:
        return {"ok":False,"status":"preference_chosen_output_not_verified","model_training_authorized":False}
    if n["rejected_output"]==n["chosen_output"]:
        return {"ok":False,"status":"preference_outputs_identical","model_training_authorized":False}
    return {"ok":True,"status":"preference_pair_ready","record_id":n["record_id"],"prompt":n["input"],"chosen":n["chosen_output"],"rejected":n["rejected_output"],"capability":n["capability"],"failure_code":n["failure_code"],"runtime_only":True,"model_training_authorized":False,"model_promotion_authorized":False}
