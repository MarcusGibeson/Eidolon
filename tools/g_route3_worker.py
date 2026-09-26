from __future__ import annotations

"""The G-ROUTE3 R7 sandbox worker and the shared executable derivation (design §8).

The holder derives the executable from the published ``call_recorded`` with ``derive_executable``; the scorer
re-derives it with the same function, split the same way (C-O5). The worker process runs R6's coding
classification verbatim on exactly the stored ``executable_json``, at the pinned recursion budget, and reports
the digests of the guarded modules it actually loaded (C-O3).

    python tools/g_route3_worker.py        (JSON request on stdin, JSON result on stdout)
"""

import json
import sys
from pathlib import Path
from typing import Any, Mapping

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_route3_platform as platform  # noqa: E402

CONSOLE_CONTROL_EXIT = 0xC000013A


def derive_executable(fixture: Mapping[str, Any], raw_output: str) -> str:
    """R6's chain, carried verbatim, each step through ``run_pinned``: sanitize_strings, safe_normalize,
    canonical_coding_payload. Returns the executable as ``ensure_ascii`` JSON (lossless for lone surrogates)."""
    from g_route3_runner import sanitize_strings
    from g_route3_qualification import safe_normalize
    from g_route3_semantics import canonical_coding_payload

    sanitized = platform.run_pinned(sanitize_strings, raw_output)
    canonical = platform.run_pinned(safe_normalize, sanitized, fixture["validator_profile"])
    executable, _ = platform.run_pinned(canonical_coding_payload, fixture, canonical["payload"])
    return json.dumps(executable, ensure_ascii=True)


def classify(fixture: Mapping[str, Any], executable: Any) -> dict[str, Any]:
    """R6's coding branch (g_route3_runner.py, after the provider call), verbatim, on one executable."""
    import subprocess
    from g_route1_coding_runner import run_isolated_fixture
    from g_route3_runner import (MODEL_CAUSED_CODING_ERRORS, _coding_candidate_error, _failed_coding_evidence,
                                 _host_baseline_ok)

    infrastructure_failure = ""
    candidate_error = _coding_candidate_error(fixture, executable)
    if candidate_error is not None:
        evidence = _failed_coding_evidence(fixture)
    else:
        try:
            evidence = run_isolated_fixture(fixture, executable)
        except subprocess.TimeoutExpired:
            evidence = _failed_coding_evidence(fixture)
            if not _host_baseline_ok(fixture):
                infrastructure_failure = "coding_sandbox_host_slow"
        except MODEL_CAUSED_CODING_ERRORS:
            evidence = _failed_coding_evidence(fixture)
        except Exception as exc:  # noqa: BLE001 - R6 attribution: the host, never the model
            evidence = _failed_coding_evidence(fixture)
            infrastructure_failure = f"coding_sandbox_host_failure:{type(exc).__name__}"[:200]
    return {"evidence": evidence, "candidate_error": candidate_error, "infrastructure_failure": infrastructure_failure}


def loaded_module_digests(root: Path) -> dict[str, str]:
    """sha256 of every module file under the repository root that this process has loaded."""
    from g_route1_contract import canonical_digest
    digests = {}
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if not path:
            continue
        try:
            relative = Path(path).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        digests[relative] = canonical_digest(Path(path).read_bytes())
    return digests


def main() -> int:
    platform.pin_recursion_limit()
    platform.join_kill_on_close_job()           # nested in the holder's job; grandchildren die with the worker
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    from g_route1_contract import ROOT
    from g_route3_contract import runtime_fixtures

    fixture = runtime_fixtures(request["phase"])[request["fixture_id"]]
    executable = json.loads(request["executable_json"])
    result = platform.run_pinned(classify, fixture, executable)
    result["module_digests"] = loaded_module_digests(ROOT)
    sys.stdout.buffer.write(json.dumps(result, sort_keys=True, ensure_ascii=True).encode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
