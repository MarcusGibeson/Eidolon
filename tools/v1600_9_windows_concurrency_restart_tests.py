from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import supervised_initiative_campaign as campaign


def candidate(char: str, score: float) -> dict[str, object]:
    return {
        "candidate_id": f"discovery-{char * 20}",
        "evidence_digest": char * 64,
        "value_evidence_digest": ("f" if char != "f" else "e") * 64,
        "priority_score": score,
        "acceptance_criteria": ["focused_pass", "active_source_unchanged"],
        "dependency_candidate_ids": [],
        "practical_benefit": "visible improvement",
        "risk_class": "bounded",
    }


SHORTLIST = {
    "ok": True,
    "shortlist_digest": "d" * 64,
    "shortlist": [candidate("a", 0.91), candidate("b", 0.72), candidate("c", 0.61)],
}
SHORTLIST["selected_candidate_id"] = SHORTLIST["shortlist"][0]["candidate_id"]
SHORTLIST["selected"] = SHORTLIST["shortlist"][0]


def child(mode: str, runtime: str) -> int:
    if mode == "create":
        result = campaign.create_or_reuse_campaign(SHORTLIST, source_digest="1" * 64, runtime_root=runtime)
    elif mode == "select":
        result = campaign.select_next_campaign_candidate(current_shortlist=SHORTLIST, runtime_root=runtime)
    elif mode == "load":
        row = campaign.load_campaign(runtime)
        result = {"ok": bool(row), "campaign": campaign.public_campaign(row) if row else {}}
    else:
        raise ValueError(mode)
    print(json.dumps(result, sort_keys=True))
    return 0


def run_children(mode: str, runtime: Path, count: int) -> list[dict[str, object]]:
    child_python = os.environ.get("EIDOLON_TEST_PYTHON") or sys.executable
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    children = [
        subprocess.Popen(
            [child_python, str(Path(__file__).resolve()), "--child", mode, str(runtime)],
            cwd=str(ROOT),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": str(runtime)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        for _ in range(count)
    ]
    results: list[dict[str, object]] = []
    for process in children:
        stdout, stderr = process.communicate(timeout=120)
        if process.returncode != 0:
            raise AssertionError(f"child_failed:{process.returncode}:{stderr[-300:]}")
        results.append(json.loads(stdout.strip().splitlines()[-1]))
    return results


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1600-9-windows-race-") as temp:
        runtime = Path(temp)
        created = run_children("create", runtime, 6)
        statuses = [str(row.get("status") or "") for row in created]
        assert statuses.count("campaign_created") == 1
        assert statuses.count("campaign_reused") == 5

        identities = {str((row.get("campaign") or {}).get("campaign_id") or "") for row in created}
        assert len(identities) == 1 and next(iter(identities)).startswith("devcampaign_")

        selected = run_children("select", runtime, 4)
        assert sum(bool(row.get("ok")) for row in selected) == 1
        assert sum(str(row.get("status") or "") == "campaign_item_already_active" for row in selected) == 3

        restarted = run_children("load", runtime, 1)[0]
        public = restarted["campaign"]
        assert restarted["ok"] is True
        assert public["campaign_id"] in identities
        assert public["cycle_count"] == 1
        assert public["active_candidate_id"] == "discovery-" + "a" * 20
        assert sum(item["state"] == "active" for item in public["items"]) == 1
        assert public["provider_contacted"] is False
        assert public["source_modified"] is False
        assert public["authority_granted"] is False

        report = {
            "ok": True,
            "suite": "v1600.9-windows-concurrency-restart",
            "create_processes": 6,
            "selection_processes": 4,
            "campaign_count": 1,
            "active_item_count": 1,
            "cycle_count": 1,
            "duplicate_campaign_count": 0,
            "duplicate_activation_count": 0,
            "restart_recovered": True,
            "provider_contacted": False,
            "source_modified": False,
            "authority_expanded": False,
        }
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        raise SystemExit(child(sys.argv[2], sys.argv[3]))
    raise SystemExit(main())
