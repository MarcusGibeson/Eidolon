from __future__ import annotations

"""Exact-bound conversational invocation of one externally authorized experiment.

This module is deliberately not a generic experiment launcher. It recognizes one
fixed manifest identifier, discovers one separately created operator authorization,
consumes that authorization before provider contact, and delegates to the frozen
G-CORROB1 runner. It cannot create or revise any experiment artifact or authority.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

MANIFEST_ID = "G-CORROB1-R2"
CONTRACT_VERSION = "authorized-frozen-experiment-execution.v1"
AUTHORIZATION_SCOPE = "one_frozen_g_corrob1_r2_execution"
EXPECTED_CALLS = 192
EXPECTED_PAIRS = 96
_COMMAND = re.compile(
    r"^(?:please\s+)?(?:execute|run)\s+(?:the\s+)?authorized\s+frozen\s+experiment\s+"
    r"(?P<manifest>G-CORROB1-R2)\s*[.!]*$",
    re.IGNORECASE,
)


class ExperimentExecutionCancelled(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _default_runtime_root() -> Path:
    from runtime_data_bootstrap import default_runtime_data_dir

    return Path(default_runtime_data_dir())


def _safe_identifier(value: str, *, prefix: str = "") -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value)) and (not prefix or value.startswith(prefix))


def parse_authorized_experiment_command(text: str) -> str:
    match = _COMMAND.fullmatch(" ".join(str(text or "").split()))
    return MANIFEST_ID if match else ""


def _authorization_directory(runtime_root: Path) -> Path:
    return runtime_root / "experiment_execution_authorizations" / MANIFEST_ID


def _load_single_authorization(runtime_root: Path) -> tuple[Path, dict[str, Any], str]:
    directory = _authorization_directory(runtime_root)
    paths = sorted(path for path in directory.glob("*.json") if path.is_file()) if directory.is_dir() else []
    available: list[tuple[Path, dict[str, Any], str]] = []
    malformed = False
    for path in paths:
        try:
            raw = path.read_bytes()
            value = json.loads(raw)
        except (OSError, ValueError, TypeError):
            malformed = True
            continue
        if not isinstance(value, dict):
            malformed = True
            continue
        authorization_id = str(value.get("authorization_id") or "")
        consumed = (
            runtime_root / "experiment_execution_consumptions" / f"{authorization_id}.json"
            if _safe_identifier(authorization_id, prefix="gcorrob1exec_auth_") else None
        )
        if consumed is not None and consumed.is_file():
            continue
        available.append((path, value, hashlib.sha256(raw).hexdigest()))
    if malformed:
        raise PermissionError("authorization_unreadable")
    if len(available) != 1:
        reason = "authorization_missing_or_consumed" if not available else "multiple_authorizations_present"
        raise PermissionError(reason)
    return available[0]


def verify_execution_authorization(
    authorization: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    from g_corrob1_execution_capability_freeze import (
        execution_manifest_sha256,
        verify_authorized_execution_manifest,
    )

    row = dict(authorization or {})
    reasons: list[str] = []
    allowed = {
        "contract_version", "authorization_id", "manifest_id", "execution_manifest",
        "execution_manifest_sha256", "authorization_scope", "one_run_only",
        "execution_frozen", "execution_authorized", "full_experiment_authorized", "provider_contact_authorized",
        "expected_generation_calls", "expected_pairs", "operator_confirmation",
        "issued_at", "expires_at", "belief_effects",
    }
    if set(row) != allowed:
        reasons.append("authorization_fields_mismatch")
    authorization_id = str(row.get("authorization_id") or "")
    if not _safe_identifier(authorization_id, prefix="gcorrob1exec_auth_"):
        reasons.append("authorization_id_invalid")
    if row.get("contract_version") != "g-corrob1.r2.operator-execution-authorization.1":
        reasons.append("authorization_contract_mismatch")
    if row.get("manifest_id") != MANIFEST_ID:
        reasons.append("manifest_id_mismatch")
    if row.get("authorization_scope") != AUTHORIZATION_SCOPE:
        reasons.append("authorization_scope_mismatch")
    if row.get("one_run_only") is not True:
        reasons.append("one_run_only_required")
    if row.get("execution_frozen") is not True:
        reasons.append("execution_freeze_missing")
    if row.get("execution_authorized") is not True or row.get("full_experiment_authorized") is not True:
        reasons.append("full_experiment_authorization_missing")
    if row.get("provider_contact_authorized") is not True:
        reasons.append("provider_contact_authorization_missing")
    if row.get("expected_generation_calls") != EXPECTED_CALLS or row.get("expected_pairs") != EXPECTED_PAIRS:
        reasons.append("authorized_denominators_mismatch")
    if row.get("belief_effects") != "none":
        reasons.append("belief_effects_mismatch")

    manifest = row.get("execution_manifest")
    manifest_check = verify_authorized_execution_manifest(manifest if isinstance(manifest, Mapping) else {})
    if not manifest_check["valid"]:
        reasons.extend("manifest:" + reason for reason in manifest_check["reasons"])
    expected = str(row.get("execution_manifest_sha256") or "")
    calculated = execution_manifest_sha256(manifest if isinstance(manifest, Mapping) else {})
    if expected != calculated or len(expected) != 64:
        reasons.append("execution_manifest_digest_mismatch")
    if row.get("operator_confirmation") != f"Authorize {MANIFEST_ID} frozen execution {expected}":
        reasons.append("operator_confirmation_mismatch")

    moment = now or datetime.now(timezone.utc)
    try:
        issued = datetime.fromisoformat(str(row.get("issued_at") or "").replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(row.get("expires_at") or "").replace("Z", "+00:00"))
        if issued.tzinfo is None or expires.tzinfo is None or not issued <= moment <= expires:
            reasons.append("authorization_stale_or_not_yet_valid")
        if expires <= issued or expires - issued > timedelta(hours=24):
            reasons.append("authorization_validity_window_invalid")
    except ValueError:
        reasons.append("authorization_time_invalid")
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "authorization_id": authorization_id,
        "execution_manifest_sha256": expected,
        "provider_contacted": False,
    }


def _consume_authorization_exclusive(
    runtime_root: Path,
    authorization_artifact_sha256: str,
    authorization: Mapping[str, Any],
) -> Path:
    authorization_id = str(authorization["authorization_id"])
    path = runtime_root / "experiment_execution_consumptions" / f"{authorization_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract_version": "g-corrob1.r2.execution-authorization-consumption.1",
        "authorization_id": authorization_id,
        "manifest_id": MANIFEST_ID,
        "authorization_artifact_sha256": authorization_artifact_sha256,
        "execution_manifest_sha256": authorization["execution_manifest_sha256"],
        "consumed_at": _now(),
        "consumed_for": AUTHORIZATION_SCOPE,
        "one_run_only": True,
        "belief_effects": "none",
    }
    payload["receipt_sha256"] = _canonical(payload)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=1, sort_keys=True))
        handle.flush()
        os.fsync(handle.fileno())
    return path


def _write_terminal_receipt(
    runtime_root: Path,
    *,
    authorization: Mapping[str, Any],
    run_id: str,
    state: str,
    reason_code: str,
    run_store: str = "",
) -> dict[str, Any]:
    authorization_id = str(authorization["authorization_id"])
    directory = runtime_root / "experiment_execution_terminal_receipts"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{authorization_id}.json"
    seed = {
        "contract_version": "g-corrob1.r2.execution-terminal-receipt.1",
        "manifest_id": MANIFEST_ID,
        "authorization_id": authorization_id,
        "execution_manifest_sha256": str(authorization["execution_manifest_sha256"]),
        "run_id": str(run_id),
        "terminal_state": str(state),
        "reason_code": str(reason_code)[:120],
        "run_manifest_sha256": "",
        "score_record_sha256": "",
        "provider_call_count": 0,
        "belief_effects": "none",
        "finished_at": _now(),
    }
    store = Path(run_store) if run_store else None
    if store and (store / "run.json").is_file():
        run_manifest_bytes = (store / "run.json").read_bytes()
        seed["run_manifest_sha256"] = hashlib.sha256(run_manifest_bytes).hexdigest()
        try:
            seed["provider_call_count"] = int(json.loads(run_manifest_bytes).get("provider_contacts") or 0)
        except (ValueError, TypeError):
            seed["provider_call_count"] = 0
    if store and (store / "score.json").is_file():
        seed["score_record_sha256"] = hashlib.sha256((store / "score.json").read_bytes()).hexdigest()
    seed["receipt_sha256"] = _canonical(seed)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(seed, indent=1, sort_keys=True))
        handle.flush()
        os.fsync(handle.fileno())
    return {**seed, "terminal_reference": f"experiment-terminal:{authorization_id}"}


def _public_result(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "manifest_id": MANIFEST_ID,
        "run_id": str(receipt.get("run_id") or ""),
        "state": str(receipt.get("terminal_state") or "failed"),
        "reason_code": str(receipt.get("reason_code") or ""),
        "terminal_reference": str(receipt.get("terminal_reference") or ""),
        "receipt_sha256": str(receipt.get("receipt_sha256") or ""),
        "provider_call_count": int(receipt.get("provider_call_count") or 0),
        "belief_effects": "none",
        "semantic_results_exposed": False,
        "source_modified": False,
        "authorization_created": False,
    }


def _execute_authorized_frozen_experiment(
    manifest_id: str,
    *,
    runtime_root: str | Path | None = None,
    provider_adapter: Any | None = None,
    activity: Any | None = None,
    cancel_event: Any | None = None,
) -> dict[str, Any]:
    if str(manifest_id) != MANIFEST_ID:
        raise PermissionError("manifest_not_registered")
    root = Path(runtime_root) if runtime_root is not None else _default_runtime_root()
    _source_path, authorization, authorization_artifact_sha256 = _load_single_authorization(root)
    check = verify_execution_authorization(authorization)
    if not check["valid"]:
        raise PermissionError("execution_authorization_rejected:" + ",".join(check["reasons"]))

    try:
        _consume_authorization_exclusive(root, authorization_artifact_sha256, authorization)
    except FileExistsError as error:
        raise PermissionError("execution_authorization_already_consumed") from error

    from g_corrob1_activity import CorrobActivity
    from g_corrob1_provider import OllamaExperimentAdapter
    from g_corrob1_runner import execute as execute_runner

    run_id = "gcorrob1r2_authorized_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = root / "experiments" / "G-CORROB1-R2" / "runs"
    adapter = provider_adapter or OllamaExperimentAdapter()
    observer = activity or CorrobActivity(run_id, root=root)
    run_store = ""
    try:
        if cancel_event is not None and cancel_event.is_set():
            raise ExperimentExecutionCancelled("cancelled_before_provider_inspection")
        preflight = adapter.inspect_model(
            str(authorization["execution_manifest"]["requested_model"]),
            allow_provider_contact=True,
        )
        def provider_call(request_id: str, body: Mapping[str, Any]) -> Any:
            if cancel_event is not None and cancel_event.is_set():
                raise ExperimentExecutionCancelled("cancelled_before_next_generation_call")
            return adapter.generate(request_id, body, allow_provider_contact=True)

        result = execute_runner(
            provider_call=provider_call,
            preflight_receipt=preflight,
            run_root=run_root,
            run_id=run_id,
            activity=observer,
            synthetic_fixture=False,
            authorization=authorization,
        )
        run_store = str(result.get("store") or "")
        receipt = _write_terminal_receipt(
            root,
            authorization=authorization,
            run_id=run_id,
            state=str(result.get("state") or "failed"),
            reason_code=str(result.get("reason") or "frozen_runner_terminal"),
            run_store=run_store,
        )
        return _public_result(receipt)
    except BaseException as error:
        candidate_store = run_root / run_id
        run_store = str(candidate_store) if candidate_store.exists() else ""
        try:
            observer.emit(
                "capability_terminal_failure",
                state="cancelled" if isinstance(error, (KeyboardInterrupt, ExperimentExecutionCancelled)) else "failed",
                stage="finalization",
                metrics={"scheduled_calls": EXPECTED_CALLS},
            )
        except Exception:
            pass
        receipt = _write_terminal_receipt(
            root,
            authorization=authorization,
            run_id=run_id,
            state="cancelled" if isinstance(error, (KeyboardInterrupt, ExperimentExecutionCancelled)) else "failed",
            reason_code=f"{type(error).__name__}"[:120],
            run_store=run_store,
        )
        if isinstance(error, KeyboardInterrupt):
            raise
        return _public_result(receipt)


def execute_authorized_frozen_experiment(manifest_id: str) -> dict[str, Any]:
    """Invoke the one registered capability. No path/configuration override is public."""
    return _execute_authorized_frozen_experiment(manifest_id)


def _process_authorized_frozen_experiment_command(
    text: str,
    *,
    runtime_root: str | Path | None = None,
    provider_adapter: Any | None = None,
    activity: Any | None = None,
    cancel_event: Any | None = None,
) -> dict[str, Any]:
    manifest_id = parse_authorized_experiment_command(text)
    if not manifest_id:
        return {"active": False}
    try:
        result = _execute_authorized_frozen_experiment(
            manifest_id,
            runtime_root=runtime_root,
            provider_adapter=provider_adapter,
            activity=activity,
            cancel_event=cancel_event,
        )
        state = result["state"]
        response = (
            f"Authorized frozen experiment {manifest_id} reached terminal state `{state}`. "
            f"Run reference: `{result['run_id']}`. Terminal receipt: `{result['terminal_reference']}`. "
            "The experimental interpretation remains a separate review step."
        )
        return {"active": True, "response": response, "receipt": result}
    except Exception as error:
        reason = str(error).split(":", 1)[0][:120]
        return {
            "active": True,
            "response": (
                f"I did not execute {manifest_id}. The governed capability stopped at `{reason}`. "
                "No authorization was created or inferred."
            ),
            "receipt": {
                "manifest_id": manifest_id,
                "state": "refused",
                "reason_code": reason,
                "belief_effects": "none",
                "semantic_results_exposed": False,
                "source_modified": False,
            },
        }


def process_authorized_frozen_experiment_command(text: str, *, cancel_event: Any | None = None) -> dict[str, Any]:
    """Conversation adapter; text and the runtime cancellation signal are the only inputs."""
    return _process_authorized_frozen_experiment_command(text, cancel_event=cancel_event)


__all__ = [
    "MANIFEST_ID", "CONTRACT_VERSION", "AUTHORIZATION_SCOPE", "EXPECTED_CALLS",
    "EXPECTED_PAIRS", "parse_authorized_experiment_command",
    "verify_execution_authorization", "execute_authorized_frozen_experiment",
    "process_authorized_frozen_experiment_command",
]
