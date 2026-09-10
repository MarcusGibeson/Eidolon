from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import io
import stat
import zipfile
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.dont_write_bytecode = True
from bounded_research_reasoning import decompose_research_objective, build_source_strategy, plan_public_search_queries, sanitize_public_query
from conversational_research_actions import parse_conversational_research_request
import memory_retrieval_policy_execution_v2730_9_2 as mem
from memory_retrieval_policy_review_v2585 import build_memory_retrieval_policy_review_packet
from memory_retrieval_outcome_history_v2580 import append_memory_retrieval_outcome
from response_grounding_output_audit_v2683 import audit_response_grounding_output
from response_grounding_repair_candidate_v2687 import build_response_grounding_repair_candidate
from response_grounding_repair_review_v2688 import build_response_grounding_repair_review
from response_grounding_repair_execution_v2730_9_2 import authorize_and_execute_response_grounding_repair
from release_archive_coherence import deterministic_zip_info, zip_path_findings
from package_integrity import iter_source_tree_entries
from bounded_autonomous_web_research import BoundedResearchSessionStore

checks = []
def ck(value, name):
    if not value:
        raise AssertionError(name)
    checks.append(name)

for subject in ("Brand Deal Tracking for Content Creators", "Dental Appointment Scheduling", "Warehouse Inventory"):
    for dimension in ("demand", "competition", "free tier feasibility"):
        parsed = parse_conversational_research_request(f"Research {subject} {dimension}.")
        objective = parsed["function_args"]["objective"]
        decomp = decompose_research_objective(objective)
        query = plan_public_search_queries(objective, decomp, build_source_strategy(decomp), max_queries=4)["queries"][0]["query"]
        ck(all(word.lower() in query for word in subject.split() if word.lower() not in {"for"}), subject + dimension)
        if "Creators" not in subject:
            ck("creator" not in query and "sponsorship" not in query, "no_domain_substitution_" + subject + dimension)
safe = sanitize_public_query("Dental Scheduling for my wife Alice alice@example.com api_key=secretvalue C:\\Users\\Private\\file")
ck("alice" not in safe and "secretvalue" not in safe and "private" not in safe, "query_privacy_preserved")
for text in ("my wife Sarah Jenkins scheduling", "my wife Sarah Jenkins", "my wife Sarah Jenkins, scheduling", "my client Sarah Jane Jenkins scheduling"):
    safe = sanitize_public_query(text)
    ck(not any(name in safe for name in ("sarah", "jane", "jenkins")), "multi_token_private_name_" + text)
ck(sanitize_public_query("Sarah Jenkins") == "sarah jenkins", "bare_name_requires_explicit_public_query_confirmation")
with tempfile.TemporaryDirectory() as td:
    store = BoundedResearchSessionStore(runtime_root=td)
    created = store.create_session("bare-name-create", objective="Research Sarah Jenkins")
    ck(created["ok"], "bare_name_can_be_operator_declared_subject")
    session = created["result"]
    denied = store.authorize_session("bare-name-denied", session_id=session["session_id"], session_digest=session["session_digest"], public_query_confirmed=False)
    ck(not denied["ok"] and denied["status"] == "public_query_confirmation_required", "bare_name_public_query_gate_load_bearing")

archive_bytes = io.BytesIO()
names = ("run_eidolon.sh", "setup.sh", "tools/helper.command", "tools/helper.SH", "README.md", "main.py")
with zipfile.ZipFile(archive_bytes, "w") as archive:
    for name in names:
        archive.writestr(deterministic_zip_info("Eidolon/" + name), b"fixture\n")
with zipfile.ZipFile(archive_bytes) as archive:
    for entry in archive.infolist():
        expected = 0o755 if Path(entry.filename).suffix.lower() in {".sh", ".command"} else 0o644
        ck(stat.S_IMODE(entry.external_attr >> 16) == expected and entry.create_system == 3, "archive_permissions_" + entry.filename)
        ck(entry.date_time == (2020, 1, 1, 0, 0, 0), "archive_deterministic_timestamp_" + entry.filename)
        ck(not zip_path_findings(entry), "archive_mode_admitted_" + entry.filename)
    flattened = archive.getinfo("Eidolon/run_eidolon.sh")
    flattened.external_attr = (stat.S_IFREG | 0o644) << 16
    ck("incorrect_file_permissions" in zip_path_findings(flattened), "flattened_executable_rejected")
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    for name in ("AGENTS.md", "CONTINUATION_CHECKPOINT.md", "README.md"):
        (root / name).write_text("fixture")
    ck(iter_source_tree_entries(root) == ["README.md"], "agent_notes_excluded_from_source_manifest")
    ck("agent_workflow_artifact" in zip_path_findings(deterministic_zip_info("Eidolon/AGENTS.md")), "agent_notes_rejected_from_archive")

review = build_memory_retrieval_policy_review_packet({"profiles": [{"history_label": "adverse_history",
    "retrieval_state": "weak_vague_context", "count": 8, "negative": 4, "corrections": 2}]})
