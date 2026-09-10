from __future__ import annotations

"""Read-only operator status plus explicitly authorized dataset/eval workflows."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from model_training.model_registry import register_model_candidate
from model_training.training_dataset import materialize_dataset_manifest, validate_dataset_manifest
from model_training.training_eval import materialize_evaluation_corpus, materialize_evaluation_result, validate_evaluation_corpus
from model_training.training_benchmark import run_frozen_corpus
from model_training.training_preferences import build_preference_pair
from model_training.training_provenance import materialize_dataset_provenance, validate_dataset_provenance
from model_training.training_record import _training_root, load_training_record
from model_training.training_policy import resolve_training_evidence_capture_policy

CONTRACT_VERSION = "v2503.4.39"
APPROVED_READINESS_TARGET = 5000
EVAL_READINESS_TARGET = 500


def _operator_runtime_root(runtime_root=None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root).expanduser().resolve()
    try:
        from paths import DATA_DIR
    except ImportError:
        from paths import DATA_DIR
    return Path(DATA_DIR).expanduser().resolve()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _stage_records(root: Path, stage: str) -> list[dict[str, Any]]:
    directory = root / stage
    rows = []
    for path in sorted(directory.glob("trn_*.json")) if directory.exists() else []:
        row = load_training_record(path.stem, runtime_root=root.parent, stage=stage)
        if row:
            rows.append(row)
    return rows


def build_training_evidence_status(*, runtime_root=None) -> dict[str, Any]:
    root = _training_root(_operator_runtime_root(runtime_root))
    raw = _stage_records(root, "raw")
    sanitized = _stage_records(root, "sanitized")
    approved = _stage_records(root, "approved")
    failures = [_read_json(path) for path in sorted((root / "capture_failures").glob("*.json"))] if (root / "capture_failures").exists() else []
    datasets = [_read_json(path) for path in sorted((root / "datasets").glob("*.manifest.json"))] if (root / "datasets").exists() else []
    datasets = [row for row in datasets if validate_dataset_manifest(row)]
    corpora = [_read_json(path) for path in sorted((root / "eval").glob("*.corpus.json"))] if (root / "eval").exists() else []
    corpora = [row for row in corpora if validate_evaluation_corpus(row)]
    evaluations = [_read_json(path) for path in sorted((root / "eval").glob("*.result.json"))] if (root / "eval").exists() else []
    models = list((root / "models").glob("*.json")) if (root / "models").exists() else []
    capability_counts = Counter(str(row.get("task_type") or "other") for row in raw)
    preference_count = sum(1 for row in sanitized if build_preference_pair(row).get("ok") is True)
    latest_dataset = datasets[-1] if datasets else {}
    latest_corpus = corpora[-1] if corpora else {}
    provenance = {}
    if latest_dataset:
        safe = "".join(c if c.isalnum() or c in "._-" else "-" for c in str(latest_dataset.get("dataset_version") or ""))[:96]
        provenance = _read_json(root / "datasets" / f"{safe}.provenance.json")
    policy = resolve_training_evidence_capture_policy()
    approved_count = len(approved)
    eval_count = int(latest_corpus.get("case_count") or 0)
    readiness = {
        "approved_examples": approved_count,
        "approved_target": APPROVED_READINESS_TARGET,
        "approved_progress_percent": round(100 * approved_count / APPROVED_READINESS_TARGET, 2),
        "frozen_eval_cases": eval_count,
        "frozen_eval_target": EVAL_READINESS_TARGET,
        "eval_progress_percent": round(100 * eval_count / EVAL_READINESS_TARGET, 2),
        "ready": bool(approved_count >= APPROVED_READINESS_TARGET and eval_count >= EVAL_READINESS_TARGET and provenance),
    }
    return {
        "ok": True,
        "status": "training_evidence_status",
        "contract_version": CONTRACT_VERSION,
        "policy": policy.public_record(),
        "counts": {
            "raw": len(raw), "sanitized": len(sanitized), "approved": approved_count,
            "capture_failures": len([row for row in failures if row]),
            "preference_pairs": preference_count,
            "datasets": len(datasets), "eval_corpora": len(corpora),
            "baseline_benchmarks": len(evaluations), "registered_model_candidates": len(models),
            "duplicates_removed_latest_dataset": int(latest_dataset.get("dedup_rejected_count") or 0),
        },
        "records_by_capability": dict(sorted(capability_counts.items())),
        "latest_dataset_version": str(latest_dataset.get("dataset_version") or ""),
        "latest_dataset_manifest_digest": str(latest_dataset.get("manifest_digest") or ""),
        "latest_eval_corpus_version": str(latest_corpus.get("corpus_version") or ""),
        "latest_eval_corpus_digest": str(latest_corpus.get("corpus_digest") or ""),
        "provenance_status": "verified" if provenance and validate_dataset_provenance(provenance, manifest=latest_dataset) else "not_available",
        "baseline_benchmark_status": "available" if evaluations else "not_available",
        "readiness": readiness,
        "hard_boundaries": {
            "auto_approve": False, "automatic_dataset_export": False,
            "training_authorized": False, "model_promotion_authorized": False,
        },
        "runtime_only": True,
    }


def create_governed_dataset(*, runtime_root, dataset_version: str, operator_authorized: bool) -> dict[str, Any]:
    manifest_result = materialize_dataset_manifest(
        runtime_root=runtime_root, dataset_version=dataset_version, operator_authorized=operator_authorized
    )
    if manifest_result.get("ok") is not True:
        return manifest_result
    provenance = materialize_dataset_provenance(
        runtime_root=runtime_root, manifest=manifest_result["manifest"], operator_authorized=operator_authorized
    )
    return {
        "ok": provenance.get("ok") is True,
        "status": "governed_dataset_created" if provenance.get("ok") is True else str(provenance.get("status") or "dataset_provenance_failed"),
        "manifest": manifest_result["manifest"], "provenance": provenance.get("certificate") or {},
        "dataset_exported": False, "model_training_authorized": False, "model_promotion_authorized": False,
    }


def create_governed_eval_corpus(*, runtime_root, corpus_version: str, cases: Iterable[Mapping[str, Any]], operator_authorized: bool) -> dict[str, Any]:
    return materialize_evaluation_corpus(
        runtime_root=runtime_root, corpus_version=corpus_version, cases=cases, operator_authorized=operator_authorized
    )


def list_training_records(*, runtime_root=None, stage: str) -> dict[str, Any]:
    if stage not in {"raw", "sanitized", "approved"}:
        return {"ok": False, "status": "training_record_stage_invalid"}
    rows = _stage_records(_training_root(_operator_runtime_root(runtime_root)), stage)
    return {
        "ok": True, "status": f"training_{stage}_records", "stage": stage, "count": len(rows),
        "records": [
            {
                "record_id": row.get("record_id"), "task_type": row.get("task_type"),
                "validation_passed": row.get("validation_passed"), "has_correction": row.get("has_correction"),
                "sanitized": row.get("sanitized"), "approved_for_training": row.get("approved_for_training"),
                "record_digest": row.get("record_digest"),
            }
            for row in rows
        ],
        "runtime_only": True,
    }


def list_training_artifacts(*, runtime_root=None, kind: str) -> dict[str, Any]:
    root = _training_root(_operator_runtime_root(runtime_root))
    pattern, validator = {
        "datasets": ("datasets/*.manifest.json", validate_dataset_manifest),
        "eval_corpora": ("eval/*.corpus.json", validate_evaluation_corpus),
        "benchmarks": ("eval/*.result.json", lambda row: bool(row.get("evaluation_digest"))),
    }.get(kind, ("", lambda _row: False))
    if not pattern:
        return {"ok": False, "status": "training_artifact_kind_invalid"}
    rows = [_read_json(path) for path in sorted(root.glob(pattern))]
    rows = [row for row in rows if validator(row)]
    return {"ok": True, "status": f"training_{kind}", "kind": kind, "count": len(rows), "items": rows, "runtime_only": True}


def run_configured_local_benchmark(
    *, runtime_root, corpus_version: str, provider: str, model: str, operator_authorized: bool
) -> dict[str, Any]:
    if operator_authorized is not True:
        return {"ok": False, "status": "benchmark_operator_authorization_required", "provider_contacted": False}
    try:
        from local_model import LocalModelClient, LocalModelConfig
        from settings_manager import load_settings
    except ImportError:
        from local_model import LocalModelClient, LocalModelConfig
        from settings_manager import load_settings
    settings = load_settings()
    requested_provider = str(provider or "").strip().lower()
    requested_model = str(model or "").strip()
    if requested_provider != str(settings.get("local_model_provider") or "").strip().lower():
        return {"ok": False, "status": "benchmark_provider_not_configured", "provider_contacted": False}
    if requested_model != str(settings.get("local_model") or "").strip():
        return {"ok": False, "status": "benchmark_model_not_configured", "provider_contacted": False}
    safe = "".join(c if c.isalnum() or c in "._-" else "-" for c in str(corpus_version))[:96]
    corpus = _read_json(_training_root(runtime_root) / "eval" / f"{safe}.corpus.json")
    if not validate_evaluation_corpus(corpus):
        return {"ok": False, "status": "benchmark_frozen_corpus_required", "provider_contacted": False}
    client = LocalModelClient(LocalModelConfig.from_settings(settings))
    try:
        result = run_frozen_corpus(
            corpus=corpus, model_id=requested_model, provider_generate=client.generate,
            operator_authorized=True,
        )
    finally:
        client.close()
    evaluation = dict(result.get("evaluation") or {})
    if evaluation:
        from model_training.training_record import _atomic_json
        model_safe = "".join(c if c.isalnum() or c in "._-" else "-" for c in requested_model)[:96]
        evaluation_digest = str(evaluation.get("evaluation_digest") or "")
        path = _training_root(runtime_root) / "eval" / f"{safe}.{model_safe}.{evaluation_digest[:12]}.result.json"
        if path.exists():
            existing = _read_json(path)
            if existing != evaluation:
                return {**result, "ok": False, "status": "benchmark_result_identity_conflict", "runtime_path": str(path)}
        else:
            _atomic_json(path, evaluation)
        result["runtime_path"] = str(path)
    result.update({
        "provider": requested_provider, "model": requested_model, "model_registered": False,
        "model_promotion_authorized": False, "raw_model_outputs_stored": False,
    })
    return result


__all__ = [
    "build_training_evidence_status", "create_governed_dataset", "create_governed_eval_corpus",
    "list_training_records", "list_training_artifacts", "run_configured_local_benchmark", "register_model_candidate",
]
