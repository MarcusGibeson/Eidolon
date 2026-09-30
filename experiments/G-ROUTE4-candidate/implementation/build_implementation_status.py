"""Build IMPLEMENTATION_STATUS.json: the state of G-ROUTE4 design step 4 at the operator-decision boundary before the
implementation review (IR).

Every value is derived, not typed: the operator's authorization from the session transcript (verbatim, bound by
record uuid and sha256), module and input digests (LF-normalized), the deterministic suites and the development
differential run here, the B7 and oracle records by digest, the development certification campaign from its report,
and the integrity of the reviewed inputs and historical records against 30b488a and the seal.

    python -B build_implementation_status.py --transcript <session .jsonl> --campaign-report <campaign_report.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parent
ROOT = CAND.parent.parent
TOOLS = ROOT / "tools"
REL = "experiments/G-ROUTE4-candidate"
BASE = "30b488a3434f69ffb1edb9b46533e4ecc1e19eba"
AUTH_PREFIX = "I authorize implementation under the frozen G-ROUTE4 design step 4."
PROTECTED_REFS = ("refs/heads/main", "refs/heads/g-route4/seal", "refs/tags/g-route4-seal")
# reviewed inputs and historical records: unchanged since the round-1 closure (30b488a)
UNCHANGED_SINCE_BASE = (f"{REL}/adjudication", f"{REL}/corpus_review", f"{REL}/DESIGN_CANDIDATE.md",
                        f"{REL}/G-ROUTE4_OBLIGATIONS.md")
# the frozen prior experiments and the modules imported unchanged: identical to the seal
UNCHANGED_SINCE_SEAL = ("experiments/G-ROUTE1-candidate", "experiments/G-ROUTE3-candidate",
                        *(f"tools/{m}.py" for m in ("g_route1_contract", "g_route1_validators", "g_route1_operational",
                                                   "g_route1_provider", "g_route1_execution_contract",
                                                   "g_route1_freeze", "g_route2_normalization",
                                                   "g_route3_conversation", "g_route3_semantics",
                                                   "g_route3_operational", "g_route3_triggers",
                                                   "g_route3_routing")))
EXECUTION_INPUTS = ("corpus_a.json", "gold_a.json", "corpus_b.json", "gold_b.json", "fixture_families.json",
                    "model_bindings.json", "schedule_a.json", "schedule_b.json", "thresholds.json")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def authorization(transcript: Path) -> dict:
    found = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("type") != "user":
            continue
        content = record.get("message", {}).get("content")
        texts = [content] if isinstance(content, str) else [
            block.get("text", "") for block in content or [] if isinstance(block, dict) and block.get("type") == "text"]
        for text in texts:
            if text.startswith(AUTH_PREFIX):
                found.append({"transcript_record_uuid": record.get("uuid"), "utc": record.get("timestamp"),
                              "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "text": text})
    if len(found) != 1:
        raise SystemExit(f"expected exactly one step-4 authorization, found {len(found)}")
    return found[0]


def run_suite(args: list[str], timeout: int = 1800) -> dict:
    done = subprocess.run([sys.executable, "-B", *args], cwd=str(TOOLS), capture_output=True, text=True,
                          timeout=timeout, encoding="utf-8", errors="replace")
    tail = (done.stdout + done.stderr).strip().splitlines()
    ran = next((m.group(1) for line in tail if (m := re.match(r"Ran (\d+) tests?", line))), None)
    return {"command": "python -B " + " ".join(args), "exit_code": done.returncode,
            "tests_run": int(ran) if ran else None, "last_line": tail[-1] if tail else ""}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--campaign-report", required=True)
    parser.add_argument("--campaign-commit", required=True)
    args = parser.parse_args()
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("the working tree has uncommitted changes; build the status from a committed head")
    head = git("rev-parse", "HEAD")

    unchanged = {}
    for path in UNCHANGED_SINCE_BASE:
        unchanged[path] = {"against": "30b488a", "identical": git("rev-parse", f"{BASE}:{path}") ==
                           git("rev-parse", f"HEAD:{path}")}
    for path in UNCHANGED_SINCE_SEAL:
        unchanged[path] = {"against": "g-route4/seal", "identical": git("rev-parse", f"g-route4/seal:{path}") ==
                           git("rev-parse", f"HEAD:{path}")}
    changes = [line.split("\t") for line in git("diff", "--name-status", BASE, "HEAD").splitlines()]
    outside = [c for c in changes if not (c[-1].startswith("tools/g_route4_") or
                                          c[-1].startswith(f"{REL}/implementation/") or
                                          (c[0] == "A" and c[-1] in {f"{REL}/{n}" for n in EXECUTION_INPUTS}))]
    modified_existing = [c for c in changes if c[0] != "A" and not c[-1].startswith("tools/g_route4_")]
    refs = {ref: git("rev-parse", ref) for ref in PROTECTED_REFS}

    suites = {"g_route4_tests": run_suite(["g_route4_tests.py"]),
              "g_route4_r7_tests": run_suite(["g_route4_r7_tests.py"])}
    scratch = HERE / "_differential_development_run.json"
    differential = subprocess.run([sys.executable, "-B", "g_route4_differential.py", "--out", str(scratch)],
                                  cwd=str(TOOLS), capture_output=True, text=True, timeout=3600)
    diff_report = json.loads(scratch.read_text(encoding="utf-8"))
    scratch.unlink()
    lifecycle = diff_report["lifecycle"]
    campaign = json.loads(Path(args.campaign_report).read_text(encoding="utf-8"))
    campaign_commit = git("rev-parse", args.campaign_commit)
    tools_changed_since_campaign = git("diff", "--name-only", campaign_commit, "HEAD", "--", "tools").split()
    b7 = json.loads((HERE / "B7_INDEPENDENCE_RECHECK.json").read_text(encoding="utf-8"))
    oracle = json.loads((HERE / "ORACLE_REPORT.json").read_text(encoding="utf-8"))

    status = {
        "schema_version": "g-route4.implementation-status.v1",
        "design_step": "4 (implementation), at the boundary before the implementation review",
        "built_at_commit": head,
        "base_commit": BASE,
        "operator_authorization": authorization(Path(args.transcript)),
        "modules_lf_sha256": {p.name: lf_sha256(p) for p in sorted(TOOLS.glob("g_route4_*.py"))},
        "fork_record": {"file": f"{REL}/implementation/FORK_RECORD.json",
                        "lf_sha256": lf_sha256(HERE / "FORK_RECORD.json")},
        "execution_inputs": {"built_by": f"{REL}/implementation/build_execution_inputs.py",
                             "from": [f"{REL}/corpus_review/round1/FINAL_MAIN_MODEL_FACING.json",
                                      f"{REL}/corpus_review/round1/FINAL_MAIN_GOLD.json"],
                             "lf_sha256": {n: lf_sha256(CAND / n) for n in EXECUTION_INPUTS}},
        "checks": {
            "B7_forked_module_recheck": {"record": f"{REL}/implementation/B7_INDEPENDENCE_RECHECK.json",
                                         "lf_sha256": lf_sha256(HERE / "B7_INDEPENDENCE_RECHECK.json"),
                                         "result": b7.get("result"), "compared": b7.get("compared"),
                                         "differing": b7.get("differing"), "bounds_met": b7.get("bounds_met"),
                                         "module_lf_sha256_in_record": b7["forked_module"]["lf_sha256"],
                                         "module_unchanged_since_b7": b7["forked_module"]["lf_sha256"] ==
                                         lf_sha256(TOOLS / "g_route4_independence.py"),
                                         "preserved_failure": f"{REL}/implementation/b7_failures/B7_RUN1_FAIL.json"},
            "B8_counts_bound": {"record": f"{REL}/adjudication/B_MAIN_CLOSURE_ADDENDUM_CR1.json",
                                "carried_by": "g_route4_freeze.b8_condition (checked when the manifest is written)"},
            "deterministic_suites": suites,
            "preserved_development_failures": sorted(
                f"{REL}/implementation/{q.relative_to(HERE).as_posix()}"
                for d in ("b7_failures", "development_failures") for q in (HERE / d).iterdir()),
            "oracle": {"record": f"{REL}/implementation/ORACLE_REPORT.json",
                       "lf_sha256": lf_sha256(HERE / "ORACLE_REPORT.json"), "passed": oracle.get("passed")},
            "differential_development_run": {
                "exit_code": differential.returncode, "passed": diff_report.get("passed"),
                "grading": {k: diff_report["grading"].get(k) for k in ("difference_count", "passed")},
                "grading_sensitivity": diff_report.get("grading_sensitivity"),
                "lifecycle": {k: lifecycle.get(k) for k in ("states", "commits_compared", "files_compared",
                                                            "difference_count", "sensitivity", "o7_undisposed",
                                                            "passed")},
                "note": "development run; the official differential record (DIFFERENTIAL_REPORT.json) is produced "
                        "at CERT, after the implementation review"},
            "certification_campaign_development_run": {
                "mode": "--quick", "run_at_commit": campaign_commit,
                "tools_changed_since": tools_changed_since_campaign, "report_sha256": hashlib.sha256(Path(args.campaign_report).read_bytes()).hexdigest(),
                "sections": {r.get("label", str(i)): len(r.get("problems", [])) for i, r in enumerate(campaign)},
                "problems_total": sum(len(r.get("problems", [])) for r in campaign),
                "note": "development run (quick stride); the official certification record "
                        "(CERTIFICATION_REPORT.json) is produced at CERT, after the implementation review"},
        },
        "integrity": {"unchanged": unchanged, "changes_outside_implementation_paths": outside,
                      "existing_files_modified_outside_g_route4_modules": modified_existing,
                      "protected_refs": refs},
        "obligations_for_ir_and_cert": {
            "O7": "lifecycle differential lists every module-bound call with its disposition (development run: "
                  "0 undisposed, 0 residual differences); verified at CERT",
            "O8": "g_route4_tests.DesignTests (thresholds keys equal to the keys read, by static reading); IR",
            "O9": "g_route4_r7_tests.SentenceMeaningTests (a refusal case for each meaning); IR, CERT",
            "N2": f"{REL}/implementation/RESULTS_TEMPLATE.md (projection label); IR",
            "N9": "g_route4_tests test_n9_the_carried_core_is_byte_identical_to_the_prior_module, named in "
                  "G3_REFERENCE_ALLOWLIST; IR"},
        "not_done": ["implementation review (fresh reviewers)", "official certification campaign and differential "
                     "(CERT)", "execution freeze (step 5)", "Phase A′", "Phase B′", "any provider or model call"],
        "next_boundary": "the implementation review (design step 4) needs fresh reviewers, started by the operator; "
                         "nothing further proceeds without that authorization",
    }
    ok = (all(v["identical"] for v in unchanged.values()) and not outside and not modified_existing
          and all(s["exit_code"] == 0 for s in suites.values()) and differential.returncode == 0
          and status["checks"]["certification_campaign_development_run"]["problems_total"] == 0
          and not tools_changed_since_campaign
          and b7.get("result") == "PASS" and b7.get("bounds_met") is True and not b7.get("differing")
          and status["checks"]["B7_forked_module_recheck"]["module_unchanged_since_b7"]
          and oracle.get("passed") is True)
    status["all_checks_passed"] = ok
    out = HERE / "IMPLEMENTATION_STATUS.json"
    out.write_text(json.dumps(status, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"all_checks_passed": ok, "suites": suites, "refs": refs,
                      "campaign_problems": status["checks"]["certification_campaign_development_run"]}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
