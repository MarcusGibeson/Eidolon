from __future__ import annotations

"""Deterministic/adversarial checks for the installed G-CORROB1-R2 review package."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for value in (str(ROOT), str(ROOT / "tools"), str(ROOT / "conscious_agent")):
    if value not in sys.path:
        sys.path.insert(0, value)

import conversational_experiment_review as selector  # noqa: E402
import experiment_review as review  # noqa: E402
import g_corrob1_review_package as package_builder  # noqa: E402
import structured_record_rendering as record_rendering  # noqa: E402


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): sha(path) for path in sorted(root.rglob("*")) if path.is_file()}


def rendered_json(path: Path) -> object:
    return record_rendering.reconstruct(path.read_text(encoding="utf-8").split("\n\n", 1)[1])


def update_document_digest(package: Path, name: str) -> None:
    manifest_path = package / review.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["documents"]:
        if row["path"] == name:
            row["sha256"] = sha(package / name)
            break
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")


def run(runtime_root: Path) -> dict[str, object]:
    package = runtime_root / "research_packages" / package_builder.PACKAGE_ID
    run_root = runtime_root / "experiments" / package_builder.RUN_EXPERIMENT_ID / "runs"
    review_root = runtime_root / review.REVIEW_AREA
    job_root = runtime_root / selector.JOB_AREA
    protected_before = {
        "run": tree(run_root), "reviews": tree(review_root), "jobs": tree(job_root),
        "beliefs": tree(runtime_root / "beliefs"), "memory": tree(runtime_root / "memory"),
        "memories": tree(runtime_root / "memories"),
    }

    original_connect = socket.socket.connect
    try:
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network_contact_forbidden")):
            verified = package_builder.verify_review_package(package, runtime_root=runtime_root)
            chosen = selector.find_package(package_builder.SELECTOR_ALIAS, runtime_root)
            require(verified["valid"] and chosen is not None and chosen["package_id"] == package_builder.PACKAGE_ID,
                    "correct_digest_verified_package_resolution")
            require(chosen["selector_aliases"] == [package_builder.SELECTOR_ALIAS]
                    and package_builder.SELECTOR_ALIAS in selector.eligible_target_ids(runtime_root),
                    "canonical_experiment_alias_maps_to_exact_review_package")
            require(selector.find_package("G-CORROB1-R2-WRONG", runtime_root) is None,
                    "wrong_package_id_rejected")
            require(selector.find_package(str(run_root), runtime_root) is None,
                    "raw_run_directory_path_cannot_be_selected")
    finally:
        socket.socket.connect = original_connect

    loaded = review.load_package(package)
    manifest = loaded["manifest"]
    score = rendered_json(package / "score.txt")
    calls = rendered_json(package / "calls.txt")
    pairs = rendered_json(package / "pairs.txt")
    lineage = rendered_json(package / "canonical_lineage.txt")
    require(score["all_gates_passed"] is False and score["conditions"]["paired"]["diagnostic_unsafe_use"]["count"] == 3
            and all(row["item_id"] == "D01" for row in score["conditions"]["paired"]["diagnostic_unsafe_use"]["offending"]),
            "canonical_scorer_facts_and_D01_details_preserved")
    require(len(calls["records"]) == 192 and len(pairs["records"]) == 96
            and {row["record"]["role"] for row in calls["records"]} == {"A", "B"}
            and all("item_id" in row["record"] and "repeat" in row["record"] for row in calls["records"]),
            "item_repeat_A_B_and_pair_evidence_preserved")
    require(len(lineage["run_inventory"]) == 482 and lineage["counts"] == {"calls": 192, "pairs": 96, "provider_envelopes": 192},
            "complete_canonical_run_inventory_and_counts_preserved")
    require(manifest["non_authoritative"] is True and manifest["belief_effects"] == "none"
            and all(value is False for value in manifest["authority"].values()),
            "review_package_remains_fully_non_authoritative")
    package_text = "\n".join(path.read_text(encoding="utf-8", errors="replace").casefold()
                               for path in package.iterdir() if path.is_file())
    require(not any(marker in package_text for marker in package_builder.EXTERNAL_INTERPRETATION_MARKERS),
            "external_interpretation_not_present")

    with tempfile.TemporaryDirectory(prefix="g-corrob1-review-adversarial-") as temp_name:
        temp = Path(temp_name)

        digest_root = temp / "digest" / "research_packages"
        digest_package = digest_root / package_builder.PACKAGE_ID
        shutil.copytree(package, digest_package)
        (digest_package / "calls.txt").write_text(
            (digest_package / "calls.txt").read_text(encoding="utf-8") + "drift", encoding="utf-8", newline="\n")
        rows = selector.eligible_packages(temp / "digest")
        require(len(rows) == 1 and not rows[0]["eligible"] and rows[0]["reason"] == "package_document_digest_mismatch",
                "document_digest_mismatch_fails_closed")

        drift_package = temp / "drift" / "research_packages" / package_builder.PACKAGE_ID
        shutil.copytree(package, drift_package)
        run_doc = drift_package / "run.txt"
        prefix, _body = run_doc.read_text(encoding="utf-8").split("\n\n", 1)
        changed = rendered_json(run_doc)
        changed["state"] = "failed"
        run_doc.write_text(prefix + "\n\n" + record_rendering.render(changed), encoding="utf-8", newline="\n")
        update_document_digest(drift_package, "run.txt")
        try:
            package_builder.verify_review_package(drift_package, runtime_root=runtime_root)
            drift_rejected = False
        except package_builder.ReviewPackageBuildError as exc:
            drift_rejected = str(exc) == "review_representation_drift:run.txt"
        require(drift_rejected, "digest_consistent_package_drift_fails_against_canonical_run")

        raw_root = temp / "raw" / "research_packages" / package_builder.SELECTOR_ALIAS
        raw_root.mkdir(parents=True)
        source_run = next(path for path in run_root.iterdir() if path.is_dir())
        shutil.copy2(source_run / "run.json", raw_root / "run.json")
        require(selector.find_package(package_builder.SELECTOR_ALIAS, temp / "raw") is None
                and selector.eligible_packages(temp / "raw")[0]["reason"] == "package_manifest_missing",
                "raw_run_directory_substitution_rejected")

    source_text = (ROOT / "tools" / "g_corrob1_review_package.py").read_text(encoding="utf-8")
    require("OllamaExperimentAdapter" not in source_text and "execute_runner" not in source_text
            and "review_experiment(" not in source_text,
            "builder_has_no_provider_experiment_or_review_launch_path")

    protected_after = {
        "run": tree(run_root), "reviews": tree(review_root), "jobs": tree(job_root),
        "beliefs": tree(runtime_root / "beliefs"), "memory": tree(runtime_root / "memory"),
        "memories": tree(runtime_root / "memories"),
    }
    require(protected_after == protected_before, "tests_make_no_run_review_job_memory_or_belief_changes")
    return {
        "status": "passed", "checks": len(CHECKS), "check_names": CHECKS,
        "provider_calls": 0, "review_launches": 0, "experiment_launches": 0,
        "belief_effects": "none", "manifest_sha256": verified["manifest_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", default="")
    args = parser.parse_args()
    runtime = Path(args.runtime_root).resolve() if args.runtime_root else package_builder._runtime_root(None)
    print(json.dumps(run(runtime), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
