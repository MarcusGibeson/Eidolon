from __future__ import annotations

"""Separately governed live mechanics pilot for G-ROUTE1.

The module never imports the scientific corpus, gold, schedule, validators, or
scorer. Its nine synthetic calls cannot become qualification observations.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping

from g_route1_execution_contract import DATA, canonical_json, json_digest, load_model_bindings
from g_route1_provider import OllamaRouteAdapter, verify_model_receipts


CONTRACT_VERSION = "g-route1.mechanical-pilot.v1"
PILOT_IDENTITY = "PX-ROUTE-MECHANICS-01"
EXPECTED_GENERATION_CALLS = 9
TERMINAL_STATES = frozenset({"complete", "failed", "incomplete", "cancelled"})
FROZEN_CONTENT_DIGEST = "feebf0e418e0cdab94463cdc0464c701e61a867deab72ee1cf93b26a33d7dfb1"
FROZEN_LITERAL_SHA256 = "77138604fc0b63b6860b1b9c0aaa4b43b68cd7560e8a4f8dfffabfdc1d1673cf"
FREEZE_PATH = DATA / "EXECUTION_FREEZE_CANDIDATE.json"
SYNTHETIC_SYSTEM = (
    "This is a provider mechanics check, not a knowledge evaluation. "
    "Return one compact JSON object and no explanation."
)
SYNTHETIC_PROMPT = (
    'Choose one token from ["amber","cedar","delta","ember","fjord","granite"] '
    'using normal sampling. Return exactly {"token":"<chosen token>"}.'
)
TOKENS = frozenset({"amber", "cedar", "delta", "ember", "fjord", "granite"})


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical_file_digest(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _literal_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pilot_definition() -> dict[str, Any]:
    bindings = load_model_bindings()
    rows = []
    seed_base = {"small": 51001, "mid": 52001, "large": 53001}
    for binding in bindings["bindings"]:
        tier = binding["tier"]
        for label, seed in (("same-a", seed_base[tier]), ("same-b", seed_base[tier]), ("different", seed_base[tier] + 1)):
            rows.append({
                "position": len(rows) + 1,
                "call_id": f"GROUTE1-PILOT-{tier}-{label}",
                "fixture_id": PILOT_IDENTITY,
                "model_tier": tier,
                "model": binding["model"],
                "manifest_digest": binding["manifest_digest"],
                "model_blob_sha256": binding["model_blob_sha256"],
                "seed": seed,
                "seed_role": label,
            })
    value = {
        "contract_version": CONTRACT_VERSION,
        "pilot_fixture_id": PILOT_IDENTITY,
        "scientific_observation": False,
        "synthetic_input_sha256": json_digest({"system": SYNTHETIC_SYSTEM, "prompt": SYNTHETIC_PROMPT}),
        "generation_configuration": bindings["generation_configuration"],
        "calls": rows,
        "expected_generation_calls": EXPECTED_GENERATION_CALLS,
        "pause_after_persisted_calls": 1,
        "scientific_retries": 0,
        "output_repair_calls": 0,
        "production_routing": False,
        "belief_effects": "none",
    }
    value["pilot_definition_sha256"] = json_digest(value)
    return value


def verify_pilot_definition(value: Mapping[str, Any]) -> dict[str, Any]:
    reasons = []
    expected = pilot_definition()
    if dict(value) != expected:
        reasons.append("pilot_definition_drift")
    rows = list(value.get("calls") or [])
    if len(rows) != EXPECTED_GENERATION_CALLS or len({row.get("call_id") for row in rows}) != EXPECTED_GENERATION_CALLS:
        reasons.append("pilot_call_identity_mismatch")
    if any(row.get("fixture_id") != PILOT_IDENTITY for row in rows):
        reasons.append("scientific_fixture_namespace_contamination")
    if {row.get("model_tier") for row in rows} != {"small", "mid", "large"}:
        reasons.append("pilot_model_tier_coverage_mismatch")
    for tier in ("small", "mid", "large"):
        seeds = [row.get("seed") for row in rows if row.get("model_tier") == tier]
        if len(seeds) != 3 or seeds[0] != seeds[1] or seeds[2] == seeds[0]:
            reasons.append(f"pilot_seed_design_mismatch:{tier}")
    return {"valid": not reasons, "reasons": sorted(set(reasons))}


def verify_scientific_freeze() -> dict[str, Any]:
    manifest = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    reasons = []
    if manifest.get("execution_freeze_content_sha256") != FROZEN_CONTENT_DIGEST:
        reasons.append("execution_freeze_content_digest_mismatch")
    if _literal_digest(FREEZE_PATH) != FROZEN_LITERAL_SHA256:
        reasons.append("execution_freeze_literal_digest_mismatch")
    root = Path(__file__).resolve().parents[1]
    for relative, expected in manifest.get("artifacts", {}).items():
        path = root / relative
        if not path.is_file() or _canonical_file_digest(path) != expected:
            reasons.append(f"frozen_dependency_drift:{relative}")
    return {
        "valid": not reasons, "reasons": sorted(set(reasons)),
        "guarded_digest": json_digest(manifest.get("artifacts", {})),
        "execution_freeze_content_sha256": manifest.get("execution_freeze_content_sha256"),
    }


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _replace(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        handle.write(json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _seal(value: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value)
    row["record_sha256"] = json_digest(row)
    return row


class PilotStore:
    def __init__(self, root: str | Path, pilot_id: str, *, create: bool, definition: Mapping[str, Any] | None = None) -> None:
        self.root = Path(root) / pilot_id
        self.manifest_path = self.root / "pilot.json"
        self.checkpoint_path = self.root / "checkpoint.json"
        if create:
            self.root.mkdir(parents=True, exist_ok=False)
            freeze = verify_scientific_freeze()
            value = {
                "contract_version": CONTRACT_VERSION, "pilot_id": pilot_id,
                "pilot_fixture_id": PILOT_IDENTITY, "state": "preparing",
                "started": now(), "updated": now(), "finished": None,
                "pilot_definition": dict(definition or pilot_definition()),
                "pilot_definition_sha256": str((definition or pilot_definition())["pilot_definition_sha256"]),
                "scientific_freeze_content_sha256": FROZEN_CONTENT_DIGEST,
                "guarded_digest": freeze["guarded_digest"],
                "generation_calls": 0, "release_requests": 0, "calls_persisted": 0,
                "scientific_observations": 0, "benchmark_launches": 0,
                "production_routing": False, "belief_effects": "none",
            }
            _write_new(self.manifest_path, value)
            self.write_checkpoint(next_position=1, state="preparing")
        elif not self.manifest_path.is_file():
            raise FileNotFoundError("pilot_manifest_missing")

    def manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def update(self, **changes: Any) -> dict[str, Any]:
        value = self.manifest()
        if value.get("state") in {"complete", "failed", "incomplete", "cancelled"}:
            raise ValueError("terminal_pilot_immutable")
        value.update(changes)
        value["updated"] = now()
        _replace(self.manifest_path, value)
        return value

    def write_call(self, record: Mapping[str, Any]) -> None:
        call_id = str(record.get("call_id") or "")
        _write_new(self.root / "calls" / f"{call_id}.json", _seal(record))
        value = self.manifest()
        value["generation_calls"] += 1
        value["calls_persisted"] += 1
        value["updated"] = now()
        _replace(self.manifest_path, value)

    def write_release(self, record: Mapping[str, Any]) -> None:
        _write_new(self.root / "release" / "paused-model-release.json", _seal(record))
        value = self.manifest()
        value["release_requests"] += 1
        value["updated"] = now()
        _replace(self.manifest_path, value)

    def write_checkpoint(
        self, *, next_position: int, state: str, completed_position: int | None = None,
    ) -> dict[str, Any]:
        if self.checkpoint_path.is_file():
            existing = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            if existing.get("state") in TERMINAL_STATES:
                raise ValueError("terminal_pilot_checkpoint_immutable")
        value = {
            "contract_version": "g-route1.mechanical-pilot-checkpoint.v1",
            "pilot_id": self.root.name, "next_position": int(next_position),
            "calls_persisted": len(list((self.root / "calls").glob("*.json"))),
            "state": state, "guarded_digest": verify_scientific_freeze()["guarded_digest"],
            "pilot_definition_sha256": pilot_definition()["pilot_definition_sha256"],
            "updated": now(),
        }
        if completed_position is not None:
            value["completed_position"] = int(completed_position)
        value["checkpoint_sha256"] = json_digest(value)
        _replace(self.checkpoint_path, value)
        return value

    def checkpoint(self) -> dict[str, Any]:
        value = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        observed = value.pop("checkpoint_sha256", "")
        if observed != json_digest(value):
            raise ValueError("pilot_checkpoint_digest_mismatch")
        value["checkpoint_sha256"] = observed
        if value["calls_persisted"] != len(self.calls()) or value["next_position"] != len(self.calls()) + 1:
            raise ValueError("pilot_checkpoint_lineage_mismatch")
        return value

    def calls(self) -> list[dict[str, Any]]:
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in (self.root / "calls").glob("*.json")]
        for row in rows:
            digest = row.pop("record_sha256", "")
            if digest != json_digest(row):
                raise ValueError("pilot_call_record_digest_mismatch")
            row["record_sha256"] = digest
        return sorted(rows, key=lambda row: row["position"])

    def terminal_receipt(self) -> dict[str, Any]:
        path = self.root / "terminal_receipt.json"
        if not path.is_file():
            raise FileNotFoundError("pilot_terminal_receipt_missing")
        value = json.loads(path.read_text(encoding="utf-8"))
        observed = value.pop("record_sha256", "")
        if observed != json_digest(value):
            raise ValueError("pilot_terminal_receipt_digest_mismatch")
        value["record_sha256"] = observed
        return value

    def seal_terminal_checkpoint(self, *, state: str, expected_calls: int) -> dict[str, Any]:
        if state not in TERMINAL_STATES:
            raise ValueError("pilot_checkpoint_terminal_state_required")
        manifest = self.manifest()
        receipt = self.terminal_receipt()
        records = self.calls()
        if manifest.get("state") != state or receipt.get("state") != state:
            raise ValueError("pilot_terminal_state_disagreement")
        if state == "complete" and len(records) != expected_calls:
            raise ValueError("pilot_terminal_call_count_mismatch")
        existing = self.checkpoint()
        expected_next = len(records) + 1
        if existing.get("state") in TERMINAL_STATES:
            if (
                existing.get("state") == state
                and existing.get("next_position") == expected_next
                and existing.get("completed_position") == len(records)
            ):
                return existing
            raise ValueError("pilot_terminal_checkpoint_conflict")
        if existing.get("next_position") != expected_next:
            raise ValueError("pilot_terminal_checkpoint_position_mismatch")
        return self.write_checkpoint(
            next_position=expected_next, state=state, completed_position=len(records),
        )

    def finish(self, state: str, reason: str) -> dict[str, Any]:
        value = self.manifest()
        if value.get("state") in TERMINAL_STATES:
            raise ValueError("terminal_pilot_immutable")
        value.update(state=state, reason=reason, finished=now(), updated=now())
        _replace(self.manifest_path, value)
        return value

    def write_terminal_receipt(self, receipt: Mapping[str, Any]) -> None:
        _write_new(self.root / "terminal_receipt.json", _seal(receipt))


def verify_terminal_views(
    store: PilotStore, activity_projection: Mapping[str, Any], *, expected_calls: int,
) -> dict[str, Any]:
    manifest = store.manifest()
    receipt = store.terminal_receipt()
    checkpoint = store.checkpoint()
    states = {
        "pilot": manifest.get("state"),
        "receipt": receipt.get("state"),
        "activity": activity_projection.get("state"),
        "checkpoint": checkpoint.get("state"),
    }
    reasons = []
    if set(states.values()) != {"complete"}:
        reasons.append("terminal_state_disagreement")
    if checkpoint.get("completed_position") != expected_calls:
        reasons.append("terminal_completed_position_mismatch")
    if checkpoint.get("next_position") != expected_calls + 1:
        reasons.append("terminal_next_position_mismatch")
    if manifest.get("calls_persisted") != expected_calls or receipt.get("generation_calls") != expected_calls:
        reasons.append("terminal_call_count_mismatch")
    return {"valid": not reasons, "reasons": reasons, "states": states, "checkpoint": checkpoint}


class PilotActivity:
    def __init__(self, pilot_id: str, *, root: str | Path, resume: bool = False) -> None:
        source = Path(__file__).resolve().parents[1] / "conscious_agent"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from activity import Activity
        if resume:
            self.activity = Activity.reopen(pilot_id, root=root)
        else:
            self.activity = Activity(
                pilot_id, "adaptive_routing_mechanical_pilot", "Three-tier provider mechanics",
                "G-ROUTE1 mechanical pilot", root=root,
                stages=("preflight", "collection", "pause_verification", "verification", "finalization"),
                identities={"pilot_id": pilot_id, "pilot_fixture_id": PILOT_IDENTITY},
                governance={"scientific_observation": False, "production_routing": False, "belief_effects": "none"},
            )

    def emit(self, event: str, *, state: str, stage: str, completed: int, total: int = EXPECTED_GENERATION_CALLS, provider_calls: int = 0) -> dict[str, Any]:
        return self.activity.update(
            event, state=state, stage=stage, units=(completed, total, "pilot calls"),
            metrics={"provider_calls": provider_calls},
        )


def _request_body(call: Mapping[str, Any]) -> dict[str, Any]:
    config = load_model_bindings()["generation_configuration"]
    options = dict(config["options"])
    options["seed"] = call["seed"]
    return {
        "model": call["model"], "system": SYNTHETIC_SYSTEM, "prompt": SYNTHETIC_PROMPT,
        "stream": False, "think": False, "options": options,
    }


def _parse_mechanical_output(raw: str) -> tuple[dict[str, Any] | None, str]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None, "malformed_json"
    if not isinstance(value, dict) or set(value) != {"token"} or value.get("token") not in TOKENS:
        return value if isinstance(value, dict) else None, "mechanical_schema_mismatch"
    return value, "valid"


def _release_model(endpoint: str, model: str) -> dict[str, Any]:
    import requests
    started = time.perf_counter()
    with requests.Session() as session:
        response = session.post(
            endpoint.rstrip("/") + "/api/generate",
            json={"model": model, "keep_alive": 0, "stream": False}, timeout=(5, 120),
        )
        raw = bytes(response.content)
        response.raise_for_status()
        ps_response = session.get(endpoint.rstrip("/") + "/api/ps", timeout=(5, 30))
        ps_response.raise_for_status()
    loaded = {str(row.get("model") or row.get("name") or "") for row in ps_response.json().get("models", [])}
    return {
        "request_type": "model_release_no_generation", "model": model,
        "provider_contacted": True, "generation_tokens": 0,
        "raw_body_b64": base64.b64encode(raw).decode("ascii"),
        "raw_body_sha256": hashlib.sha256(raw).hexdigest(),
        "model_absent_after_release": model not in loaded,
        "loaded_models_after_release": sorted(loaded),
        "latency_seconds": round(time.perf_counter() - started, 6),
    }


def _seed_findings(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    findings = {}
    for tier in ("small", "mid", "large"):
        rows = [row for row in records if row["model_tier"] == tier]
        rows.sort(key=lambda row: row["position"])
        same_equal = rows[0]["raw_output"] == rows[1]["raw_output"]
        different_changed = rows[0]["raw_output"] != rows[2]["raw_output"]
        if not same_equal:
            classification = "inconsistent"
        elif different_changed:
            classification = "reproducible_and_distinguishable_observed_not_provider_attested"
        else:
            classification = "reproducible_observed_seed_effect_unverifiable"
        findings[tier] = {
            "same_seed_output_equal": same_equal,
            "different_seed_output_changed": different_changed,
            "classification": classification,
            "internal_seed_honoring_attested": False,
        }
    return findings


def _preflight(adapter: OllamaRouteAdapter) -> list[dict[str, Any]]:
    receipts = adapter.inspect_models(allow_metadata_inspection=True)
    verified = verify_model_receipts(receipts)
    if not verified["valid"]:
        raise RuntimeError("pilot_model_preflight_failed:" + ",".join(verified["reasons"]))
    return receipts


def run_start(*, pilot_id: str, root: Path, activity_root: Path, endpoint: str, authorization_digest: str) -> dict[str, Any]:
    if authorization_digest != FROZEN_CONTENT_DIGEST:
        raise PermissionError("pilot_authorization_freeze_mismatch")
    freeze = verify_scientific_freeze()
    if not freeze["valid"]:
        raise RuntimeError("scientific_freeze_drift:" + ",".join(freeze["reasons"]))
    definition = pilot_definition()
    if not verify_pilot_definition(definition)["valid"]:
        raise RuntimeError("pilot_definition_invalid")
    store = PilotStore(root, pilot_id, create=True, definition=definition)
    activity = PilotActivity(pilot_id, root=activity_root)
    adapter = OllamaRouteAdapter(endpoint)
    receipts = _preflight(adapter)
    store.update(state="running", model_receipts=receipts)
    activity.emit("pilot_running", state="running", stage="collection", completed=0)
    call = definition["calls"][0]
    body = _request_body(call)
    result = adapter.generate(call["call_id"], body, allow_generation=True).as_dict()
    parsed, parse_status = _parse_mechanical_output(str(result.get("raw_output") or ""))
    record = {
        **call, "activity_id": pilot_id, "checkpoint_before": 1,
        "requested_generation_configuration": definition["generation_configuration"],
        "submitted_body_sha256": result["submitted_body_sha256"],
        "synthetic_input_sha256": definition["synthetic_input_sha256"],
        "raw_provider_body_b64": result["raw_body_b64"],
        "raw_provider_body_sha256": result["raw_body_sha256"],
        "provider_envelope": result["envelope"], "raw_output": result["raw_output"],
        "output_field": result["output_field"], "parsed_output": parsed,
        "parse_status": parse_status, "timing_seconds": result["latency_seconds"],
        "token_accounting": result["metrics"], "returned_model": result["returned_model"],
        "provider_error": result["error"], "fresh_session": {
            "new_http_session": True, "conversation_context_sent": False,
            "server_session_identifier_present": False,
        },
        "scientific_observation": False, "production_routing": False, "belief_effects": "none",
    }
    if result["error"] or result["returned_model"] != call["model"] or parse_status != "valid":
        store.write_call(record)
        store.write_checkpoint(next_position=2, state="incomplete")
        store.finish("incomplete", "first_live_call_failed_mechanical_contract")
        activity.emit("pilot_incomplete", state="incomplete", stage="finalization", completed=1, provider_calls=1)
        return {"state": "incomplete", "pilot_id": pilot_id, "generation_calls": 1}
    store.write_call(record)
    store.write_checkpoint(next_position=2, state="paused")
    store.update(state="paused", paused_at=now())
    paused_projection = activity.emit("pilot_paused", state="paused", stage="pause_verification", completed=1, provider_calls=1)
    release = _release_model(endpoint, call["model"])
    store.write_release(release)
    return {
        "state": "paused", "pilot_id": pilot_id, "activity_id": pilot_id,
        "generation_calls": 1, "release_requests": 1,
        "release": release, "activity": paused_projection,
    }


def run_resume(*, pilot_id: str, root: Path, activity_root: Path, endpoint: str, authorization_digest: str) -> dict[str, Any]:
    if authorization_digest != FROZEN_CONTENT_DIGEST:
        raise PermissionError("pilot_authorization_freeze_mismatch")
    freeze = verify_scientific_freeze()
    if not freeze["valid"]:
        raise RuntimeError("scientific_freeze_drift:" + ",".join(freeze["reasons"]))
    store = PilotStore(root, pilot_id, create=False)
    manifest = store.manifest()
    if manifest.get("state") != "paused":
        raise ValueError("pilot_not_paused")
    definition = manifest["pilot_definition"]
    if not verify_pilot_definition(definition)["valid"]:
        raise ValueError("pilot_definition_drift")
    checkpoint = store.checkpoint()
    if checkpoint["guarded_digest"] != freeze["guarded_digest"]:
        raise ValueError("pilot_resume_guard_drift")
    adapter = OllamaRouteAdapter(endpoint)
    receipts = _preflight(adapter)
    if receipts != manifest.get("model_receipts"):
        raise ValueError("pilot_resume_model_receipt_drift")
    activity = PilotActivity(pilot_id, root=activity_root, resume=True)
    existing = store.calls()
    activity.emit("pilot_resumed", state="running", stage="collection", completed=len(existing), provider_calls=len(existing))
    store.update(state="running", resumed_at=now())
    for call in definition["calls"][checkpoint["next_position"] - 1:]:
        if not verify_scientific_freeze()["valid"]:
            raise RuntimeError("pilot_mutation_guard_failed")
        body = _request_body(call)
        result = adapter.generate(call["call_id"], body, allow_generation=True).as_dict()
        parsed, parse_status = _parse_mechanical_output(str(result.get("raw_output") or ""))
        record = {
            **call, "activity_id": pilot_id, "checkpoint_before": call["position"],
            "requested_generation_configuration": definition["generation_configuration"],
            "submitted_body_sha256": result["submitted_body_sha256"],
            "synthetic_input_sha256": definition["synthetic_input_sha256"],
            "raw_provider_body_b64": result["raw_body_b64"],
            "raw_provider_body_sha256": result["raw_body_sha256"],
            "provider_envelope": result["envelope"], "raw_output": result["raw_output"],
            "output_field": result["output_field"], "parsed_output": parsed,
            "parse_status": parse_status, "timing_seconds": result["latency_seconds"],
            "token_accounting": result["metrics"], "returned_model": result["returned_model"],
            "provider_error": result["error"], "fresh_session": {
                "new_http_session": True, "conversation_context_sent": False,
                "server_session_identifier_present": False,
            },
            "scientific_observation": False, "production_routing": False, "belief_effects": "none",
        }
        store.write_call(record)
        calls = store.calls()
        store.write_checkpoint(next_position=call["position"] + 1, state="running")
        activity.emit("pilot_call_persisted", state="running", stage="collection", completed=len(calls), provider_calls=len(calls))
        if result["error"] or result["returned_model"] != call["model"] or parse_status != "valid":
            store.finish("incomplete", f"mechanical_call_failed:{call['call_id']}")
            activity.emit("pilot_incomplete", state="incomplete", stage="finalization", completed=len(calls), provider_calls=len(calls))
            return {"state": "incomplete", "pilot_id": pilot_id, "generation_calls": len(calls)}
    records = store.calls()
    if len(records) != EXPECTED_GENERATION_CALLS or [row["position"] for row in records] != list(range(1, 10)):
        store.finish("incomplete", "pilot_call_accounting_mismatch")
        activity.emit("pilot_incomplete", state="incomplete", stage="finalization", completed=len(records), provider_calls=len(records))
        return {"state": "incomplete", "pilot_id": pilot_id, "generation_calls": len(records)}
    if not verify_scientific_freeze()["valid"]:
        raise RuntimeError("pilot_terminal_mutation_guard_failed")
    findings = _seed_findings(records)
    terminal = {
        "contract_version": "g-route1.mechanical-pilot-terminal.v1",
        "pilot_id": pilot_id, "pilot_fixture_id": PILOT_IDENTITY,
        "state": "complete", "generation_calls": len(records),
        "release_requests": store.manifest()["release_requests"],
        "call_ids": [row["call_id"] for row in records],
        "seed_findings": findings,
        "fresh_session_finding": {
            "new_http_session_per_generation": True,
            "conversation_context_sent": False,
            "provider_process_isolation": False,
            "provider_internal_state_attestation": "unavailable",
        },
        "mutation_guard": "passed", "scientific_observations": 0,
        "benchmark_launches": 0, "production_routing": False, "belief_effects": "none",
        "completed": now(),
    }
    store.write_terminal_receipt(terminal)
    store.finish("complete", "mechanical_pilot_complete")
    activity_projection = activity.emit("pilot_complete", state="complete", stage="finalization", completed=len(records), provider_calls=len(records))
    store.seal_terminal_checkpoint(state="complete", expected_calls=EXPECTED_GENERATION_CALLS)
    terminal_views = verify_terminal_views(
        store, activity_projection, expected_calls=EXPECTED_GENERATION_CALLS,
    )
    if not terminal_views["valid"]:
        raise RuntimeError("pilot_terminal_view_mismatch:" + ",".join(terminal_views["reasons"]))
    return {
        **terminal, "activity": activity_projection, "terminal_views": terminal_views,
        "runtime_root": str(store.root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the separately authorized G-ROUTE1 mechanical pilot.")
    parser.add_argument("phase", choices=("start", "resume"))
    parser.add_argument("--pilot-id", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--activity-root", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--authorize-freeze", required=True)
    args = parser.parse_args()
    function = run_start if args.phase == "start" else run_resume
    result = function(
        pilot_id=args.pilot_id, root=Path(args.root), activity_root=Path(args.activity_root),
        endpoint=args.endpoint, authorization_digest=args.authorize_freeze,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("state") in {"paused", "complete"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
