from __future__ import annotations

"""Build and verify the non-authorizing G-ROUTE3 execution-freeze candidate."""

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

from g_route1_contract import ROOT, digest_file
from g_route3_contract import (DATA, EXPECTED_CALLS, EXECUTION_FREEZE_PATH, json_digest, load_corpus, load_gold,
                               load_json, load_model_bindings, load_thresholds, verify_checked_schedule)

CONTRACT_VERSION = "g-route3.execution-freeze-candidate.v7"
CANDIDATE_ID = "G-ROUTE3-EXECUTION-R7"
DATA_ROOT = r"C:\Users\marcu\AppData\Local\Eidolon\research\g_route3"   # pinned literally (B-O9, §3)
SUPERSEDED = (
    {"candidate_id": "G-ROUTE3-EXECUTION-R1",
     "path": "experiments/G-ROUTE3-candidate/EXECUTION_FREEZE_CANDIDATE_R1.json",
     "literal_sha256": "b63f0094bbba9c3e822a359cb92b56f66f3ff244e29bbc834ce9af42a4f1653c",
     "binding_sha256": "64eed1ba1a6bb40faa0277f363f4027c09056ef909e6a31bdf71e8ad5ffe3c21",
     "review_record": "experiments/G-ROUTE3-candidate/EXTERNAL_REVIEW_ROUND1.md",
     "reason": ("independent pre-contact review returned FINDINGS: hidden grader rules in conversation, "
                "coding and planning, ambiguous gold, a trigger that fired on correct answers, template "
                "reuse between corpora, a gate that could mask failure, weak table provenance, and a freeze "
                "check that made Phase B impossible to authorize"),
     "authorized": False, "provider_generation_calls": 0},
    {"candidate_id": "G-ROUTE3-EXECUTION-R2",
     "path": "experiments/G-ROUTE3-candidate/EXECUTION_FREEZE_CANDIDATE_R2.json",
     "literal_sha256": "b029632eae910a2f261508e9710e4dbd5620760baac405cf350bf11ebd56d83f",
     "binding_sha256": "aa5db17af6e12aaf1453cdbd1c88940743cb8712882c8a7ccba2a6541bfd52af",
     "review_record": "experiments/G-ROUTE3-candidate/EXTERNAL_REVIEW_ROUND2.md",
     "reason": ("second independent pre-contact review returned FINDINGS: Phase A provenance could be fabricated "
                "from unsealed fields, the one-shot authorization could be reused under a new key or run root, "
                "conversation anchors still rejected correct and accepted wrong replies, coding rejected a "
                "correct fix whose old lacked the final newline, and several runtime dependencies were unguarded"),
     "authorized": False, "provider_generation_calls": 0},
    {"candidate_id": "G-ROUTE3-EXECUTION-R3",
     "path": "experiments/G-ROUTE3-candidate/EXECUTION_FREEZE_CANDIDATE_R3.json",
     "literal_sha256": "dbbb473d26f0f24ef98d2f5b7119ce2d2f4e8c13060bc0c440cb8bfc8e69a536",
     "binding_sha256": "f92fd6e0a628864a7da9a842642ec2e3fd79c81685f9fce3c0a817dbed721397",
     "review_record": "experiments/G-ROUTE3-candidate/EXTERNAL_REVIEW_ROUND3.md",
     "reason": ("third independent pre-contact review returned FINDINGS: one authorization could drive several "
                "complete runs by changing the run root, the authorized path accepted any provider, a synthetic run "
                "could be relabelled with one resealed receipt, complete attempts could be repeated best-of-N, the "
                "conversation action-claim pattern failed in both directions, and synthesis graded keywords the "
                "model was never shown"),
     "authorized": False, "provider_generation_calls": 0},
    {"candidate_id": "G-ROUTE3-EXECUTION-R4",
     "path": "experiments/G-ROUTE3-candidate/EXECUTION_FREEZE_CANDIDATE_R4.json",
     "literal_sha256": "555c45b59f1e9892a8482c09bbe9129bc866539749879229cdbe9004388a16bb",
     "binding_sha256": "3660f60f459ef7a0b3dc1e86bd50aec397d1233e7a235665989ad91195b727b3",
     "review_record": "experiments/G-ROUTE3-candidate/EXTERNAL_REVIEW_ROUND4.md",
     "reason": ("fourth independent pre-contact review returned FINDINGS: the Actions taken field accepted a trailing "
                "note that could carry an action and rejected natural no-action forms, malformed model output could "
                "crash collection so Phase A could never finish, an interrupted finalization could deadlock an "
                "attempt, and cheap ledger tampering or a redirected endpoint was not tamper-evident"),
     "authorized": False, "provider_generation_calls": 0},
    {"candidate_id": "G-ROUTE3-EXECUTION-R5",
     "path": "experiments/G-ROUTE3-candidate/EXECUTION_FREEZE_CANDIDATE_R5.json",
     "literal_sha256": "55c40f1633d5c4b2a29ed97218580750e54d07f9eb19979bb5dd0de40ae7e467",
     "binding_sha256": "2e97b75e0b3ce68bd2cd21fd5cbcc69f6133abaa736727b62452d729061fce94",
     "review_record": "experiments/G-ROUTE3-candidate/EXTERNAL_REVIEW_ROUND5.md",
     "reason": ("fifth independent pre-contact review returned FINDINGS: a pathological coding candidate raised "
                "before the sandbox subprocess and was charged to infrastructure, stopping Phase A, and several "
                "crash windows during finalization left an attempt unrecoverable by any supported command"),
     "authorized": False, "provider_generation_calls": 0},
    {"candidate_id": "G-ROUTE3-EXECUTION-R6",
     "path": "experiments/G-ROUTE3-candidate/EXECUTION_FREEZE_CANDIDATE_R6.json",
     "literal_sha256": "8d64f703dadeb9787ba64ffd832e0134668cb644ab54de4a06eda8cfc100a085",
     "binding_sha256": "2e5e8cc72570b6be1dd92b1bebe80d0366b3b1c489fb75a8d1f4404886e062e3",
     "review_record": "experiments/G-ROUTE3-candidate/EXTERNAL_REVIEW_ROUND6.md",
     "reason": ("sixth independent pre-contact review returned FINDINGS: model output could crash sealing, torn "
                "files and interrupted anchors wedged recovery, and resume could not reopen terminal activity; "
                "the operator chose to restructure the lifecycle around one journal per run (R7)"),
     "authorized": False, "provider_generation_calls": 0},
)
FREEZE_PATH = EXECUTION_FREEZE_PATH
ARTIFACTS = tuple(f"experiments/G-ROUTE3-candidate/{name}" for name in (
    "DESIGN.md", "GOLD_DERIVABILITY.md", "GOLD_DERIVABILITY_DIAGNOSTIC.json", "QUALIFICATION_CONTRACT.md",
    "ROUTING_POLICY.md", "SCORING_CONTRACT.md", "CONTAMINATION_ANALYSIS.md", "PRODUCTION_ADAPTER_MAPPING.md",
    "INDEPENDENT_AUDIT.md", "DETERMINISTIC_TEST_RESULTS.json", "INDEPENDENCE_REPORT.json",
    "EXTERNAL_REVIEW_ROUND1.md", "EXECUTION_FREEZE_CANDIDATE_R1.json",
    "EXTERNAL_REVIEW_ROUND2.md", "EXECUTION_FREEZE_CANDIDATE_R2.json",
    "EXTERNAL_REVIEW_ROUND3.md", "EXECUTION_FREEZE_CANDIDATE_R3.json",
    "EXTERNAL_REVIEW_ROUND4.md", "EXECUTION_FREEZE_CANDIDATE_R4.json",
    "EXTERNAL_REVIEW_ROUND5.md", "EXECUTION_FREEZE_CANDIDATE_R5.json",
    "EXTERNAL_REVIEW_ROUND6.md", "EXECUTION_FREEZE_CANDIDATE_R6.json",
    "R7_LIFECYCLE_DESIGN.md", "R7_DESIGN_REVIEW_CANDIDATE.json", "R7_IMPLEMENTATION_OBLIGATIONS.md",
    "R7_DESIGN_REVIEW_ROUND1.md", "R7_DESIGN_REVIEW_ROUND2.md", "R7_DESIGN_REVIEW_ROUND3.md",
    "R7_DESIGN_REVIEW_ROUND4.md", "R7_DESIGN_REVIEW_ROUND5.md", "R7_DESIGN_REVIEW_ROUND6.md",
    "R7_DESIGN_REVIEW_ROUND7.md", "R7_DESIGN_REVIEW_ROUND8.md", "R7_IMPLEMENTATION_STATUS.md",
    "R7_CERTIFICATION_REPORT.json",
    "corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json", "fixture_design.json",
    "model_bindings.json", "thresholds.json", "schedule_a.json", "schedule_b.json",
    "authoring/author_g3_part1.py", "authoring/author_g3_part2.py", "authoring/author_g3_part3.py",
    "authoring/author_g3_part3_round2.py", "authoring/assemble_g3.py",
)) + (
    "experiments/G-ROUTE1-candidate/prompt_profiles.json", "experiments/G-ROUTE1-candidate/model_bindings.json",
    "tools/g_route3_launch.py",
    "tools/g_route1_contract.py", "tools/g_route1_validators.py", "tools/g_route1_operational.py",
    "tools/g_route1_execution_contract.py", "tools/g_route1_freeze.py", "conscious_agent/activity.py",
    "conscious_agent/json_storage.py", "conscious_agent/metadata_mutation_coordination.py",
    "tools/g_route3_conversation.py", "tools/g_route3_semantics.py",
    "tools/g_route1_coding_runner.py", "tools/g_route1_persistence.py", "tools/g_route1_provider.py",
    "tools/g_route2_normalization.py", "tools/g_route3_operational.py", "tools/g_route3_triggers.py",
    "tools/g_route3_contract.py", "tools/g_route3_qualification.py", "tools/g_route3_routing.py",
    "tools/g_route3_validation.py", "tools/g_route3_runner.py", "tools/g_route3_independence.py",
    "tools/g_route3_tests.py", "tools/g_route3_freeze.py",
    "tools/g_route3_platform.py", "tools/g_route3_fs.py", "tools/g_route3_journal.py", "tools/g_route3_evidence.py",
    "tools/g_route3_lifecycle.py", "tools/g_route3_worker.py", "tools/g_route3_scorer.py",
    "tools/g_route3_campaign.py", "tools/g_route3_r7_tests.py",
)


