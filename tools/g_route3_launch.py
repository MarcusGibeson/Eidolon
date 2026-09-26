from __future__ import annotations

"""The governed entry point for G-ROUTE3 under the R7 lifecycle (launcher v4).

This is the only supported way to contact a model for G-ROUTE3. Every command is an exact operator sentence
(design §7.1); none is ever self-issued. The launcher joins a kill-on-close job before anything else, pins the
recursion limit, strips proxy variables, builds the Ollama provider itself at the fixed loopback endpoint, reads
the data root from the execution freeze, and hands everything to ``g_route3_lifecycle``.

    python tools/g_route3_launch.py --sentence "Authorize G-ROUTE3 phase A execution <binding> attempt <n>"
    python tools/g_route3_launch.py --sentence "Authorize G-ROUTE3 phase B execution <binding> table <table> attempt <n>" \\
        --phase-a-attempt <n>
    python tools/g_route3_launch.py --resume --sentence "<the sentence consumed for the attempt>"
    python tools/g_route3_launch.py --sentence "Abandon G-ROUTE3 phase <P> attempt <n> after failed preflight"
    python tools/g_route3_launch.py --sentence "Declare G-ROUTE3 phase <P> attempt <n> integrity failure"
    python tools/g_route3_launch.py --sentence "Clear G-ROUTE3 phase <P> orphan run <run_id>"
    python tools/g_route3_launch.py --sentence "Freeze G-ROUTE3 qualification table from phase A attempt <n> of execution <binding>" \\
        --audit-document <path> --auditor <name> --verdict READY
    python tools/g_route3_launch.py --export-evidence <path outside the data root>

Only launch sentences authorize provider generation calls. ``--resume`` and ``--abandon`` read model receipts,
which is metadata contact, as in R6.
"""

import argparse
import json
import os
import re
import signal
import sys
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import g_route3_platform as platform  # noqa: E402

CONTRACT_VERSION = "g-route3.launcher.v4"
PROXY_VARIABLES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
HEX = r"[0-9a-f]{64}"
NUM = r"[1-9][0-9]*"
SENTENCES = {
    "launch_a": re.compile(rf"^Authorize G-ROUTE3 phase A execution (?P<binding>{HEX}) attempt (?P<n>{NUM})"
                           rf"(?: after integrity failure of attempt (?P<m>{NUM}))?$"),
    "launch_b": re.compile(rf"^Authorize G-ROUTE3 phase B execution (?P<binding>{HEX}) table (?P<table>{HEX}) "
                           rf"attempt (?P<n>{NUM})(?: after integrity failure of attempt (?P<m>{NUM}))?$"),
    "abandon": re.compile(rf"^Abandon G-ROUTE3 phase (?P<phase>[AB]) attempt (?P<n>{NUM}) after failed preflight$"),
    "declare": re.compile(rf"^Declare G-ROUTE3 phase (?P<phase>[AB]) attempt (?P<n>{NUM}) integrity failure$"),
    "clear_orphan": re.compile(r"^Clear G-ROUTE3 phase (?P<phase>[AB]) orphan run (?P<run>[A-Za-z0-9_.-]+)$"),
    "freeze_table": re.compile(rf"^Freeze G-ROUTE3 qualification table from phase A attempt (?P<n>{NUM}) "
                               rf"of execution (?P<binding>{HEX})$"),
}


def parse_sentence(sentence: str) -> tuple[str, dict[str, str]]:
    for kind, pattern in SENTENCES.items():
        match = pattern.fullmatch(sentence)
        if match:
            return kind, {key: value for key, value in match.groupdict().items() if value is not None}
    raise ValueError("sentence_not_recognized")


def local_only_network() -> None:
    """R6's _local_only_network, carried (§17)."""
    for name in PROXY_VARIABLES:
        os.environ.pop(name, None)
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"


_INTERRUPTED = {"flag": False}


def install_interrupt_flag() -> None:
    """The handler only sets a flag; the lifecycle closes through the normal path at its safe points (§7)."""
    def handler(signum, frame):  # noqa: ARG001
        _INTERRUPTED["flag"] = True
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), handler)


def checkout_git_env() -> dict[str, str]:
    env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
           "GIT_OPTIONAL_LOCKS": "0"}
    return env


def table_on_main(fs, root: Path) -> Any:
    """§10.9, read-only: the table at the tip of main has exactly these bytes, with one version in first-parent
    history."""
    import g_route3_evidence as ev
    relative = "experiments/G-ROUTE3-candidate/QUALIFICATION_TABLE.json"

    def check(table_bytes: bytes) -> bool:
        base = ["git", "-c", f"safe.directory={root.resolve().as_posix()}", "-C", str(root)]
        tip = fs.run_child(base + ["rev-parse", f"main:{relative}"], env=checkout_git_env(), timeout=120)
        if tip.returncode != 0 or tip.stdout.decode().strip() != ev.blob_id(table_bytes):
            return False
        log = fs.run_child(base + ["log", "--first-parent", "--format=%H", "main", "--", relative],
                           env=checkout_git_env(), timeout=120)
        versions = set()
        for commit in log.stdout.decode().split():
            blob = fs.run_child(base + ["rev-parse", f"{commit}:{relative}"], env=checkout_git_env(), timeout=120)
            if blob.returncode == 0:
                versions.add(blob.stdout.decode().strip())
        return versions == {ev.blob_id(table_bytes)}
    return check


