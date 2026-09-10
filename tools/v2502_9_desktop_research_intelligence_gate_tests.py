from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for path in (ROOT, AGENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
sys.dont_write_bytecode = True

from conscious_agent import release_authority


def main() -> int:
    checks: list[str] = []

    def require(value: object, name: str) -> None:
        checks.append(name)
        assert value, name

    require(("2502.9", "Desktop Research Intelligence Engineering Gate") in release_authority.CHECKPOINT_HISTORY, "v2502_9_historical_gate_retained")
    require(tuple(map(int, release_authority.WORKING_SOURCE_VERSION.split("."))) >= (2502, 9), "working_version_retains_or_advances_v2502_9")
    require(bool(release_authority.NEXT_BOUNDED_UNIT), "next_bounded_unit_named")
    require(not any(release_authority.AUTHORITY_FLAGS.values()), "release_authority_remains_denied")

    verifier = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    suite_name = "v2502.9-desktop-research-intelligence-gate"
    suite_path = "tools/v2502_9_desktop_research_intelligence_gate_tests.py"
    require(verifier.count(f'("{suite_name}", "{suite_path}")') == 1, "gate_registered_exactly_once")
    require(verifier.count(f'"{suite_name}"') == 2, "gate_present_once_in_registry_and_quick_profile")

    for version in range(4, 9):
        matches = list((ROOT / "tools").glob(f"v2502_{version}_*_tests.py"))
        require(len(matches) == 1, f"v2502_{version}_suite_is_unique")
        text = matches[0].read_text(encoding="utf-8")
        require("Path(__file__).resolve().parents[1]" in text and "sys.path.insert" in text, f"v2502_{version}_suite_self_locates")

    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2502-9-gate-")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "v2501_9_desktop_research_acceptance_tests.py"), "--json"],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    require(result.returncode == 0, "retained_desktop_research_acceptance_passes")
    payload = json.loads(result.stdout.strip().splitlines()[-1]) if result.stdout.strip() else {}
    require(payload.get("ok") is True and payload.get("native_network_contacted") is False, "fallback_regression_is_provider_free")
    require((ROOT / "archive/docs/legacy_dependencies/ledgers/EIDOLON_V2502_9_DESKTOP_GATE_LEDGER.md").is_file(), "desktop_gate_ledger_present")
    require(not (ROOT / "data" / "projects.json").exists(), "private_project_registry_not_packaged")

    print(json.dumps({
        "suite": suite_name,
        "ok": True,
        "passed": len(checks),
        "failed": 0,
        "checks": checks,
        "native_network_contacted": False,
        "source_modified": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
