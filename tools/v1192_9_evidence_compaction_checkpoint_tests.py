from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1192-9-data-"))

from conscious_agent.api_server import dispatch_api
from conscious_agent.bounded_evidence_compaction import (
    compact_evidence,
    create_evidence_record,
    expand_compaction,
    public_compaction_summary,
    verify_compaction_equivalence,
)
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.evidence_compaction_checkpoint import (
    CONTRACT_VERSION,
    build_evidence_compaction_checkpoint,
)
from conscious_agent.evidence_compaction_reliability import (
    _digest as reliability_digest,
    assess_compaction_reliability,
    create_reliability_record,
    public_reliability_summary,
)
from conscious_agent.evidence_compaction_review import (
    _digest as review_digest,
    create_compaction_review,
    create_compaction_review_request,
    public_compaction_review_summary,
    review_compaction,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


with tempfile.TemporaryDirectory(prefix="eidolon-v1192-9-suite-") as temp:
    report = build_evidence_compaction_checkpoint(
        source_root=ROOT,
        runtime_root=Path(temp) / "runtime",
    )

for key, expected in (
    ("ok", True),
    ("contract_version", "v1192.9"),
    ("checkpoint_id", "bounded-evidence-compaction:v1192.9"),
    ("read_only", True),
    ("post_available", False),
    ("content_free", True),
    ("source_unchanged", True),
    ("runtime_mutated", False),
    ("production_source_modified", False),
    ("original_evidence_preserved", True),
    ("replacement_performed", False),
    ("deletion_performed", False),
    ("automatic_recovery", False),
    ("rollback_invoked", False),
    ("execution_invoked", False),
    ("approval_created", False),
    ("approval_consumed", False),
    ("provider_contacted", False),
    ("model_contacted", False),
    ("thread_started", False),
    ("process_started", False),
    ("installation_invoked", False),
    ("promotion_invoked", False),
    ("publication_invoked", False),
    ("release_invoked", False),
    ("authority_granted", False),
    ("authority_preserved", True),
    ("global_profile_pass_claimed", False),
    ("desktop_verification_deferred_until_v1200", True),
):
    require(report.get(key) == expected)
require(report.get("passed") == report.get("total"))
require(report.get("total", 0) >= 140)
require(len(str(report.get("structural_digest") or "")) == 64)
require(len(report.get("limitations") or []) == 5)
require(report.get("source_file_count", 0) > 2200)

summary = report.get("summary") or {}
for key, expected in (
    ("retained_checkpoint_count", 3),
    ("retained_check_total", 122),
    ("unified_domain_count", 9),
    ("evidence_record_count", 9),
    ("compacted_record_count", 9),
    ("exact_expansion_verified", True),
    ("equivalence_verified", True),
    ("historical_truth_preserved", True),
    ("uncertainty_truth_preserved", True),
    ("approval_truth_preserved", True),
    ("rollback_truth_preserved", True),
    ("authority_separation_preserved", True),
    ("review_decision_count", 3),
    ("approved_review_count", 1),
    ("rejected_review_count", 1),
    ("deferred_review_count", 1),
    ("reliability_event_count", 8),
    ("blocked_case_count", 4),
    ("original_evidence_preserved", True),
    ("content_free", True),
):
    require(summary.get(key) == expected)
for name in ("stale-compaction", "compaction-tamper", "private-review", "replay"):
    require(name in (report.get("blocked_cases") or {}))
    require(bool((report.get("blocked_cases") or {}).get(name)))

snapshot = digest({"suite": "v1192.9", "snapshot": 1})
context = digest({"suite": "v1192.9", "context": 1})
domains = ("conversation", "cognition", "reasoning", "planning", "campaign", "approval", "action", "result", "learning")
kinds = ("observation", "observation", "decision", "decision", "transition", "decision", "transition", "result", "learning")
outcomes = ("retained", "revised", "retained", "suspended", "completed", "retained", "completed", "completed", "revised")
uncertainty = ("none", "bounded", "conflicted", "unresolved", "bounded", "none", "bounded", "none", "bounded")
approval = ("not_required", "not_required", "review_required", "deferred", "approved", "approved", "approved", "approved", "review_required")
rollback = ("not_applicable", "not_applicable", "available", "available", "verified", "available", "verified", "verified", "available")
records: list[dict[str, object]] = []
previous = ""
for sequence, domain in enumerate(domains):
    row = create_evidence_record(
        evidence_id=f"v1192.9-suite-{domain}",
        sequence=sequence,
        previous_evidence_digest=previous,
        snapshot_digest=snapshot,
        context_digest=context,
        artifact_digest=digest({"artifact": domain}),
        receipt_digest=digest({"receipt": domain}),
        domain=domain,
        evidence_kind=kinds[sequence],
        outcome=outcomes[sequence],
        uncertainty_code=uncertainty[sequence],
        approval_state=approval[sequence],
        rollback_state=rollback[sequence],
    )
    records.append(row)
    previous = str(row["evidence_digest"])
    require(row["sequence"] == sequence)
    require(row["domain"] == domain)
    require(row["authority_state"] == "separate_not_granted")
    require(len(str(row["evidence_digest"])) == 64)
require(len(records) == 9)
require(len({str(row["evidence_id"]) for row in records}) == 9)
require(records[0]["previous_evidence_digest"] == "")
require(records[-1]["previous_evidence_digest"] == records[-2]["evidence_digest"])

compacted = compact_evidence(records, snapshot_digest=snapshot, context_digest=context)
require(compacted["status"] == "compacted")
require(compacted["errors"] == [])
require(compacted["lossless_claim"] is True)
require(compacted["content_free"] is True)
require(compacted["execution_invoked"] is False)
require(compacted["approval_consumed"] is False)
require(compacted["rollback_invoked"] is False)
require(compacted["authority_granted"] is False)
require(len(compacted["compaction_digest"]) == 64)
require(compacted["compaction"]["record_count"] == 9)
require(compacted["compaction"]["first_sequence"] == 0)
require(compacted["compaction"]["last_sequence"] == 8)
require(compacted["compaction"]["terminal_evidence_digest"] == records[-1]["evidence_digest"])

expanded = expand_compaction(
    compacted,
    expected_snapshot_digest=snapshot,
    expected_context_digest=context,
)
require(expanded["status"] == "expanded")
require(expanded["records"] == records)
require(expanded["record_count"] == 9)
require(expanded["content_free"] is True)
require(expanded["execution_invoked"] is False)
require(expanded["authority_granted"] is False)

equivalence = verify_compaction_equivalence(
    records,
    compacted,
    snapshot_digest=snapshot,
    context_digest=context,
)
for key in (
    "equivalent",
    "historical_truth_preserved",
    "approval_truth_preserved",
    "rollback_truth_preserved",
    "uncertainty_truth_preserved",
    "authority_separation_preserved",
):
    require(equivalence[key] is True)
require(equivalence["status"] == "equivalent")
require(equivalence["record_count"] == 9)
require(equivalence["original_digest"] == equivalence["expanded_digest"])
require(equivalence["execution_invoked"] is False)
require(equivalence["authority_granted"] is False)
public = public_compaction_summary(compacted, equivalence)
require(public["status"] == "compacted")
require(public["record_count"] == 9)
require(public["equivalent"] is True)
require(public["content_free"] is True)
require(public["authority_granted"] is False)

# Stale/tamper/broken lineage/private/oversized cases remain blocked.
require(expand_compaction(compacted, expected_snapshot_digest=digest("stale"), expected_context_digest=context)["status"] == "blocked")
require("stale_compaction_snapshot" in expand_compaction(compacted, expected_snapshot_digest=digest("stale"), expected_context_digest=context)["errors"])
require("stale_compaction_context" in expand_compaction(compacted, expected_snapshot_digest=snapshot, expected_context_digest=digest("stale"))["errors"])
tampered = dict(compacted)
tampered["compaction_digest"] = "0" * 64
require("compaction_tamper" in expand_compaction(tampered, expected_snapshot_digest=snapshot, expected_context_digest=context)["errors"])
for mutation, expected_error in (
    ((1, "previous_evidence_digest", digest("wrong")), "broken_lineage"),
    ((1, "evidence_id", records[0]["evidence_id"]), "duplicate_evidence_id"),
    ((1, "sequence", 0), "duplicate_sequence"),
    ((1, "authority_state", "granted"), "authority_expansion"),
):
    index, field, value = mutation
    bad = [dict(row) for row in records]
    bad[index][field] = value
    if field != "evidence_digest":
        candidate = dict(bad[index])
        candidate.pop("evidence_digest", None)
        bad[index]["evidence_digest"] = digest(candidate)
    blocked = compact_evidence(bad, snapshot_digest=snapshot, context_digest=context)
    require(blocked["status"] == "blocked")
    require(expected_error in blocked["errors"])
bad = [dict(row) for row in records]
bad[1]["prompt"] = "private"
blocked = compact_evidence(bad, snapshot_digest=snapshot, context_digest=context)
require(blocked["status"] == "blocked")
require("private_field" in blocked["errors"])
oversized = records * 8
blocked = compact_evidence(oversized, snapshot_digest=snapshot, context_digest=context)
require(blocked["status"] == "blocked")
require("oversized_evidence" in blocked["errors"])

# Review decisions bind the exact equivalent compaction but never alter originals.
equivalence_digest = digest({
    "original_digest": equivalence["original_digest"],
    "expanded_digest": equivalence["expanded_digest"],
    "record_count": equivalence["record_count"],
})
request = create_compaction_review_request(
    request_id="v1192.9-suite-review-request",
    compaction_digest=compacted["compaction_digest"],
    terminal_evidence_digest=records[-1]["evidence_digest"],
    snapshot_digest=snapshot,
    context_digest=context,
    record_count=9,
    equivalence_digest=equivalence_digest,
)
require(request["content_free"] is True)
for field in ("replacement_requested", "deletion_requested", "execution_requested", "automatic_acceptance", "authority_requested"):
    require(request[field] is False)
for decision, status in (("approve", "review_approved"), ("reject", "review_rejected"), ("defer", "review_deferred")):
    review = create_compaction_review(
        request_digest=request["request_digest"],
        decision=decision,
        review_id=f"v1192.9-suite-review-{decision}",
        operator_review_digest=digest({"review": decision}),
    )
    result = review_compaction(
        request=request,
        review=review,
        current_snapshot_digest=snapshot,
        current_context_digest=context,
        current_compaction_digest=compacted["compaction_digest"],
        current_terminal_evidence_digest=records[-1]["evidence_digest"],
        equivalence_verified=True,
    )
    require(result["status"] == status)
    require(result["original_evidence_preserved"] is True)
    require(result["equivalence_verified"] is True)
    require(result["replacement_performed"] is False)
    require(result["deletion_performed"] is False)
    require(result["runtime_modified"] is False)
    require(result["execution_invoked"] is False)
    require(result["approval_created"] is False)
    require(result["approval_consumed"] is False)
    require(result["provider_contacted"] is False)
    require(result["model_contacted"] is False)
    require(result["thread_started"] is False)
    require(result["process_started"] is False)
    require(result["authority_granted"] is False)
    summary_review = public_compaction_review_summary(result)
    require(summary_review["content_free"] is True)
    require(summary_review["compaction_retention_presented"] is (decision == "approve"))

review = create_compaction_review(
    request_digest=request["request_digest"],
    decision="approve",
    review_id="v1192.9-suite-blocked-review",
    operator_review_digest=digest("blocked-review"),
)
def review_case(req: dict[str, object] = request, **current: object) -> dict[str, object]:
    return review_compaction(
        request=req,
        review=review,
        current_snapshot_digest=str(current.get("snapshot", snapshot)),
        current_context_digest=str(current.get("context", context)),
        current_compaction_digest=str(current.get("compaction", compacted["compaction_digest"])),
        current_terminal_evidence_digest=str(current.get("terminal", records[-1]["evidence_digest"])),
        equivalence_verified=bool(current.get("equivalent", True)),
    )
for result, expected_error in (
    (review_case(snapshot=digest("stale")), "stale_snapshot"),
    (review_case(context=digest("stale")), "stale_context"),
    (review_case(compaction=digest("stale")), "stale_compaction"),
    (review_case(terminal=digest("stale")), "stale_terminal_evidence"),
    (review_case(equivalent=False), "equivalence_not_verified"),
):
    require(result["status"] == "blocked")
    require(expected_error in result["errors"])
    require(result["replacement_performed"] is False)
    require(result["authority_granted"] is False)
for field in ("replacement_requested", "deletion_requested", "execution_requested", "automatic_acceptance", "authority_requested"):
    bad = dict(request)
    bad[field] = True
    bad.pop("request_digest", None)
    bad["request_digest"] = review_digest(bad)
    bad_review = create_compaction_review(
        request_digest=bad["request_digest"],
        decision="approve",
        review_id=f"v1192.9-hidden-{field}",
        operator_review_digest=digest(field),
    )
    result = review_compaction(
        request=bad,
        review=bad_review,
        current_snapshot_digest=snapshot,
        current_context_digest=context,
        current_compaction_digest=compacted["compaction_digest"],
        current_terminal_evidence_digest=records[-1]["evidence_digest"],
        equivalence_verified=True,
    )
    require(result["status"] == "blocked")
    require("hidden_mutation_or_authority_claim" in result["errors"])

# Reliability chain covers all supported event classes without performing recovery.
reliability_rows: list[dict[str, object]] = []
previous = ""
for sequence, (event_type, action) in enumerate((
    ("interruption", "preserve"),
    ("restart", "review_required"),
    ("stale_compaction", "rebuild_required"),
    ("replay", "reject"),
    ("privacy", "reject"),
    ("tamper", "reject"),
    ("outage", "defer"),
    ("recovery_review", "review_required"),
)):
    row = create_reliability_record(
        record_id=f"v1192.9-suite-reliability-{event_type}",
        event_type=event_type,
        action=action,
        compaction_digest=compacted["compaction_digest"],
        terminal_evidence_digest=records[-1]["evidence_digest"],
        snapshot_digest=snapshot,
        context_digest=context,
        review_digest=digest({"event": event_type, "sequence": sequence}),
        sequence=sequence,
        previous_record_digest=previous,
    )
    reliability_rows.append(row)
    previous = str(row["record_digest"])
    require(row["automatic_recovery"] is False)
    require(row["replacement_performed"] is False)
    require(row["deletion_performed"] is False)
    require(row["execution_invoked"] is False)
    require(row["authority_granted"] is False)
reliability = assess_compaction_reliability(
    records=reliability_rows,
    current_compaction_digest=compacted["compaction_digest"],
    current_terminal_evidence_digest=records[-1]["evidence_digest"],
    current_snapshot_digest=snapshot,
    current_context_digest=context,
)
for key, expected in (
    ("ok", True),
    ("status", "reliability_verified"),
    ("record_count", 8),
    ("interruption_count", 1),
    ("restart_count", 1),
    ("replay_detected", False),
    ("original_evidence_preserved", True),
    ("content_free", True),
    ("automatic_recovery", False),
    ("replacement_performed", False),
    ("deletion_performed", False),
    ("execution_invoked", False),
    ("provider_contacted", False),
    ("model_contacted", False),
    ("thread_started", False),
    ("process_started", False),
    ("runtime_modified", False),
    ("authority_granted", False),
):
    require(reliability[key] == expected)
require(public_reliability_summary(reliability)["content_free"] is True)
for key, current in (
    ("comp", digest("stale")),
    ("term", digest("stale")),
    ("snap", digest("stale")),
    ("ctx", digest("stale")),
):
    kwargs = {
        "current_compaction_digest": compacted["compaction_digest"],
        "current_terminal_evidence_digest": records[-1]["evidence_digest"],
        "current_snapshot_digest": snapshot,
        "current_context_digest": context,
    }
    names = {"comp": "current_compaction_digest", "term": "current_terminal_evidence_digest", "snap": "current_snapshot_digest", "ctx": "current_context_digest"}
    kwargs[names[key]] = current
    blocked = assess_compaction_reliability(records=reliability_rows, **kwargs)
    require(blocked["status"] == "blocked")
    require(blocked["execution_invoked"] is False)
    require(blocked["authority_granted"] is False)
replay_rows = [dict(row) for row in reliability_rows]
replay_rows[1]["review_digest"] = replay_rows[0]["review_digest"]
replay_rows[1].pop("record_digest", None)
replay_rows[1]["record_digest"] = reliability_digest(replay_rows[1])
replay = assess_compaction_reliability(
    records=replay_rows,
    current_compaction_digest=compacted["compaction_digest"],
    current_terminal_evidence_digest=records[-1]["evidence_digest"],
    current_snapshot_digest=snapshot,
    current_context_digest=context,
)
require(replay["status"] == "blocked")
require(replay["replay_detected"] is True)
require("replay_detected" in replay["errors"])
private_rows = [dict(row) for row in reliability_rows]
private_rows[2]["prompt"] = "private"
private = assess_compaction_reliability(
    records=private_rows,
    current_compaction_digest=compacted["compaction_digest"],
    current_terminal_evidence_digest=records[-1]["evidence_digest"],
    current_snapshot_digest=snapshot,
    current_context_digest=context,
)
require(private["status"] == "blocked")
require("private_or_authority_content_present" in private["errors"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "evidence-compaction-checkpoint"), None)
require(row is not None)
require((row or {}).get("contract_version") == CONTRACT_VERSION)
require((row or {}).get("builder") == "build_evidence_compaction_checkpoint")
require((row or {}).get("read_only") is True)
require((row or {}).get("post_available") is False)
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))
for checkpoint_id in (
    "bounded-evidence-compaction-checkpoint",
    "evidence-compaction-review-checkpoint",
    "evidence-compaction-reliability-checkpoint",
    "evidence-compaction-checkpoint",
):
    require(any(item.get("checkpoint_id") == checkpoint_id for item in registry.get("checkpoints", [])))