def measure_recursion_thresholds() -> dict[str, int]:
    """C-O2: the near-limit thresholds at the pinned budget, measured in a fresh pinned thread (§1.2, §8)."""
    import json as _json
    import g_route3_platform as platform
    from g_route1_coding_runner import validate_candidate_ast
    from g_route1_validators import coding_candidate_source
    from g_route3_contract import runtime_fixtures

    platform.pin_recursion_limit()
    fixture = next(f for f in runtime_fixtures("A").values() if f["validator_profile"] == "coding.v1")

    def json_ok(depth: int) -> bool:
        try:
            _json.loads("[" * depth + "]" * depth)
            return True
        except RecursionError:
            return False

    def ast_ok(terms: int) -> bool:
        output = {"path": fixture["input"]["allowed_path"], "old": fixture["input"]["source"],
                  "new": "value = " + " + ".join(["1"] * terms) + "\n"}
        try:
            validate_candidate_ast(coding_candidate_source(fixture["input"], output))
            return True
        except RecursionError:
            return False
        except Exception:  # noqa: BLE001 - any other rejection is not the recursion band
            return True

    def highest(check, low: int, high: int) -> int:
        while low < high:
            middle = (low + high + 1) // 2
            if platform.run_pinned(check, middle):
                low = middle
            else:
                high = middle - 1
        return low

    return {"json_nesting_max": highest(json_ok, 100, 5000), "ast_binary_chain_terms_max": highest(ast_ok, 100, 20000),
            "recursion_limit": platform.RECURSION_LIMIT, "stack_bytes": platform.PINNED_STACK_BYTES}


