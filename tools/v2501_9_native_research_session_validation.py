from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from conscious_agent.bounded_autonomous_web_research import BoundedResearchSessionStore
from conscious_agent.governed_public_web_research_adapter import GovernedPublicWebResearchAdapter, PublicWebResearchError


def digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MeasuredAdapter:
    def __init__(self):
        self.native = GovernedPublicWebResearchAdapter()
        self.search_calls = 0
        self.observe_calls = 0
        self.search_ms = 0.0
        self.observe_ms = 0.0
        self.queries: list[str] = []

    def describe(self):
        return self.native.describe()

    def search(self, query, *, limit, timeout_seconds):
        self.search_calls += 1
        self.queries.append(str(query))
        started = time.perf_counter()
        try:
            return self.native.search(query, limit=limit, timeout_seconds=timeout_seconds)
        finally:
            self.search_ms += (time.perf_counter() - started) * 1000

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        self.observe_calls += 1
        started = time.perf_counter()
        try:
            return self.native.observe(candidate, plan=plan, max_bytes=max_bytes, timeout_seconds=timeout_seconds)
        finally:
            self.observe_ms += (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one explicit content-free native v2501.9 research session.")
    parser.add_argument("--confirm-native", action="store_true")
    args = parser.parse_args()
    if not args.confirm_native:
        print(json.dumps({"suite": "v2501.9-native-research-session", "ok": False, "blocked": True, "reason": "explicit_native_confirmation_required", "network_contacted": False}, sort_keys=True))
        return 2

    runtime_root = Path(tempfile.mkdtemp(prefix="eidolon-v2501-9-native-"))
    adapter = MeasuredAdapter()
    store = BoundedResearchSessionStore(runtime_root)
    started = time.perf_counter()
    try:
        created = store.create_session(
            "native-create",
            objective="Compare current public Python packaging guidance from official sources",
            budget={"max_queries": 1, "max_candidates": 3, "max_observed_pages": 2, "max_total_bytes": 400_000, "max_elapsed_seconds": 60},
        )
        session = created["result"]
        authorized = store.authorize_session(
            "native-authorize",
            session_id=session["session_id"],
            session_digest=session["session_digest"],
            public_query_confirmed=True,
        )
        executed = store.execute_session(
            "native-execute",
            session_id=session["session_id"],
            authorization_digest=authorized["result"]["authorization_digest"],
            adapter=adapter,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        report = dict((executed.get("result") or {}).get("report") or {})
        serialized = json.dumps(report, sort_keys=True)
        payload = {
            "suite": "v2501.9-native-research-session",
            "ok": bool(executed.get("ok")),
            "blocked": False,
            "network_contacted": True,
            "status": executed.get("status"),
            "total_ms": elapsed_ms,
            "search_ms": round(adapter.search_ms, 3),
            "observe_ms": round(adapter.observe_ms, 3),
            "search_request_count": adapter.search_calls,
            "observation_request_count": adapter.observe_calls,
            "committed_session_count": 1 if executed.get("ok") else 0,
            "citation_count": int(report.get("citation_count") or 0),
            "contradiction_count": len(report.get("contradicted_claim_codes") or []),
            "report_digest": str(report.get("report_digest") or ""),
            "query_evidence_digest": digest([digest(query) for query in adapter.queries]),
            "raw_query_absent_from_report": all(query not in serialized for query in adapter.queries),
            "raw_content_included": False,
            "credentials_sent": False,
            "cookies_sent": False,
            "write_method_used": False,
            "authority_expanded": False,
        }
        print(json.dumps(payload, sort_keys=True))
        return 0 if payload["ok"] and payload["raw_query_absent_from_report"] else 1
    except PublicWebResearchError as error:
        print(json.dumps({"suite": "v2501.9-native-research-session", "ok": False, "blocked": False, "network_contacted": True, "failure_code": error.code, "raw_content_included": False, "credentials_sent": False, "cookies_sent": False, "write_method_used": False}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
