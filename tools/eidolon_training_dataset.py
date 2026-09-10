from __future__ import annotations

"""Local operator utility for inspecting the governed training evidence pipeline.

This utility never trains, fine-tunes, distills, downloads, uploads, or promotes
models. It only sanitizes, assesses, explicitly approves, and exports records
inside a caller-supplied runtime root.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

from conscious_agent.model_training.training_export import approve_training_record, export_approved_sft_jsonl, export_manifest_sft_jsonl, export_manifest_preference_jsonl
from conscious_agent.model_training.training_quality import assess_training_record_quality
from conscious_agent.model_training.training_record import load_training_record
from conscious_agent.model_training.training_sanitizer import sanitize_stored_training_record
from conscious_agent.model_training.training_operator import (
    build_training_evidence_status,
    create_governed_dataset,
    create_governed_eval_corpus,
    list_training_artifacts,
    list_training_records,
    run_configured_local_benchmark,
)


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed local Eidolon training-dataset utility")
    parser.add_argument("--runtime-root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    p_sanitize = sub.add_parser("sanitize"); p_sanitize.add_argument("record_id")
    p_assess = sub.add_parser("assess"); p_assess.add_argument("record_id"); p_assess.add_argument("--stage", choices=("sanitized", "approved"), default="sanitized")
    p_approve = sub.add_parser("approve"); p_approve.add_argument("record_id"); p_approve.add_argument("--confirm", action="store_true")
    p_export = sub.add_parser("export-sft"); p_export.add_argument("--name", default="eidolon_sft.jsonl"); p_export.add_argument("--confirm", action="store_true")
    p_manifest_sft = sub.add_parser("export-manifest-sft"); p_manifest_sft.add_argument("manifest"); p_manifest_sft.add_argument("--name"); p_manifest_sft.add_argument("--confirm", action="store_true")
    p_manifest_pref = sub.add_parser("export-manifest-preferences"); p_manifest_pref.add_argument("manifest"); p_manifest_pref.add_argument("--name"); p_manifest_pref.add_argument("--confirm", action="store_true")
    sub.add_parser("status")
    sub.add_parser("list-raw")
    sub.add_parser("list-sanitized")
    sub.add_parser("list-approved")
    sub.add_parser("readiness")
    p_build = sub.add_parser("build-manifest"); p_build.add_argument("version"); p_build.add_argument("--confirm", action="store_true")
    sub.add_parser("list-datasets")
    sub.add_parser("list-eval-corpora")
    sub.add_parser("benchmark-status")
    p_eval = sub.add_parser("create-eval-corpus"); p_eval.add_argument("version"); p_eval.add_argument("cases"); p_eval.add_argument("--confirm", action="store_true")
    p_benchmark = sub.add_parser("benchmark"); p_benchmark.add_argument("corpus_version"); p_benchmark.add_argument("--provider", required=True); p_benchmark.add_argument("--model", required=True); p_benchmark.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    runtime_root = Path(args.runtime_root).expanduser().resolve()
    if args.command == "status":
        result = build_training_evidence_status(runtime_root=runtime_root)
    elif args.command in {"list-raw", "list-sanitized", "list-approved"}:
        result = list_training_records(runtime_root=runtime_root, stage=args.command.removeprefix("list-"))
    elif args.command == "readiness":
        result = build_training_evidence_status(runtime_root=runtime_root)
        result["status"] = "training_readiness_status"
    elif args.command == "build-manifest":
        result = create_governed_dataset(runtime_root=runtime_root, dataset_version=args.version, operator_authorized=bool(args.confirm))
    elif args.command == "list-datasets":
        result = list_training_artifacts(runtime_root=runtime_root, kind="datasets")
    elif args.command == "list-eval-corpora":
        result = list_training_artifacts(runtime_root=runtime_root, kind="eval_corpora")
    elif args.command == "benchmark-status":
        result = list_training_artifacts(runtime_root=runtime_root, kind="benchmarks")
    elif args.command == "create-eval-corpus":
        try:
            cases_payload = json.loads(Path(args.cases).expanduser().read_text(encoding="utf-8"))
            cases = cases_payload.get("cases", []) if isinstance(cases_payload, dict) else cases_payload
            if not isinstance(cases, list):
                raise ValueError("evaluation_cases_must_be_a_list")
        except Exception as exc:
            result = {"ok": False, "status": "evaluation_cases_read_failed", "failure_class": type(exc).__name__}
        else:
            result = create_governed_eval_corpus(runtime_root=runtime_root, corpus_version=args.version, cases=cases, operator_authorized=bool(args.confirm))
    elif args.command == "benchmark":
        result = run_configured_local_benchmark(runtime_root=runtime_root, corpus_version=args.corpus_version, provider=args.provider, model=args.model, operator_authorized=bool(args.confirm))
    elif args.command == "sanitize":
        result = sanitize_stored_training_record(args.record_id, runtime_root=runtime_root)
    elif args.command == "assess":
        record = load_training_record(args.record_id, runtime_root=runtime_root, stage=args.stage)
        result = assess_training_record_quality(record) if record else {"ok": False, "status": "training_record_missing_or_invalid"}
    elif args.command == "approve":
        result = approve_training_record(args.record_id, runtime_root=runtime_root, operator_approved=bool(args.confirm))
    elif args.command == "export-sft":
        result = export_approved_sft_jsonl(runtime_root=runtime_root, export_name=args.name, operator_authorized=bool(args.confirm))
    else:
        try:
            manifest = json.loads(Path(args.manifest).expanduser().read_text(encoding="utf-8"))
        except Exception as exc:
            result = {"ok": False, "status": "training_dataset_manifest_read_failed", "failure_class": type(exc).__name__}
        else:
            if args.command == "export-manifest-sft":
                result = export_manifest_sft_jsonl(runtime_root=runtime_root, dataset_manifest=manifest, export_name=args.name, operator_authorized=bool(args.confirm))
            else:
                result = export_manifest_preference_jsonl(runtime_root=runtime_root, dataset_manifest=manifest, export_name=args.name, operator_authorized=bool(args.confirm))
    _print(result)
    return 0 if result.get("ok", True) is not False else 2


if __name__ == "__main__":
    raise SystemExit(main())