def literal_sha256(path: Path) -> str:
    """sha256 of the file's bytes with CRLF and CR normalized to LF, so a git checkout's line endings do not matter."""
    import hashlib
    data = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def current_commit(root: Path = ROOT) -> str:
    return subprocess.run(["git", "-c", "safe.directory=C:/Users/marcu/Eidolon", "rev-parse", "HEAD"],
                          cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def build_manifest(*, implementation_commit: str | None = None, root: Path = ROOT) -> dict[str, Any]:
    for prior in SUPERSEDED:
        superseded = root / prior["path"]
        if not superseded.is_file() or literal_sha256(superseded) != prior["literal_sha256"]:
            raise ValueError(f"superseded_freeze_not_preserved:{prior['candidate_id']}")
    missing = [path for path in ARTIFACTS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("execution_freeze_artifacts_missing:" + ",".join(missing))
    for corpus in ("A", "B"):
        load_corpus(corpus)
        load_gold(corpus)
    schedules = {corpus: verify_checked_schedule(corpus) for corpus in ("A", "B")}
    independence = load_json(DATA / "INDEPENDENCE_REPORT.json")
    if independence.get("valid") is not True:
        raise ValueError("independence_report_not_clean")
    models = load_model_bindings()
    thresholds = load_thresholds()
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": CANDIDATE_ID,
        "status": "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION",
        "implementation_commit": implementation_commit or current_commit(root),
        "supersedes": [dict(prior) for prior in SUPERSEDED],
        "research_questions": {
            "primary": ("Can a task x risk x model qualification table derived prospectively from one independent "
                        "qualification corpus safely guide cheapest-qualified model selection and stopping on a "
                        "separate unseen validation corpus?"),
            "secondary": ("When a qualified model's individual output fails deterministic validation, can escalation "
                          "to the next independently qualified tier improve usable admission without creating unsafe stops?"),
        },
        "phases": {
            "A": {"corpus": "G-ROUTE3-CORPUS-A", "role": "qualification", "planned_calls": EXPECTED_CALLS["A"],
                  "schedule_sha256": json_digest(schedules["A"]),
                  "authorization_format": ("Authorize G-ROUTE3 phase A execution <execution_freeze_binding> "
                                           "attempt <n>"),
                  "attempts": "numbered from 1; each attempt is a separate explicit authorization recorded in "
                              "the fixed authorization ledger, and the table discloses every Phase A attempt"},
            "B": {"corpus": "G-ROUTE3-CORPUS-B", "role": "validation", "planned_calls": EXPECTED_CALLS["B"],
                  "schedule_sha256": json_digest(schedules["B"]),
                  "authorization_format": ("Authorize G-ROUTE3 phase B execution <execution_freeze_binding> "
                                           "table <qualification_table_sha256> attempt <n>"),
                  "requires_frozen_audited_qualification_table": True},
        },
        "corpus_digests": {name: digest_file(root / f"experiments/G-ROUTE3-candidate/{name}")
                           for name in ("corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json")},
        "both_corpora_frozen_before_any_contact": True,
        "qualification_table_exists": False,
        "model_bindings_sha256": json_digest(models),
        "thresholds_sha256": json_digest(thresholds),
        "independence_report_sha256": digest_file(DATA / "INDEPENDENCE_REPORT.json"),
        "model_identities": [{"tier": r["tier"], "model": r["model"], "manifest_digest": r["manifest_digest"],
                              "model_blob_sha256": r["model_blob_sha256"]} for r in models["bindings"]],
        "generation_configuration": models["generation_configuration"],
        "normalization_contract": "g-route2.transport-normalization.v1",
        "validator_contract": "g-route1.validators.v1",
        "operational_validator_contract": "g-route3.operational-validator.v2",
        "semantic_contract": "g-route3.semantics.v1",
        "conversation_contract": "g-route3.conversation-frame.v3",
        "runner_contract": "g-route3.runner.v5 (R6 authorized path superseded; synthetic path kept)",
        "lifecycle_contract": "g-route3.lifecycle.r7",
        "data_root": DATA_ROOT,
        "recursion_thresholds": measure_recursion_thresholds(),
        "threat_model": ("operator ruling 10: accidents in code, tampering at boundaries. The code guarantees "
                         "at-most-once and a truthful history against accidents and misuse of supported commands; "
                         "every attempt's journal is committed to the private evidence repository at its "
                         "boundaries and verified by every command; tampering with an attempt in progress is a "
                         "declared residual"),
        "launcher": {"contract": "g-route3.launcher.v4", "path": "tools/g_route3_launch.py",
                     "provider_endpoint": "http://127.0.0.1:11434 (fixed)",
                     "sentences": "R7_LIFECYCLE_DESIGN.md §7.1 (no Close sentence: ruling 11)",
                     "authorized_runs_only_through_launcher": True, "data_root": DATA_ROOT},
        "attempt_policy": ("R7 §9.3: numbered attempts, each separately authorized, spanning every freeze; attempt "
                           "n+1 only after every earlier attempt is closed or closed at ledger level; refused while "
                           "a completed or protected attempt exists; every attempt disclosed, every non-complete "
                           "attempt flagged 'optional stopping cannot be excluded'"),
        "semantic_validators_unchanged_from_g_route1": ("research, synthesis, extraction and planning: yes; "
                                                        "conversation: replaced by the disclosed two-line frame "
                                                        "(Answer, Actions taken); "
                                                        "coding: unchanged except that old is compared with the "
                                                        "source ignoring trailing newlines"),
        "trigger_contract": "g-route3.triggers.v1",
        "evidence_scale": "pilot",
        "digest_convention": "sha256; CRLF and CR normalized to LF for source artifacts",
        "artifacts": {path: digest_file(root / path) for path in ARTIFACTS},
        "prior_experiments_modified": False,
        "execution_freeze": True,
        "benchmark_execution_authorized": False,
        "provider_generation_authorized": False,
        "production_routing_authorized": False,
        "automatic_escalation_authorized": False,
        "source_mutation_authorized": False,
        "authorization_artifact_created": False,
        "belief_effects": "none",
        "provider_generation_calls": 0,
        "benchmark_launches": 0,
        "deterministic_tests_passed": True,
        "independent_audit_verdict": "READY",
        "independent_audit_is_author_self_audit": True,
        "external_reviews": [{"round": index, "verdict": "FINDINGS", "reviewed_binding": prior["binding_sha256"],
                              "record": prior["review_record"]} for index, prior in enumerate(SUPERSEDED, 1)],
        "external_review_required_before_authorization": True,
    }
    seed["execution_freeze_content_sha256"] = json_digest(seed)
    return seed


def verify_manifest(manifest: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        expected = build_manifest(implementation_commit=str(manifest.get("implementation_commit") or ""), root=root)
    except Exception as exc:
        return {"valid": False, "reasons": [f"freeze_rebuild_failed:{type(exc).__name__}:{exc}"], "authorized": False}
    if dict(manifest) != expected:
        reasons += [f"manifest_mismatch:{key}" for key in sorted(set(expected) | set(manifest))
                    if expected.get(key) != manifest.get(key)]
    for key in ("benchmark_execution_authorized", "provider_generation_authorized", "production_routing_authorized",
                "automatic_escalation_authorized", "source_mutation_authorized", "authorization_artifact_created"):
        if manifest.get(key) is not False:
            reasons.append(f"authority_must_remain_false:{key}")
    if manifest.get("provider_generation_calls") != 0 or manifest.get("benchmark_launches") != 0:
        reasons.append("execution_count_nonzero")
    if manifest.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")
    return {"valid": not reasons, "reasons": sorted(set(reasons)), "status": manifest.get("status"),
            "authorized": False, "candidate_id": manifest.get("candidate_id"),
            "provider_generation_calls": manifest.get("provider_generation_calls"),
            "benchmark_launches": manifest.get("benchmark_launches"),
            "independent_audit_verdict": manifest.get("independent_audit_verdict")}


def data_root_refusals(data_root: Path) -> list[str]:
    """R7 §9.3: the freeze writer refuses once D holds a table, or a completed, protected or in-progress attempt.
    It follows J8 (lease, verification, replay) and refuses on unreadable files (B-O3)."""
    import g_route3_fs as fsmod
    import g_route3_lifecycle as lifecycle
    if not Path(data_root).exists():
        return []

    def refuse(*_args, **_kwargs):
        raise PermissionError("freeze_writer_never_contacts_a_provider")
    from g_route3_contract import runtime_fixtures
    runtime = lifecycle.Runtime(
        data_root=Path(data_root), fs=fsmod.RealFs(), provider=refuse, model_receipts=refuse,
        verify_receipts=lambda receipts: {"valid": False}, freeze_binding=lambda: "", freeze_valid=lambda: False,
        guarded_files=lambda phase: {}, worker=refuse, scorer=refuse,
        schedules={phase: verify_checked_schedule(phase) for phase in ("A", "B")},
        fixtures={phase: runtime_fixtures(phase) for phase in ("A", "B")}, synthetic=False, endpoint="")
    lc = lifecycle.Lifecycle(runtime)
    lc.open()
    try:
        lc.prelude()                                  # J8: recover and complete pending boundaries first
        reasons = []
        if "tables/" + lifecycle.TABLE_NAME in lc.tree():
            reasons.append("data_root_holds_a_qualification_table")
        for phase in ("A", "B"):
            for attempt, run_id, replay, ledger_closed in lc.attempt_table(phase):
                if replay.state == "completed" or lc.committed_completed(phase, run_id):
                    reasons.append(f"data_root_holds_a_completed_attempt:{phase}{attempt}")
                elif not ledger_closed and replay.state != "closed":
                    if lc.protected(phase, run_id):
                        reasons.append(f"data_root_holds_a_protected_attempt:{phase}{attempt}")
                    reasons.append(f"data_root_holds_an_attempt_in_progress:{phase}{attempt}:{replay.state}")
        return reasons
    finally:
        lc.close()


def _data_roots_in_history(path: Path) -> list[str]:
    """Every data_root named by any version of the freeze file in main's history (B-9, read-only git)."""
    try:
        relative = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return []
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]
    log = subprocess.run(git + ["log", "--format=%H", "main", "--", relative], capture_output=True, text=True)
    if log.returncode != 0:
        raise ValueError("freeze_history_unreadable")                  # refuse rather than check nothing
    roots = []
    for commit in log.stdout.split():
        shown = subprocess.run(git + ["show", f"{commit}:{relative}"], capture_output=True, text=True)
        if shown.returncode != 0:
            # a commit that deleted or renamed the file has no version of it; any other failure refuses
            listed = subprocess.run(git + ["ls-tree", "--name-only", commit, "--", relative],
                                    capture_output=True, text=True)
            if listed.returncode != 0 or listed.stdout.strip():
                raise ValueError(f"freeze_history_unreadable:{commit}")
            continue
        try:
            root = json.loads(shown.stdout).get("data_root")
        except (ValueError, AttributeError):
            continue
        if root:
            roots.append(root)
    return roots


def write_manifest(path: Path = FREEZE_PATH, *, implementation_commit: str | None = None) -> dict[str, Any]:
    # The execution freeze must precede any qualification table. This is checked when the freeze is
    # written, not when it is verified, so a valid freeze stays valid once Phase A has produced a table.
    if (DATA / "QUALIFICATION_TABLE.json").exists():
        raise ValueError("qualification_table_must_not_exist_at_execution_freeze")
    earlier_roots = {prior.get("data_root") for prior in SUPERSEDED if prior.get("data_root")}
    earlier_roots |= set(_data_roots_in_history(path))
    if path.exists():
        existing_root = load_json(path).get("data_root")
        if existing_root:
            earlier_roots.add(existing_root)
    if earlier_roots and earlier_roots != {DATA_ROOT}:
        raise ValueError("data_root_differs_from_earlier_r7_freezes:" + ",".join(sorted(earlier_roots)))
    refusals = data_root_refusals(Path(DATA_ROOT))
    if refusals:
        raise ValueError("freeze_writer_refuses:" + ",".join(refusals))
    manifest = build_manifest(implementation_commit=implementation_commit)
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        replacing_preserved = literal_sha256(path) in {prior["literal_sha256"] for prior in SUPERSEDED}
        if load_json(path).get("candidate_id") != CANDIDATE_ID and not replacing_preserved:
            raise FileExistsError("conflicting_execution_freeze_candidate_exists")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the G-ROUTE3 execution freeze candidate.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = write_manifest() if args.write else load_json(FREEZE_PATH)
    result = verify_manifest(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
