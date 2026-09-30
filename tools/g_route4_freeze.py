# forked from g_route3_freeze
from __future__ import annotations

"""Build and verify the non-authorizing G-ROUTE4 execution-freeze candidate (design order of work, step 5).

The freeze binds every G-ROUTE4 input and module by digest and records what the design requires: the Ollama
version, the versions of `requests` and its loaded dependencies, the model identities and generation configuration,
the carried contract ids (read by module attribute), the thresholds, schedules and corpora, and the pinned data root.

Freeze conditions carried from the external corpus review (corpus_review/round1/CORPUS_REVIEW_R1_CLOSURE.json):
- B7: writing the freeze re-runs the forked-module independence re-check against the reviewed corpus, and refuses
  unless it reproduces the frozen values and satisfies the same bounds; the pinned-tool result cannot waive it.
- B8: the B′ fix-round per-cell counts are bound in the manifest.

It also requires the step-4 records (implementation review, certification report, differential report), so a freeze
cannot be written before those stages. Nothing here authorizes contact: every authority flag is false.
"""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

import g_route3_conversation
import g_route3_operational
import g_route3_routing
import g_route3_semantics
import g_route3_triggers
from g_route1_contract import ROOT, digest_file
from g_route4_contract import (DATA, EXPECTED_CALLS, EXECUTION_FREEZE_PATH, json_digest, load_corpus, load_gold,
                               load_json, load_model_bindings, load_thresholds, verify_checked_schedule)

CONTRACT_VERSION = "g-route4.execution-freeze-candidate.v1"
CANDIDATE_ID = "G-ROUTE4-EXECUTION-R1"
DATA_ROOT = r"C:\Users\marcu\AppData\Local\Eidolon\research\g_route4"   # pinned literally
SUPERSEDED: tuple[Mapping[str, Any], ...] = ()                            # design: the superseded list is empty
FREEZE_PATH = EXECUTION_FREEZE_PATH
CAND = "experiments/G-ROUTE4-candidate"
B7_SCRIPT = ROOT / CAND / "implementation" / "b7_independence_recheck.py"
B7_RECORD = f"{CAND}/implementation/B7_INDEPENDENCE_RECHECK.json"
B8_SOURCE = f"{CAND}/adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json"
REQUESTS_DISTRIBUTIONS = ("requests", "urllib3", "idna", "charset-normalizer", "certifi")
ARTIFACTS = tuple(f"{CAND}/{name}" for name in (
    # design, obligations and their reviews
    "DESIGN_CANDIDATE.md", "G-ROUTE4_OBLIGATIONS.md", "RESEARCH_DIAGNOSIS.md", "RESEARCH_DIAGNOSIS.json",
    "DESIGN_REVIEW_ROUND1.md", "DESIGN_REVIEW_ROUND2.md", "DESIGN_REVIEW_ROUND3.md", "DESIGN_REVIEW_ROUND4.md",
    "DESIGN_REVIEW_ROUND5.md", "DESIGN_REVIEW_ROUND6.md",
    # blueprint, seal and audit sample
    "blueprint/BLUEPRINT.json", "blueprint/BLUEPRINT_CANDIDATE.md", "blueprint/BLUEPRINT_FREEZE.json",
    "blueprint/FEASIBILITY_REPORT.json", "blueprint/audit_sample.py", "blueprint/build_blueprint.py",
    "sealed/SEAL_MANIFEST.json", "sealed/SEAL_NOTES.md", "sealed/O3_IDENTIFIER_DECISION.md",
    "sealed/adjudicator_config.json", "sealed/corpus_a.json", "sealed/corpus_b.json", "sealed/gold_a.json",
    "sealed/gold_b.json", "sealed/reserve_corpus_a.json", "sealed/reserve_corpus_b.json", "sealed/reserve_gold_a.json",
    "sealed/reserve_gold_b.json", "sealed/authoring_ledger.json", "audit_sample/AUDIT_SAMPLE.json",
    # adjudication, fixes, errata and the corpus review (step-13 records)
    "adjudication/O2_AMENDMENT_2026-09-29.md", "adjudication/adjudicator_config_amended.json",
    "adjudication/A_MAIN_CLOSURE.json", "adjudication/B_MAIN_CLOSURE.json",
    "adjudication/A_MAIN_CLOSURE_ADDENDUM_CR1.json", "adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json",
    "adjudication/errata/B_MAIN_CLOSURE_ERRATUM_1.json", "adjudication/errata/B_MAIN_CLOSURE_ERRATUM_2.json",
    "adjudication/errata/STEP7_RULING_ANNOTATION.md",
    "adjudication/fixes/round1_bmain/FIX_RECORD.json", "adjudication/fixes/round1_amain/FIX_RECORD.json",
    "adjudication/fixes/cr1_amain/FIX_RECORD.json", "adjudication/fixes/cr1_bmain/FIX_RECORD.json",
    "adjudication/fixes/LATENT_DEFECTS.md", "adjudication/fixes/round1_amain/LATENT_DEFECTS_ADDENDUM.md",
    "corpus_review/round1/CORPUS_REVIEW_R1_CLOSURE.json", "corpus_review/round1/RECONCILIATION_R1_FINAL.md",
    "INDEPENDENCE_REPORT.json", "INDEPENDENCE_REPORT_CR1.json", "CONTAMINATION_ANALYSIS.md",
    "CONTAMINATION_ANALYSIS_CR1.md",
    # execution inputs
    "corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json", "fixture_families.json", "model_bindings.json",
    "thresholds.json", "schedule_a.json", "schedule_b.json",
    # implementation stage records
    "implementation/FORK_RECORD.json", "implementation/B7_INDEPENDENCE_RECHECK.json",
)) + (
    "experiments/G-ROUTE1-candidate/prompt_profiles.json", "experiments/G-ROUTE1-candidate/model_bindings.json",
    "tools/g_route1_contract.py", "tools/g_route1_validators.py", "tools/g_route1_operational.py",
    "tools/g_route1_provider.py", "tools/g_route1_execution_contract.py", "tools/g_route1_freeze.py",
    "tools/g_route2_normalization.py", "tools/g_route3_conversation.py", "tools/g_route3_semantics.py",
    "tools/g_route3_operational.py", "tools/g_route3_triggers.py", "tools/g_route3_routing.py",
    "tools/g_route4_contract.py", "tools/g_route4_qualification.py", "tools/g_route4_validation.py",
    "tools/g_route4_runner.py", "tools/g_route4_independence.py", "tools/g_route4_freeze.py",
    "tools/g_route4_platform.py", "tools/g_route4_fs.py", "tools/g_route4_journal.py", "tools/g_route4_evidence.py",
    "tools/g_route4_lifecycle.py", "tools/g_route4_scorer.py", "tools/g_route4_launch.py",
    "tools/g_route4_campaign.py", "tools/g_route4_tests.py", "tools/g_route4_r7_tests.py",
    "tools/g_route4_differential.py", "tools/g_route4_oracle.py",
    f"{CAND}/implementation/RESULTS_TEMPLATE.md",
)
# Records of the later step-4 stages; the freeze cannot be written without them (design order of work 4 -> 5).
STEP4_RECORDS = (f"{CAND}/implementation/IMPLEMENTATION_REVIEW.json", f"{CAND}/implementation/CERTIFICATION_REPORT.json",
                 f"{CAND}/implementation/DIFFERENTIAL_REPORT.json")


