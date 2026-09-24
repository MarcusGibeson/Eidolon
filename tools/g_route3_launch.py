from __future__ import annotations

"""The governed entry point for an authorized G-ROUTE3 run.

This is the only supported way to contact a model for G-ROUTE3. It builds the Ollama provider itself
(nothing can be injected), reads the operator's verbatim authorization sentence, derives the
authorization from it, uses one fixed run root per phase, and never overrides the guarded root.

    python tools/g_route3_launch.py --confirmation "Authorize G-ROUTE3 phase A execution <binding> attempt 1"
    python tools/g_route3_launch.py --confirmation "Authorize G-ROUTE3 phase B execution <binding> table <table> attempt 1" \\
        --phase-a-run-id <run id of the complete Phase A attempt>
    python tools/g_route3_launch.py --confirmation "<the same sentence>" --run-id <id> --resume
    python tools/g_route3_launch.py --abandon A --reason "<why the attempt can neither finish nor resume>"

A stale lease file (`.g-route1-single-job.lease` in the phase run root) remains only if a process was
killed. Remove it by hand only after confirming that no G-ROUTE3 process is running, and record that in
the attempt's abandon reason.
"""

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

from g_route1_contract import ROOT
import g_route3_runner as runner

CONTRACT_VERSION = "g-route3.launcher.v1"
RUN_ROOTS = {"A": ROOT / "data" / "g_route3" / "phase_a", "B": ROOT / "data" / "g_route3" / "phase_b"}
_PHASE_A = re.compile(r"^Authorize G-ROUTE3 phase A execution (?P<freeze>[0-9a-f]{64}) attempt (?P<attempt>[1-9][0-9]*)$")
_PHASE_B = re.compile(r"^Authorize G-ROUTE3 phase B execution (?P<freeze>[0-9a-f]{64}) table (?P<table>[0-9a-f]{64}) "
                      r"attempt (?P<attempt>[1-9][0-9]*)$")


def authorization_from_sentence(sentence: str, *, phase_a_run_id: str | None = None) -> dict[str, Any]:
    """Build the authorization record from the operator's exact sentence. Nothing else is accepted."""
    for phase, pattern in (("A", _PHASE_A), ("B", _PHASE_B)):
        match = pattern.match(sentence)
        if match:
            row = {"benchmark_id": runner.BENCHMARK_ID, "phase": phase,
                   "execution_freeze_sha256": match.group("freeze"), "attempt": int(match.group("attempt")),
                   "one_execution_only": True, "consumed": False, "operator_confirmation": sentence}
            if phase == "B":
                if not phase_a_run_id:
                    raise ValueError("phase_b_requires_phase_a_run_id")
                row.update(qualification_table_sha256=match.group("table"), phase_a_run_id=phase_a_run_id)
            return row
    raise ValueError("authorization_sentence_not_recognized")


def launch(sentence: str, *, phase_a_run_id: str | None = None, run_id: str | None = None, resume: bool = False,
           endpoint: str = "http://127.0.0.1:11434") -> dict[str, Any]:
    authorization = authorization_from_sentence(sentence, phase_a_run_id=phase_a_run_id)
    phase = authorization["phase"]
    if resume and not run_id:
        raise ValueError("resume_requires_run_id")
    run_id = run_id or runner.utc_run_id(phase)
    provider = runner.GovernedOllamaProvider(endpoint)
    receipts = provider.model_receipts()
    activity = runner.RouteThreeActivity(run_id, phase=phase, root=RUN_ROOTS[phase] / "activity", resume=resume)
    if phase == "A":
        return runner.execute_phase_a(provider_call=provider, model_receipts=receipts, run_root=RUN_ROOTS["A"],
                                      run_id=run_id, activity=activity, authorization=authorization, resume=resume)
    return runner.execute_phase_b(provider_call=provider, model_receipts=receipts, run_root=RUN_ROOTS["B"],
                                  phase_a_root=RUN_ROOTS["A"], phase_a_run_id=str(phase_a_run_id), run_id=run_id,
                                  activity=activity, authorization=authorization, resume=resume)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one authorized G-ROUTE3 phase attempt.")
    parser.add_argument("--confirmation", help="the operator's verbatim authorization sentence")
    parser.add_argument("--phase-a-run-id")
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--abandon", choices=("A", "B"))
    parser.add_argument("--reason")
    args = parser.parse_args(argv)
    if args.abandon:
        result = runner.abandon_attempt(args.abandon, args.reason or "")
    elif args.confirmation:
        result = launch(args.confirmation, phase_a_run_id=args.phase_a_run_id, run_id=args.run_id,
                        resume=args.resume, endpoint=args.endpoint)
        result = {key: value for key, value in result.items() if key != "store"}
    else:
        parser.error("--confirmation or --abandon is required")
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