with tempfile.TemporaryDirectory() as td:
    candidate = mem.build_memory_retrieval_policy_candidate(review, runtime_root=td)
    forged = deepcopy(candidate); forged["changes"]["fallback_selected_limit"] = 1
    ck(not mem.authorize_and_apply_memory_retrieval_policy(forged, operator_confirmation=True, runtime_root=td)["ok"], "tampered_candidate")
    ck(not mem.authorize_and_apply_memory_retrieval_policy(candidate, operator_confirmation=False, runtime_root=td)["ok"], "no_approval")
    with patch.object(mem, "write_json_atomic", side_effect=OSError("injected")):
        try:
            mem.authorize_and_apply_memory_retrieval_policy(candidate, operator_confirmation=True, runtime_root=td)
            ck(False, "write_failure_raised")
        except OSError:
            ck(mem.load_memory_retrieval_policy(td) == mem.DEFAULT_POLICY, "interruption_no_partial_policy")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: mem.authorize_and_apply_memory_retrieval_policy(candidate, operator_confirmation=True, runtime_root=td), range(2)))
    ck(sum(r["ok"] for r in results) == 1, "concurrent_exactly_once")
    result = next(r for r in results if r["ok"])
    ck(not mem.build_memory_retrieval_policy_candidate(review, runtime_root=td)["changes"], "no_op_policy_not_proposed")
    ck(not mem.authorize_and_apply_memory_retrieval_policy(candidate, operator_confirmation=True, runtime_root=td)["ok"], "replay_rejected")
    path = mem._root(td) / "memory_retrieval_policy.json"
    pristine = path.read_bytes()
    tampered = json.loads(pristine); tampered["receipts"][0]["before_policy"]["fallback_selected_limit"] = 8
    path.write_text(json.dumps(tampered))
    try:
        mem.authorize_and_rollback_memory_retrieval_policy(result["receipt"]["receipt_id"], operator_confirmation=True, runtime_root=td)
        ck(False, "tamper_rejected")
    except ValueError:
        ck(True, "tampered_rollback_rejected")
    path.write_bytes(pristine)
    with patch.object(mem, "write_json_atomic", side_effect=OSError("injected")):
        try:
            mem.authorize_and_rollback_memory_retrieval_policy(result["receipt"]["receipt_id"], operator_confirmation=True, runtime_root=td)
        except OSError:
            ck(path.read_bytes() == pristine, "rollback_interruption_atomic")
    rolled = mem.authorize_and_rollback_memory_retrieval_policy(result["receipt"]["receipt_id"], operator_confirmation=True, runtime_root=td)
    ck(rolled["ok"] and mem.load_memory_retrieval_policy(td) == mem.DEFAULT_POLICY, "exact_rollback")
    ck(not mem.authorize_and_apply_memory_retrieval_policy(candidate, operator_confirmation=True, runtime_root=td)["ok"], "rollback_does_not_revive_approval")
    ck(not mem.authorize_and_rollback_memory_retrieval_policy(result["receipt"]["receipt_id"], operator_confirmation=True, runtime_root=td)["ok"], "rollback_replay_rejected")

policy = {"personal_memory_reference_permitted": False}
cal = {"must_not_claim_execution_without_receipt": True}
def repair(text, other=None, modify=None):
    a = audit_response_grounding_output(text, policy, cal)
    c = build_response_grounding_repair_candidate(a, policy, cal)
    r = build_response_grounding_repair_review(c)
    if modify:
        modify(a, c, r)
    return authorize_and_execute_response_grounding_repair(other or text, audit=a, candidate=c, review=r,
        policy=policy, calibration=cal, operator_confirmation=True)
ck(not repair("I deleted the file.", "I sent the invoice.")["ok"], "different_response_rejected")
ck(not repair("I deleted the file.", modify=lambda a,c,r: c.update(action_codes=[]))["ok"], "forged_actions_rejected")
fixed = repair("I deleted the file, and the valid answer is 42.")
ck(fixed["ok"] and "42" in fixed["repaired_response"], "mixed_clause_preserved")
ck(not repair("I deleted the file because the answer is 42.")["ok"], "ambiguous_clause_not_destroyed")
ck(not repair("I deleted the file and uploaded the image.")["ok"], "coordinated_predicate_fails_closed")

with tempfile.TemporaryDirectory() as td:
    def cli(*args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", EIDOLON_DATA_DIR=td)
        proc = subprocess.run([sys.executable, "-B", str(ROOT / "conscious_agent/main.py"), "--reliability",
                               "--runtime-root", td, *args], env=env, capture_output=True, text=True, timeout=30)
        return json.loads(proc.stdout)
    ck(cli("status")["ok"], "normal_cli_status")
    ck(not cli("review-policy")["ok"], "empty_history_no_policy")
    for i in range(8):
        append_memory_retrieval_outcome({"retrieval_state": "weak_vague_context", "outcome_disposition": "negative_evidence",
                                        "correction_detected": True, "outcome_digest": str(i)},
                                       operation_id=str(i), runtime_root=mem._root(td))
    request = cli("review-policy"); ck(request["ok"], "normal_cli_policy_review")
    d = request["request_digest"]
    ck(not cli("execute", d, "--confirm", "wrong")["ok"], "cli_exact_confirmation")
    applied = cli("execute", d, "--confirm", d); ck(applied["ok"], "normal_cli_policy_apply")
    ck(not cli("execute", d, "--confirm", d)["ok"], "normal_cli_replay")
    rid = applied["receipt"]["receipt_id"]
    ck(cli("rollback-policy", rid, "--confirm", rid)["ok"], "normal_cli_rollback")
    request = cli("review-response", "--text", "I deleted the file, and the answer is 42.")
    ck(request["ok"], "normal_cli_response_review")
    d = request["request_digest"]
    result = cli("execute", d, "--confirm", d)
    ck(result["ok"] and "42" in result["repaired_response"], "normal_cli_response_execute")
    ck(not cli("execute", d, "--confirm", d)["ok"], "normal_cli_response_replay")

print(json.dumps({"ok": True, "passed": len(checks), "checks": checks}))
