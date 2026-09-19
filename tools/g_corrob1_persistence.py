from __future__ import annotations

"""Append-only scientific records for G-CORROB1-R2 candidate runs."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from g_corrob1_contract import canonical_digest


CONTRACT_VERSION = "g-corrob1.r2.persistence-candidate.1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(value), indent=1, ensure_ascii=False, sort_keys=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def _replace(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(dict(value), indent=1, ensure_ascii=False, sort_keys=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        temp = Path(handle.name)
    os.replace(temp, path)


class RunStore:
    def __init__(self, run_root: str | Path, run_id: str, *, create: bool,
                 run_manifest: Mapping[str, Any] | None = None) -> None:
        self.root = Path(run_root) / run_id
        self.run_id = str(run_id)
        self.manifest_path = self.root / "run.json"
        if create:
            self.root.mkdir(parents=True, exist_ok=False)
            manifest = {
                "contract_version": CONTRACT_VERSION, "run_id": self.run_id,
                "state": "preparing", "started": now(), "updated": now(), "finished": None,
                "belief_effects": "none", "provider_contacts": 0, "returned_responses": 0,
                "calls_persisted": 0, "pairs_persisted": 0, "valid_verdict": False,
                **dict(run_manifest or {}),
            }
            _write_new(self.manifest_path, manifest)
        elif not self.manifest_path.is_file():
            raise FileNotFoundError("run_manifest_missing")

    def manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def update(self, **changes: Any) -> dict[str, Any]:
        value = self.manifest()
        if value.get("state") in {"complete", "incomplete", "failed"}:
            raise ValueError("terminal_run_is_immutable")
        value.update(changes)
        value["updated"] = now()
        _replace(self.manifest_path, value)
        return value

    def write_call(self, record: Mapping[str, Any]) -> Path:
        call_id = str(record.get("call_id") or "")
        if not call_id:
            raise ValueError("call_id_missing")
        path = self.root / "calls" / f"{call_id}.json"
        payload = dict(record)
        payload["record_sha256"] = canonical_digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        _write_new(path, payload)
        manifest = self.manifest()
        manifest["calls_persisted"] = int(manifest.get("calls_persisted") or 0) + 1
        manifest["provider_contacts"] = int(manifest.get("provider_contacts") or 0) + int(bool(record.get("provider_contacted")))
        manifest["returned_responses"] = int(manifest.get("returned_responses") or 0) + int(not bool(record.get("provider_error")))
        manifest["updated"] = now()
        _replace(self.manifest_path, manifest)
        return path

    def write_pair(self, record: Mapping[str, Any]) -> Path:
        pair_id = str(record.get("pair_id") or "")
        if not pair_id:
            raise ValueError("pair_id_missing")
        path = self.root / "pairs" / f"{pair_id}.json"
        payload = dict(record)
        payload["record_sha256"] = canonical_digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        _write_new(path, payload)
        manifest = self.manifest()
        manifest["pairs_persisted"] = int(manifest.get("pairs_persisted") or 0) + 1
        manifest["updated"] = now()
        _replace(self.manifest_path, manifest)
        return path

    def write_score(self, report: Mapping[str, Any]) -> Path:
        path = self.root / "score.json"
        payload = dict(report)
        payload["report_sha256"] = canonical_digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        _write_new(path, payload)
        return path

    def finish(self, *, state: str, reason: str, valid_verdict: bool) -> dict[str, Any]:
        if state not in {"complete", "incomplete", "failed"}:
            raise ValueError("invalid_terminal_state")
        value = self.manifest()
        if value.get("state") in {"complete", "incomplete", "failed"}:
            raise ValueError("terminal_run_is_immutable")
        value.update(state=state, reason=str(reason), valid_verdict=bool(valid_verdict), finished=now(), updated=now())
        _replace(self.manifest_path, value)
        return value

    def call_records(self) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted((self.root / "calls").glob("*.json"))]

    def pair_records(self) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted((self.root / "pairs").glob("*.json"))]


__all__ = ["CONTRACT_VERSION", "RunStore", "now"]
