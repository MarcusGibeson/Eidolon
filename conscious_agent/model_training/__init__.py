"""Governed, runtime-only Eidolon model-training evidence foundations."""

from model_training.training_record import TRAINING_RECORD_SCHEMA_VERSION, create_training_record, load_training_record, record_training_interaction, training_record_path
from model_training.training_sanitizer import sanitize_training_record
from model_training.training_quality import assess_training_record_quality
from model_training.training_export import approve_training_record, export_approved_sft_jsonl, export_manifest_sft_jsonl, export_manifest_preference_jsonl

__all__ = [
    "TRAINING_RECORD_SCHEMA_VERSION",
    "create_training_record",
    "load_training_record",
    "record_training_interaction",
    "training_record_path",
    "sanitize_training_record",
    "assess_training_record_quality",
    "approve_training_record",
    "export_approved_sft_jsonl",
    "export_manifest_sft_jsonl",
    "export_manifest_preference_jsonl",
]

from model_training.training_schema import normalize_training_record
from model_training.training_dedup import deduplicate_records
from model_training.training_preferences import build_preference_pair
from model_training.training_dataset import build_dataset_manifest, validate_dataset_manifest, materialize_dataset_manifest
from model_training.training_eval import freeze_evaluation_corpus, score_evaluation_results, compare_model_evaluations, validate_evaluation_corpus, validate_evaluation_result
from model_training.model_registry import register_model_candidate
from model_training.training_readiness import assess_training_readiness

from model_training.training_provenance import materialize_dataset_provenance, validate_dataset_provenance
from model_training.training_benchmark import run_frozen_corpus
