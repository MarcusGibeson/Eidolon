from __future__ import annotations
"""Local operator review/apply controls; never installs source or contacts providers."""
import argparse
import hashlib
import json
from pathlib import Path
from json_storage import write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from memory_retrieval_policy_execution_v2730_9_2 import (
    _root, _digest, _read_state, load_memory_retrieval_policy, build_memory_retrieval_policy_candidate,
    authorize_and_apply_memory_retrieval_policy, authorize_and_rollback_memory_retrieval_policy,
)
from memory_retrieval_learning_observability_v2584 import build_memory_retrieval_learning_observability
from memory_retrieval_policy_review_v2585 import build_memory_retrieval_policy_review_packet
from response_grounding_output_audit_v2683 import audit_response_grounding_output
from response_grounding_repair_candidate_v2687 import build_response_grounding_repair_candidate
from response_grounding_repair_review_v2688 import build_response_grounding_repair_review
from response_grounding_repair_execution_v2730_9_2 import authorize_and_execute_response_grounding_repair


def _request_path(digest, runtime_root):
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("exact_request_digest_required")
    return _root(runtime_root) / "operator_repairs" / (digest + ".json")


def prepare(kind, *, runtime_root=None, response=None):
    if kind == "policy":
        observed = build_memory_retrieval_learning_observability(_root(runtime_root))
        review = build_memory_retrieval_policy_review_packet(observed)
        candidate = build_memory_retrieval_policy_candidate(review, runtime_root=runtime_root)
        if not candidate["changes"]:
            return {"ok": False, "status": "insufficient_policy_evidence"}
        request = {"kind": kind, "candidate": candidate}
    else:
        if not response or len(response) > 32000:
            raise ValueError("bounded_response_required")
        policy = {"personal_memory_reference_permitted": False}
        calibration = {"must_not_claim_execution_without_receipt": True}
        audit = audit_response_grounding_output(response, policy, calibration)
        candidate = build_response_grounding_repair_candidate(audit, policy, calibration)
        if candidate["state"] != "repair_candidate_ready":
            return {"ok": False, "status": "no_repair_needed"}
        request = {"kind": kind, "response": response, "policy": policy, "calibration": calibration,
                   "audit": audit, "candidate": candidate, "review": build_response_grounding_repair_review(candidate)}
    digest = _digest(request)
    path = _request_path(digest, runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=5):
        if not path.exists():
            write_json_atomic(path, {"request": request, "digest": digest}, expected_type=dict)
    return {"ok": True, "status": "operator_review_required", "request_digest": digest, "kind": kind,
            "candidate": candidate, "confirmation_required": digest,
            "source_modified": False, "provider_contacted": False}


def execute(digest, confirmation, *, runtime_root=None):
    if confirmation != digest:
        return {"ok": False, "status": "exact_confirmation_required"}
    path = _request_path(digest, runtime_root)
    with metadata_mutation_lock(path, timeout_seconds=5):
        row = json.loads(path.read_text(encoding="utf-8"))
        request = row["request"]
        if row.get("digest") != digest or _digest(request) != digest:
            return {"ok": False, "status": "invalid_operator_request"}
        if row.get("consumed"):
            return {"ok": False, "status": "authorization_already_consumed"}
        # Consume before execution; an interrupted attempt never retries implicitly.
        row["consumed"] = True
        write_json_atomic(path, row, expected_type=dict)
        if request["kind"] == "policy":
            result = authorize_and_apply_memory_retrieval_policy(request["candidate"], operator_confirmation=True, runtime_root=runtime_root)
        else:
            result = authorize_and_execute_response_grounding_repair(
                request["response"], audit=request["audit"], candidate=request["candidate"], review=request["review"],
                policy=request["policy"], calibration=request["calibration"], operator_confirmation=True)
        row["result"] = result
        write_json_atomic(path, row, expected_type=dict)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Governed local reliability repair. No provider or source changes.")
    parser.add_argument("--runtime-root", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("review-policy")
    response = sub.add_parser("review-response")
    response.add_argument("--text", required=True, help="Explicitly selected response, retained only in private runtime.")
    run = sub.add_parser("execute")
    run.add_argument("digest")
    run.add_argument("--confirm", required=True)
    rollback = sub.add_parser("rollback-policy")
    rollback.add_argument("receipt")
    rollback.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = {"ok": True, "policy": load_memory_retrieval_policy(args.runtime_root),
                      "recent_policy_receipts": _read_state(args.runtime_root)["receipts"][-8:],
                      "learning": build_memory_retrieval_learning_observability(_root(args.runtime_root))}
        elif args.command.startswith("review-"):
            result = prepare("policy" if args.command == "review-policy" else "response",
                             runtime_root=args.runtime_root, response=getattr(args, "text", None))
        elif args.command == "execute":
            result = execute(args.digest, args.confirm, runtime_root=args.runtime_root)
        else:
            result = authorize_and_rollback_memory_retrieval_policy(
                args.receipt, operator_confirmation=args.confirm == args.receipt, runtime_root=args.runtime_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"ok": False, "status": "operator_repair_failed_closed", "error_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1