def measure_recursion_thresholds() -> dict[str, int]:
    """The JSON nesting band at the pinned budget, in a fresh pinned thread. The AST recursion band is not measured:
    coding is excluded (design "Coding exclusion in the R7 fork")."""
    import json as _json
    import g_route4_platform as platform

    platform.pin_recursion_limit()

    def json_ok(depth: int) -> bool:
        try:
            _json.loads("[" * depth + "]" * depth)
            return True
        except RecursionError:
            return False

    low, high = 100, 5000
    while low < high:
        middle = (low + high + 1) // 2
        if platform.run_pinned(json_ok, middle):
            low = middle
        else:
            high = middle - 1
    return {"json_nesting_max": low, "recursion_limit": platform.RECURSION_LIMIT,
            "stack_bytes": platform.PINNED_STACK_BYTES}


def literal_sha256(path: Path) -> str:
    """sha256 of the file's bytes with CRLF and CR normalized to LF, so a git checkout's line endings do not matter."""
    import hashlib
    data = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def current_commit(root: Path = ROOT) -> str:
    return subprocess.run(["git", "-c", f"safe.directory={Path(root).as_posix()}", "rev-parse", "HEAD"],
                          cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def requests_versions() -> dict[str, str | None]:
    """The versions of `requests` and its loaded dependencies (design "Closure rule")."""
    from importlib import metadata
    out = {}
    for name in REQUESTS_DISTRIBUTIONS:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def b7_condition(root: Path = ROOT) -> dict[str, Any]:
    """B7 as recorded: the forked-module re-check passed, against the forked module that is bound now."""
    record = load_json(root / B7_RECORD)
    module_digest = literal_sha256(root / "tools/g_route4_independence.py")
    if record.get("result") != "PASS" or record.get("blocks_freeze") is not False or record.get("differing"):
        raise ValueError("freeze_condition_B7_not_met")
    if record.get("forked_module", {}).get("lf_sha256") != module_digest:
        raise ValueError("freeze_condition_B7_recorded_for_a_different_module")
    return {"record": B7_RECORD, "record_sha256": digest_file(root / B7_RECORD), "result": record["result"],
            "values_compared": record["compared"], "forked_module_sha256": module_digest,
            "condition_verbatim": record["condition_verbatim"]}


def b8_condition(root: Path = ROOT) -> dict[str, Any]:
    """B8: the B′ fix-round per-cell counts, bound in the freeze records."""
    addendum = load_json(root / B8_SOURCE)
    counts = addendum["per_cell_fix_rounds_B8"]
    return {"source": B8_SOURCE, "source_sha256": digest_file(root / B8_SOURCE),
            "per_cell_fix_round_counts": {k: v for k, v in counts.items() if k != "note"}}


def build_manifest(*, implementation_commit: str | None = None, root: Path = ROOT) -> dict[str, Any]:
    missing = [path for path in ARTIFACTS + STEP4_RECORDS if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError("execution_freeze_artifacts_missing:" + ",".join(missing))
    for corpus in ("A", "B"):
        load_corpus(corpus)
        load_gold(corpus)
    schedules = {corpus: verify_checked_schedule(corpus) for corpus in ("A", "B")}
    models = load_model_bindings()
    thresholds = load_thresholds()
    seed = {
        "contract_version": CONTRACT_VERSION,
        "candidate_id": CANDIDATE_ID,
        "status": "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION",
        "implementation_commit": implementation_commit or current_commit(root),
        "supersedes": [],
        "research_questions": {
            "P1": ("On the frozen validation corpus, given the A′ table actually produced: is the true unsafe-stop rate "
                   "at most 0.10, and is the true correct-stop rate of qualified-start cases at least 0.60, each at "
                   "one-sided 95% confidence with exact binomial bounds?"),
            "P2": "conversation on the cheapest tier (descriptive)",
            "E1": "escalation (pilot, descriptive)",
            "R1": "grounded research: can a tier qualify on fresh, adjudicated fixtures (descriptive metrics)",
        },
        "phases": {
            "A": {"corpus": "G-ROUTE4-CORPUS-A", "role": "qualification", "planned_calls": EXPECTED_CALLS["A"],
                  "schedule_sha256": json_digest(schedules["A"]),
                  "authorization_format": "Authorize G-ROUTE4 phase A execution <binding> attempt <n>",
                  "attempts": "numbered from 1; each attempt is a separate explicit authorization"},
            "B": {"corpus": "G-ROUTE4-CORPUS-B", "role": "validation", "planned_calls": EXPECTED_CALLS["B"],
                  "schedule_sha256": json_digest(schedules["B"]),
                  "authorization_format": "Authorize G-ROUTE4 phase B execution <binding> table <table> attempt <n>",
                  "requires_frozen_audited_qualification_table": True},
            "table_freeze_sentence": "Freeze G-ROUTE4 qualification table from phase A attempt <n> of execution <binding>",
        },
        "corpus_digests": {name: digest_file(root / f"{CAND}/{name}")
                           for name in ("corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json")},
        "both_corpora_frozen_before_any_contact": True,
        "qualification_table_exists": False,
        "model_bindings_sha256": json_digest(models),
        "thresholds_sha256": json_digest(thresholds),
        "model_identities": [{"tier": r["tier"], "model": r["model"], "manifest_digest": r["manifest_digest"],
                              "model_blob_sha256": r["model_blob_sha256"]} for r in models["bindings"]],
        "ollama_version": models["provider_version"],
        "generation_configuration": models["generation_configuration"],
        "requests_and_dependencies": requests_versions(),
        "carried_contracts": {"conversation": g_route3_conversation.CONTRACT_VERSION,
                              "semantics": g_route3_semantics.CONTRACT_VERSION,
                              "operational_validator": g_route3_operational.CONTRACT_VERSION,
                              "triggers": g_route3_triggers.CONTRACT_VERSION,
                              "routing": g_route3_routing.CONTRACT_VERSION,
                              "normalization": "g-route2.transport-normalization.v1",
                              "validators": "g-route1.validators.v1"},
        "runner_contract": "g-route4.runner.v1",
        "lifecycle_contract": "g-route4.lifecycle.r7",
        "data_root": DATA_ROOT,
        "recursion_thresholds": measure_recursion_thresholds(),
        "coding": "excluded (D6): no coding fixture, no worker, execution kinds are integrity failures",
        "freeze_conditions": {"B7": b7_condition(root), "B8": b8_condition(root)},
        "step4_records": {path: digest_file(root / path) for path in STEP4_RECORDS},
        "threat_model": ("accidents in code, tampering at boundaries. The code guarantees at-most-once and a truthful "
                         "history against accidents and misuse of supported commands; every attempt's journal is "
                         "committed to the private evidence repository at its boundaries and verified by every command; "
                         "tampering with an attempt in progress is a declared residual"),
        "launcher": {"contract": "g-route4.launcher.v4", "path": "tools/g_route4_launch.py",
                     "provider_endpoint": "http://127.0.0.1:11434 (fixed)",
                     "authorized_runs_only_through_launcher": True, "data_root": DATA_ROOT},
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
            "benchmark_launches": manifest.get("benchmark_launches")}


def data_root_refusals(data_root: Path) -> list[str]:
    """R7 §9.3: the freeze writer refuses once D holds a table, or a completed, protected or in-progress attempt.
    It follows J8 (lease, verification, replay) and refuses on unreadable files."""
    import g_route4_fs as fsmod
    import g_route4_lifecycle as lifecycle
    if not Path(data_root).exists():
        return []

    def refuse(*_args, **_kwargs):
        raise PermissionError("freeze_writer_never_contacts_a_provider")
    from g_route4_contract import runtime_fixtures
    runtime = lifecycle.Runtime(
        data_root=Path(data_root), fs=fsmod.RealFs(), provider=refuse, model_receipts=refuse,
        verify_receipts=lambda receipts: {"valid": False}, freeze_binding=lambda: "", freeze_valid=lambda: False,
        guarded_files=lambda phase: {}, scorer=refuse,
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
    """Every data_root named by any version of the freeze file in main's history (read-only git)."""
    try:
        relative = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return []
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT)]
    log = subprocess.run(git + ["log", "--format=%H", "main", "--", relative], capture_output=True, text=True,
                         timeout=120)
    if log.returncode != 0:
        raise ValueError("freeze_history_unreadable")                  # refuse rather than check nothing
    roots = []
    for commit in log.stdout.split():
        shown = subprocess.run(git + ["show", f"{commit}:{relative}"], capture_output=True, text=True, timeout=120)
        if shown.returncode != 0:
            listed = subprocess.run(git + ["ls-tree", "--name-only", commit, "--", relative],
                                    capture_output=True, text=True, timeout=120)
            if listed.returncode != 0 or listed.stdout.strip():
                raise ValueError(f"freeze_history_unreadable:{commit}")
            continue
        try:
            root = json.loads(shown.stdout).get("data_root")
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"freeze_history_version_unparseable:{commit}") from exc
        if root:
            roots.append(root)
    return roots


