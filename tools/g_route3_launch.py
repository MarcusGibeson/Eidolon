from __future__ import annotations

"""The governed entry point for an authorized G-ROUTE3 run.

This is the only supported way to contact a model for G-ROUTE3. It builds the Ollama provider itself at
the fixed local endpoint (nothing can be injected or redirected), reads the operator's verbatim
authorization sentence, derives the authorization from it, uses one fixed run root per phase, never
overrides the guarded root, and anchors the run in git.

    python tools/g_route3_launch.py --confirmation "Authorize G-ROUTE3 phase A execution <binding> attempt 1"
    python tools/g_route3_launch.py --confirmation "Authorize G-ROUTE3 phase B execution <binding> table <table> attempt 1" \\
        --phase-a-run-id <run id of the complete Phase A attempt>
    python tools/g_route3_launch.py --confirmation "<the same sentence>" --run-id <id> --resume
    python tools/g_route3_launch.py --abandon A --reason "<why the attempt can neither finish nor resume>"
    python tools/g_route3_launch.py --clear-orphan A <run id> --reason "<why the folder has no ledger entry>"
    python tools/g_route3_launch.py --freeze-table --phase-a-run-id <id> --audit-document <path> \
        --auditor <name> --verdict READY

Resume repairs any interrupted finalization: a run that holds every call record, or is already complete, is
finished idempotently without contacting the model again. A run that was closed (incomplete, failed,
cancelled or abandoned) is never resumable; it needs the next numbered attempt.

Before Phase B the launcher requires the Phase A ledger entries, the Phase A run anchor and the frozen table
to be committed and unmodified in git. Ollama's automatic updates should be disabled until Phase B is done:
the model receipts pin the provider version, and a changed version fails the preflight closed.

Git anchor. When an authorization is consumed, the launcher commits its ledger entry; when a run
completes, it commits a small anchor file binding the run to its sealed receipt. Each is a local commit of
that one file only (`git commit -- <path>`); nothing is pushed. Deleting a ledger entry or rewriting a
finished run is then visible in git history. This is the procedural half of the declared threat model:
an honest operator, tamper-evident records.

A stale lease file (`.g-route1-single-job.lease` in the phase run root) remains only if a process was
killed. Remove it by hand only after confirming that no G-ROUTE3 process is running, and record that in
the attempt's abandon reason.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from g_route1_contract import ROOT
import g_route3_runner as runner

CONTRACT_VERSION = "g-route3.launcher.v3"
PROXY_VARIABLES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
_PHASE_A = re.compile(r"^Authorize G-ROUTE3 phase A execution (?P<freeze>[0-9a-f]{64}) attempt (?P<attempt>[1-9][0-9]*)$")
_PHASE_B = re.compile(r"^Authorize G-ROUTE3 phase B execution (?P<freeze>[0-9a-f]{64}) table (?P<table>[0-9a-f]{64}) "
                      r"attempt (?P<attempt>[1-9][0-9]*)$")
ATTRIBUTION = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"


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


def git_anchor(event: str, path: Path, *, root: Path = ROOT) -> None:
    """Commit exactly one file, locally. A failure stops the run before it can go further unanchored."""
    relative = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    git = ["git", "-c", f"safe.directory={Path(root).as_posix()}", "-C", str(root)]
    subprocess.run(git + ["add", "--", relative], check=True, capture_output=True, text=True)
    staged = subprocess.run(git + ["diff", "--cached", "--name-only", "--", relative], check=True,
                            capture_output=True, text=True).stdout.strip()
    if not staged:
        return      # already anchored with this exact content (for example on resume)
    message = f"G-ROUTE3 anchor: {event} {Path(relative).name}\n\n{ATTRIBUTION}\n"
    subprocess.run(git + ["commit", "-q", "-m", message, "--", relative], check=True, capture_output=True, text=True)


def git_is_committed(path: Path, *, root: Path = ROOT) -> bool:
    """True when the file is tracked and identical to HEAD."""
    relative = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    git = ["git", "-c", f"safe.directory={Path(root).as_posix()}", "-C", str(root)]
    tracked = subprocess.run(git + ["ls-files", "--error-unmatch", "--", relative], capture_output=True, text=True)
    unchanged = subprocess.run(git + ["diff", "--quiet", "HEAD", "--", relative], capture_output=True, text=True)
    return tracked.returncode == 0 and unchanged.returncode == 0


def _local_only_network() -> None:
    """The endpoint is loopback; make sure no proxy setting can route it anywhere else."""
    for name in PROXY_VARIABLES:
        os.environ.pop(name, None)
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"


def freeze_table(phase_a_run_id: str, audit_document: str, auditor: str, verdict: str) -> dict[str, Any]:
    """The governed table freeze: build the table from the sealed Phase A score, bind the audit document by
    digest, write it once, anchor it in git, and report the Phase B preconditions."""
    from g_route1_persistence import RouteRunStore
    import g_route3_qualification as qualification

    store = RouteRunStore(runner.RUN_ROOTS["A"], phase_a_run_id, create=False)
    score = store.score_record()
    audit = qualification.audit_record(Path(audit_document).resolve(), verdict, auditor, run_id=phase_a_run_id,
                                       score_record_sha256=score["record_sha256"])
    doc = qualification.build_table(score["cells"], run_id=phase_a_run_id, score_record_sha256=score["record_sha256"],
                                    execution_freeze_binding=runner._freeze_digest(), audit=audit,
                                    phase_a_attempts=runner.phase_a_attempts())
    table_sha = qualification.freeze_table(doc, runner.QUALIFICATION_TABLE_PATH)
    git_anchor("qualification_table_frozen", runner.QUALIFICATION_TABLE_PATH)
    return {"table_sha256": table_sha,
            "phase_b_preconditions": runner.phase_b_preconditions(runner.RUN_ROOTS["A"], phase_a_run_id)}


def launch(sentence: str, *, phase_a_run_id: str | None = None, run_id: str | None = None,
           resume: bool = False) -> dict[str, Any]:
    _local_only_network()
    authorization = authorization_from_sentence(sentence, phase_a_run_id=phase_a_run_id)
    phase = authorization["phase"]
    if resume and not run_id:
        raise ValueError("resume_requires_run_id")
    run_id = run_id or runner.utc_run_id(phase)
    provider = runner.GovernedOllamaProvider()
    receipts = provider.model_receipts()
    activity = runner.RouteThreeActivity(run_id, phase=phase, root=runner.RUN_ROOTS[phase].parent / "activity",
                                         resume=resume)
    if phase == "A":
        return runner.execute_phase_a(provider_call=provider, model_receipts=receipts, run_root=runner.RUN_ROOTS["A"],
                                      run_id=run_id, activity=activity, authorization=authorization, resume=resume,
                                      anchor=git_anchor)
    return runner.execute_phase_b(provider_call=provider, model_receipts=receipts, run_root=runner.RUN_ROOTS["B"],
                                  phase_a_root=runner.RUN_ROOTS["A"], phase_a_run_id=str(phase_a_run_id),
                                  run_id=run_id, activity=activity, authorization=authorization, resume=resume,
                                  anchor=git_anchor, committed=git_is_committed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one authorized G-ROUTE3 phase attempt.")
    parser.add_argument("--confirmation", help="the operator's verbatim authorization sentence")
    parser.add_argument("--phase-a-run-id")
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--abandon", choices=("A", "B"))
    parser.add_argument("--clear-orphan", nargs=2, metavar=("PHASE", "RUN_ID"))
    parser.add_argument("--freeze-table", action="store_true")
    parser.add_argument("--audit-document")
    parser.add_argument("--auditor")
    parser.add_argument("--verdict")
    parser.add_argument("--reason")
    args = parser.parse_args(argv)
    if args.abandon:
        result = runner.abandon_attempt(args.abandon, args.reason or "", anchor=git_anchor)
    elif args.clear_orphan:
        result = runner.clear_orphan_run(args.clear_orphan[0], args.clear_orphan[1], args.reason or "",
                                         anchor=git_anchor)
    elif args.freeze_table:
        result = freeze_table(args.phase_a_run_id, args.audit_document, args.auditor, args.verdict)
    elif args.confirmation:
        result = launch(args.confirmation, phase_a_run_id=args.phase_a_run_id, run_id=args.run_id,
                        resume=args.resume)
        result = {key: value for key, value in result.items() if key != "store"}
    else:
        parser.error("--confirmation, --abandon, --clear-orphan or --freeze-table is required")
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