def governed_runtime():
    """The only runtime this launcher builds: the governed Ollama provider, the freeze's data root."""
    import g_route3_contract as contract
    import g_route3_fs as fsmod
    import g_route3_lifecycle as lifecycle
    import g_route3_runner as runner
    from g_route1_contract import ROOT
    from g_route3_freeze import verify_manifest

    manifest = contract.load_json(contract.EXECUTION_FREEZE_PATH)
    data_root = manifest.get("data_root")
    if not data_root or not Path(data_root).is_absolute():
        raise PermissionError("execution_freeze_names_no_absolute_data_root")
    fs = fsmod.RealFs()
    provider = runner.GovernedOllamaProvider()

    def freeze_valid() -> bool:
        try:
            current = contract.load_json(contract.EXECUTION_FREEZE_PATH)
            return (verify_manifest(current)["valid"]
                    and current.get("status") == "READY_FOR_EXPLICIT_SCIENTIFIC_EXECUTION_AUTHORIZATION"
                    and current.get("data_root") == data_root)
        except Exception:  # noqa: BLE001
            return False

    return lifecycle.Runtime(
        data_root=Path(data_root), fs=fs, provider=provider, model_receipts=provider.model_receipts,
        verify_receipts=runner.verify_model_receipts,
        freeze_binding=lambda: contract.json_digest(contract.load_json(contract.EXECUTION_FREEZE_PATH)),
        freeze_valid=freeze_valid,
        guarded_files=lambda phase: lifecycle.standard_guarded_files(Path(data_root), phase),
        worker=lifecycle.spawn_worker(fs), scorer=lifecycle.spawn_scorer(fs),
        schedules={phase: contract.verify_checked_schedule(phase) for phase in ("A", "B")},
        fixtures={phase: contract.runtime_fixtures(phase) for phase in ("A", "B")},
        synthetic=False, endpoint=runner.OLLAMA_ENDPOINT, interrupted=lambda: _INTERRUPTED["flag"],
        frozen_artifact_digests=lambda: set((manifest.get("artifacts") or {}).values()),
        table_on_main=table_on_main(fs, ROOT), sleep=__import__("time").sleep)


def main(argv: list[str] | None = None) -> int:
    platform.join_kill_on_close_job()               # before any child exists (§15)
    platform.pin_recursion_limit()                  # before any pinned thread (§8)
    local_only_network()
    install_interrupt_flag()
    parser = argparse.ArgumentParser(description="Run one governed G-ROUTE3 R7 command.")
    parser.add_argument("--sentence")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--phase-a-attempt", type=int)
    parser.add_argument("--audit-document")
    parser.add_argument("--auditor")
    parser.add_argument("--verdict")
    parser.add_argument("--export-evidence")
    args = parser.parse_args(argv)
    import g_route3_lifecycle as lifecycle

    runtime = governed_runtime()
    lc = lifecycle.Lifecycle(runtime)
    if args.export_evidence:
        destination = Path(args.export_evidence).resolve()
        if Path(runtime.data_root).resolve() in destination.parents:
            parser.error("--export-evidence must be outside the data root")
        print(json.dumps(lc.command_export(destination), indent=2, sort_keys=True))
        return 0
    if not args.sentence:
        parser.error("--sentence is required")
    kind, fields = parse_sentence(args.sentence)
    if kind in ("launch_a", "launch_b") and not args.resume:
        lc.setup_if_missing()
    lc.open()
    try:
        if args.resume:
            if kind not in ("launch_a", "launch_b"):
                parser.error("--resume takes the launch sentence consumed for the attempt")
            result = lc.command_resume("A" if kind == "launch_a" else "B", args.sentence)
        elif kind in ("launch_a", "launch_b"):
            n, distinct = int(fields["n"]), "m" in fields
            if distinct and int(fields["m"]) != n - 1:
                raise ValueError("distinct_sentence_must_name_attempt_n_minus_1")
            if fields["binding"] != runtime.freeze_binding():
                raise PermissionError("sentence_binding_is_not_the_freeze_in_force")
            if kind == "launch_a":
                result = lc.command_launch("A", args.sentence, n, distinct)
            else:
                if not args.phase_a_attempt:
                    parser.error("phase B needs --phase-a-attempt")
                result = lc.command_launch_b(args.sentence, n, distinct, fields["table"], args.phase_a_attempt)
        elif kind == "abandon":
            result = lc.command_abandon(fields["phase"], int(fields["n"]))
        elif kind == "declare":
            table_run = None
            result = lc.command_declare(fields["phase"], int(fields["n"]), table_run)
        elif kind == "clear_orphan":
            result = lc.command_clear_orphan(fields["phase"], fields["run"])
        else:
            if not (args.audit_document and args.auditor and args.verdict):
                parser.error("--freeze-table sentence needs --audit-document, --auditor and --verdict")
            result = lc.command_freeze_table(int(fields["n"]), fields["binding"], Path(args.audit_document),
                                             args.auditor, args.verdict)
    finally:
        lc.close()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