def rerun_b7() -> None:
    """B7 at the freeze: re-run the forked-module re-check now; refuse unless it passes."""
    spec = importlib.util.spec_from_file_location("g4_b7_recheck", B7_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.main() != 0:
        raise ValueError("freeze_condition_B7_failed_at_freeze")


def write_manifest(path: Path = FREEZE_PATH, *, implementation_commit: str | None = None) -> dict[str, Any]:
    # The execution freeze must precede any qualification table. This is checked when the freeze is
    # written, not when it is verified, so a valid freeze stays valid once Phase A has produced a table.
    if (DATA / "QUALIFICATION_TABLE.json").exists():
        raise ValueError("qualification_table_must_not_exist_at_execution_freeze")
    earlier_roots = set(_data_roots_in_history(path))
    if path.exists():
        existing_root = load_json(path).get("data_root")
        if existing_root:
            earlier_roots.add(existing_root)
    if earlier_roots and earlier_roots != {DATA_ROOT}:
        raise ValueError("data_root_differs_from_earlier_freezes:" + ",".join(sorted(earlier_roots)))
    refusals = data_root_refusals(Path(DATA_ROOT))
    if refusals:
        raise ValueError("freeze_writer_refuses:" + ",".join(refusals))
    rerun_b7()
    manifest = build_manifest(implementation_commit=implementation_commit)
    rendered = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") != rendered:
        if load_json(path).get("candidate_id") != CANDIDATE_ID:
            raise FileExistsError("conflicting_execution_freeze_candidate_exists")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the G-ROUTE4 execution freeze candidate.")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = write_manifest() if args.write else load_json(FREEZE_PATH)
    result = verify_manifest(manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