proc = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "evidence-compaction-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1192-9-cli-"),
    },
)
require(proc.returncode == 0)
try:
    cli = json.loads(proc.stdout.strip().splitlines()[-1])
    require(cli.get("ok") is True)
    require(cli.get("contract_version") == "v1192.9")
    require((cli.get("summary") or {}).get("exact_expansion_verified") is True)
except Exception:
    require(False)
    require(False)
    require(False)

status, payload = dispatch_api("GET", "/api/cognition/evidence-compaction-checkpoint")
require(status == 200)
require(payload.get("ok") is True)
require((payload.get("data") or {}).get("contract_version") == "v1192.9")
require(((payload.get("data") or {}).get("summary") or {}).get("original_evidence_preserved") is True)
status_post, _ = dispatch_api("POST", "/api/cognition/evidence-compaction-checkpoint")
require(status_post in {404, 405})

html = render_first_use_shell()
require("evidence-compaction-checkpoint-panel" in html)
require("bounded-evidence-compaction-checkpoint-panel" in html)
require("evidence-compaction-review-checkpoint-panel" in html)
require("evidence-compaction-reliability-checkpoint-panel" in html)
require("/api/cognition/evidence-compaction-checkpoint" in html)
require("next v1193" in html.lower())

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1192.9-bounded-evidence-compaction-checkpoint") == 1)
require(release.count("v1192_9_evidence_compaction_checkpoint_tests.py") == 1)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1192.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1192.8"' in metadata)
require("v1192.9 Bounded Evidence Compaction Checkpoint" in metadata)
require("v1193.0-v1193.2 Verifier Ownership and Historical-Debt Foundations" in metadata)
require('WORKING_SOURCE_VERSION = "1192.8"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1192.5"' in metadata)

for name in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    require("v1192.9 Bounded Evidence Compaction Checkpoint" in text)
    require("v1192.9 Bounded Evidence Compaction Checkpoint" in text)
    require("exact expansion and equivalence" in text)
    require("approve/reject/defer operator review" in text)
    require("Original evidence is never replaced, deleted, or rewritten" in text)
    require("v1193.0-v1193.2 Verifier Ownership and Historical-Debt Foundations" in text)
    require("v1200" in text)
    require("Current source: v1192.8" in text)
    require("Current source: v1192.5" in text)

result = {
    "suite": "v1192.9-bounded-evidence-compaction-checkpoint",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
    "global_profile_pass_claimed": False,
    "production_source_modified_by_checkpoint": False,
    "original_evidence_replaced": False,
    "automatic_recovery_invoked": False,
    "authority_expanded": False,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
