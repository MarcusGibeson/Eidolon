from __future__ import annotations

"""Append-only scientific persistence and resumable checkpoints for G-ROUTE1."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from g_route1_execution_contract import EXPECTED_CALLS, canonical_json, json_digest


CONTRACT_VERSION = "g-route1.persistence.v1"
TERMINAL = frozenset({"complete", "incomplete", "failed", "cancelled"})


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def _replace(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent,
        prefix=path.name + ".", suffix=".tmp", delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _sealed_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["record_sha256"] = json_digest(payload)
    return payload


def verify_record(record: Mapping[str, Any]) -> bool:
    payload = dict(record)
    observed = str(payload.pop("record_sha256", ""))
    return len(observed) == 64 and observed == json_digest(payload)


class RunLease:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None

    def __enter__(self) -> "RunLease":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("x", encoding="utf-8", newline="\n")
        self.handle.write(json.dumps({"pid": os.getpid(), "created": now()}))
        self.handle.flush()
        os.fsync(self.handle.fileno())
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.handle:
            self.handle.close()
        self.path.unlink(missing_ok=True)


class RouteRunStore:
    def __init__(
        self, run_root: str | Path, run_id: str, *, create: bool,
        manifest: Mapping[str, Any] | None = None,
    ) -> None:
        self.base_root = Path(run_root)
        self.root = self.base_root / str(run_id)
        self.run_id = str(run_id)
        self.manifest_path = self.root / "run.json"
        self.checkpoint_path = self.root / "checkpoint.json"
        self.lease_path = self.base_root / ".g-route1-single-job.lease"
        if create:
            self.root.mkdir(parents=True, exist_ok=False)
            value = {
                "contract_version": CONTRACT_VERSION, "run_id": self.run_id,
                "state": "preparing", "started": now(), "updated": now(), "finished": None,
                "expected_calls": EXPECTED_CALLS, "calls_persisted": 0,
                "provider_contacts": 0, "returned_outputs": 0,
                "active_seconds": 0.0, "paused_seconds": 0.0,
                "belief_effects": "none", "production_routing_invoked": False,
                "valid_verdict": False, **dict(manifest or {}),
            }
            _write_new(self.manifest_path, value)
            self.write_checkpoint(next_position=1, state="preparing", guarded_digest=value.get("guarded_digest", ""))
        elif not self.manifest_path.is_file():
            raise FileNotFoundError("route_run_manifest_missing")

    def lease(self) -> RunLease:
        return RunLease(self.lease_path)

    def manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def update(self, **changes: Any) -> dict[str, Any]:
        value = self.manifest()
        if value.get("state") in TERMINAL:
            raise ValueError("terminal_route_run_is_immutable")
        value.update(changes)
        value["updated"] = now()
        _replace(self.manifest_path, value)
        return value

    def write_call(self, record: Mapping[str, Any]) -> Path:
        call_id = str(record.get("call_id") or "")
        if not call_id:
            raise ValueError("route_call_id_missing")
        path = self.root / "calls" / f"{call_id}.json"
        _write_new(path, _sealed_record(record))
        value = self.manifest()
        value["calls_persisted"] = int(value.get("calls_persisted") or 0) + 1
        value["provider_contacts"] = int(value.get("provider_contacts") or 0) + int(bool(record.get("provider_contacted")))
        value["returned_outputs"] = int(value.get("returned_outputs") or 0) + int(record.get("raw_output") is not None)
        value["updated"] = now()
        _replace(self.manifest_path, value)
        return path

    def write_checkpoint(self, *, next_position: int, state: str, guarded_digest: str) -> dict[str, Any]:
        value = {
            "contract_version": "g-route1.checkpoint.v1", "run_id": self.run_id,
            "next_position": int(next_position), "state": str(state),
            "calls_persisted": len(list((self.root / "calls").glob("*.json"))),
            "guarded_digest": str(guarded_digest), "updated": now(),
        }
        value["checkpoint_sha256"] = json_digest(value)
        _replace(self.checkpoint_path, value)
        return value

    def checkpoint(self) -> dict[str, Any]:
        value = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        observed = str(value.pop("checkpoint_sha256", ""))
        if observed != json_digest(value):
            raise ValueError("route_checkpoint_digest_mismatch")
        value["checkpoint_sha256"] = observed
        if value.get("run_id") != self.run_id:
            raise ValueError("route_checkpoint_run_mismatch")
        records = self.call_records()
        if value.get("calls_persisted") != len(records):
            raise ValueError("route_checkpoint_record_count_mismatch")
        if value.get("next_position") != len(records) + 1:
            raise ValueError("route_checkpoint_position_mismatch")
        return value

    def write_score(self, score: Mapping[str, Any]) -> Path:
        path = self.root / "score.json"
        _write_new(path, _sealed_record(score))
        return path

    def write_failure(self, record: Mapping[str, Any]) -> Path:
        sequence = len(list((self.root / "failures").glob("*.json"))) + 1
        path = self.root / "failures" / f"failure-{sequence:04d}.json"
        _write_new(path, _sealed_record(record))
        return path

    def finish(self, *, state: str, reason: str, valid_verdict: bool) -> dict[str, Any]:
        if state not in TERMINAL:
            raise ValueError("invalid_route_terminal_state")
        value = self.manifest()
        if value.get("state") in TERMINAL:
            raise ValueError("terminal_route_run_is_immutable")
        value.update(state=state, reason=str(reason), valid_verdict=bool(valid_verdict), finished=now(), updated=now())
        _replace(self.manifest_path, value)
        return value

    def call_records(self) -> list[dict[str, Any]]:
        records = [json.loads(path.read_text(encoding="utf-8")) for path in (self.root / "calls").glob("*.json")]
        if any(not verify_record(record) for record in records):
            raise ValueError("route_call_record_digest_mismatch")
        return sorted(records, key=lambda record: int(record.get("schedule_position") or 0))


__all__ = ["CONTRACT_VERSION", "RouteRunStore", "RunLease", "TERMINAL", "now", "verify_record"]
