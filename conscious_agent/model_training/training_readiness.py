from __future__ import annotations
"""Readiness gate for a future operator-authorized fine-tuning campaign."""
from typing import Any,Mapping
from model_training.training_dataset import validate_dataset_manifest
from model_training.training_eval import validate_evaluation_corpus, validate_evaluation_result
from model_training.training_provenance import validate_dataset_provenance, validate_dataset_provenance_against_store
CONTRACT_VERSION="v2503.4.30.1"
def assess_training_readiness(*,dataset_manifest:Mapping[str,Any],evaluation_corpus:Mapping[str,Any],baseline_evaluation:Mapping[str,Any],dataset_provenance:Mapping[str,Any]|None=None,runtime_root=None,minimum_records:int=5000,minimum_eval_cases:int=500)->dict[str,Any]:
    manifest_valid=validate_dataset_manifest(dataset_manifest); provenance_required=dataset_manifest.get("approved_store_provenance_required") is True; provenance_valid=bool(
        manifest_valid and dataset_provenance is not None and runtime_root is not None
        and validate_dataset_provenance_against_store(dataset_provenance,manifest=dataset_manifest,runtime_root=runtime_root)
    ); corpus_valid=validate_evaluation_corpus(evaluation_corpus); baseline_valid=bool(corpus_valid and validate_evaluation_result(baseline_evaluation,corpus=evaluation_corpus))
    checks={
      "dataset_versioned":bool(manifest_valid and dataset_manifest.get("dataset_version")),
      "dataset_approved_store_provenance":bool((not provenance_required) or provenance_valid),
      "dataset_large_enough":manifest_valid and int(dataset_manifest.get("record_count") or 0)>=minimum_records,
      "dataset_diverse":manifest_valid and len([v for v in (dataset_manifest.get("capability_counts") or {}).values() if int(v)>0])>=5,
      "dataset_bound_to_records":manifest_valid and len(dataset_manifest.get("record_bindings") or [])==int(dataset_manifest.get("record_count") or 0),
      "eval_frozen":corpus_valid,
      "eval_large_enough":corpus_valid and int(evaluation_corpus.get("case_count") or 0)>=minimum_eval_cases,
      "baseline_complete":baseline_valid and baseline_evaluation.get("complete") is True,
    }
    ready=all(checks.values())
    return {"contract_version":CONTRACT_VERSION,"ready_for_operator_training_review":ready,"checks":checks,"missing":[k for k,v in checks.items() if not v],"automatic_training":False,"model_training_authorized":False,"model_promotion_authorized":False}
