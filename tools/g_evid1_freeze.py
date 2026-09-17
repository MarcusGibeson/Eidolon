from __future__ import annotations

"""G-EVID1: freeze the preregistration, and verify the freeze before any run.

Digests are taken over newline-normalised bytes. A Windows checkout rewrites line endings, so hashing raw bytes
would report a change that does not exist and would make the freeze unverifiable on another machine.

    python tools/g_evid1_freeze.py --write     # record the freeze
    python tools/g_evid1_freeze.py             # verify every artifact still matches it
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "G-EVID1"
FREEZE = DATA / "FREEZE.json"

ARTIFACTS = (
    "experiments/G-EVID1/DESIGN_AND_PREREGISTRATION.md",
    "experiments/G-EVID1/corpus.json",
    "experiments/G-EVID1/gold.json",
    "tools/g_evid1_policy.py",
    "tools/g_evid1_scorer.py",
    "tools/g_evid1_harness.py",
    "tools/g_evid1_review_package.py",
    "tools/g_evid1_build_corpus.py",
    "tools/v2731_12_0_g_evid1_contract_tests.py",
)

REVIEWER_BASELINE = "d158e253dd88febca8f22ed050beccde2724fd9b604138fa579c5201228b21c8"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def current() -> dict[str, str]:
    return {name: digest(ROOT / name) for name in ARTIFACTS}


def write() -> dict:
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT / "conscious_agent"))
    import g_evid1_harness as harness
    import runtime_data_bootstrap as bootstrap

    bootstrap.ensure_runtime_data_env()
    import experiment_review as er

    payload = {
        "experiment_id": "G-EVID1",
        "contract_version": "g-evid1.0",
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "approved_by": "Marcus",
        "status": "frozen_not_run",
        "plan": {"items": 60, "repeats": 3, "model_calls": 180},
        "pilot": {"kind": "structural", "abort_only": True, "items": list(harness.PILOT_ITEMS)},
        "primary_gate": "unsafe_use = 0",
        "digest_note": "sha256 over newline-normalised bytes, so the freeze verifies on any checkout",
        "artifacts": current(),
        "prompt_template_sha256": hashlib.sha256(harness.PROMPT_TEMPLATE.encode("utf-8")).hexdigest(),
        "model_identity": er.model_identity(),
        "reviewer_baseline_sha256": REVIEWER_BASELINE,
        "belief_effects": "none",
    }
    FREEZE.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


def verify() -> dict:
    if not FREEZE.exists():
        return {"frozen": False, "verified": False, "reason": "no FREEZE.json"}
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    now = current()
    changed = sorted(name for name, value in frozen["artifacts"].items() if now.get(name) != value)
    missing = sorted(name for name in ARTIFACTS if name not in frozen["artifacts"])
    reviewer = digest(ROOT / "conscious_agent" / "experiment_review.py")
    return {"frozen": True, "verified": not changed and not missing and reviewer == frozen["reviewer_baseline_sha256"],
            "changed_artifacts": changed, "unfrozen_artifacts": missing,
            "reviewer_baseline_matches": reviewer == frozen["reviewer_baseline_sha256"],
            "frozen_at": frozen.get("frozen_at"), "status": frozen.get("status")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze or verify the G-EVID1 preregistration.")
    parser.add_argument("--write", action="store_true", help="record the freeze")
    args = parser.parse_args()
    if args.write:
        payload = write()
        print(json.dumps({"frozen_at": payload["frozen_at"], "artifacts": payload["artifacts"],
                          "prompt_template_sha256": payload["prompt_template_sha256"],
                          "model_identity": payload["model_identity"]}, indent=1))
        return 0
    result = verify()
    print(json.dumps(result, indent=1))
    return 0 if result.get("verified") else 1


if __name__ == "__main__":
    raise SystemExit(main())
