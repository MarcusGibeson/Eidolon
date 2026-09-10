from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from conscious_agent.bounded_autonomous_web_research import BoundedResearchSessionStore
from conscious_agent.research_web_intelligence_v2100 import NATIVE_RECEIPT_CONTRACT_VERSION


def digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SlowAdapter:
    def __init__(self, marker_root: Path):
        self.marker_root = marker_root
        self.search_calls = 0
        self.observe_calls = 0
        self._lock = threading.Lock()

    def describe(self):
        return {
            "adapter_code": "v2501.9-cross-process-fixture",
            "read_only": True,
            "allowed_methods": ["GET", "HEAD"],
            "search_supported": True,
            "private_network_allowed": False,
            "redirect_revalidation_required": True,
            "credentials_allowed": False,
            "cookies_allowed": False,
            "uploads_allowed": False,
            "side_effects_allowed": False,
            "max_bytes_enforced": True,
            "timeout_enforced": True,
        }

    def search(self, query, *, limit, timeout_seconds):
        with self._lock:
            self.search_calls += 1
            call_number = self.search_calls
        (self.marker_root / f"search-{call_number}").write_text(digest(query), encoding="utf-8")
        time.sleep(0.75)
        return [{"url": "https://official.example/research", "source_kind": "primary_official", "fetched_at": "2026-08-26T00:00:00+00:00"}]

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        self.observe_calls += 1
        row = {
            "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
            "receipt_kind": "source_observation",
            "authoritative": True,
            "terminal": True,
            "operation_digest": "8" * 64,
            "terminal_result_digest": "9" * 64,
            "source_observed": True,
            "plan_digest": plan["plan_digest"],
            "source_candidate_digest": candidate["source_candidate_digest"],
            "claim_code": candidate.get("subquestion_id", "rq1"),
            "stance": "supports",
            "evidence_digest": "7" * 64,
            "citation_id": "c1",
            "source_kind": candidate["source_kind"],
            "quality_score": candidate["quality_score"],
            "freshness_known": True,
            "fresh_enough": True,
            "relevance_score": 0.9,
            "observed_bytes": min(128, max_bytes),
        }
        row["receipt_digest"] = digest(row)
        return row


class PartialFailureAdapter(SlowAdapter):
    def search(self, query, *, limit, timeout_seconds):
        self.search_calls += 1
        return [
            {"url": "https://first.example/research", "source_kind": "primary_official", "fetched_at": "2026-08-26T00:00:00+00:00"},
            {"url": "https://second.example/research", "source_kind": "reputable_secondary", "fetched_at": "2026-08-26T00:00:00+00:00"},
        ][:limit]

    def observe(self, candidate, *, plan, max_bytes, timeout_seconds):
        self.observe_calls += 1
        if self.observe_calls == 1:
            raise RuntimeError("fixture_source_unavailable")
        return super().observe(candidate, plan=plan, max_bytes=max_bytes, timeout_seconds=timeout_seconds)


def main() -> int:
    checks: list[str] = []

    def require(value: object, name: str) -> None:
        checks.append(name)
        assert value, name

    runtime_root = Path(tempfile.mkdtemp(prefix="eidolon-v2501-9-runtime-"))
    marker_root = Path(tempfile.mkdtemp(prefix="eidolon-v2501-9-markers-"))
    store = BoundedResearchSessionStore(runtime_root)
    created = store.create_session("create", objective="Compare current public Python packaging guidance")
    session = created["result"]
    authorized = store.authorize_session(
        "authorize",
        session_id=session["session_id"],
        session_digest=session["session_digest"],
        public_query_confirmed=True,
    )
    auth_digest = authorized["result"]["authorization_digest"]
    adapter = SlowAdapter(marker_root)
    results: list[dict[str, object]] = []

    def execute(event_id: str) -> None:
        results.append(BoundedResearchSessionStore(runtime_root).execute_session(
            event_id,
            session_id=session["session_id"],
            authorization_digest=auth_digest,
            adapter=adapter,
        ))

    first = threading.Thread(target=execute, args=("execute-a",))
    second = threading.Thread(target=execute, args=("execute-b",))
    first.start()
    time.sleep(0.15)
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)
    require(not first.is_alive() and not second.is_alive() and len(results) == 2, "concurrent_workers_exit_cleanly")
    statuses = {str(result.get("status")) for result in results}
    require(statuses == {"bounded_research_completed", "bounded_research_execution_already_running"}, "live_owner_and_observer_are_distinguished")
    require(adapter.search_calls == 1 and len(list(marker_root.glob("search-*"))) == 1, "concurrent_provider_request_is_exactly_once")
    summary = BoundedResearchSessionStore(runtime_root).inspection_summary()
    require(summary["sessions"][0]["state"] == "completed", "winning_execution_commits_terminal_state")
    require(summary["query_text_exposed"] is False and summary["raw_page_content_exposed"] is False, "inspection_remains_content_free")

    degraded_root = Path(tempfile.mkdtemp(prefix="eidolon-v2501-9-degraded-"))
    degraded_store = BoundedResearchSessionStore(degraded_root)
    degraded_created = degraded_store.create_session("create", objective="Research current public packaging evidence", budget={"max_queries": 1, "max_candidates": 2, "max_observed_pages": 2})
    degraded_session = degraded_created["result"]
    degraded_auth = degraded_store.authorize_session("authorize", session_id=degraded_session["session_id"], session_digest=degraded_session["session_digest"], public_query_confirmed=True)
    degraded_adapter = PartialFailureAdapter(marker_root)
    degraded = degraded_store.execute_session("execute", session_id=degraded_session["session_id"], authorization_digest=degraded_auth["result"]["authorization_digest"], adapter=degraded_adapter)
    require(degraded["ok"] and degraded["result"]["session"]["source_failure_count"] == 1, "one_unavailable_source_does_not_abort_session")
    require(degraded_adapter.observe_calls >= 2 and degraded["result"]["report"]["source_failure_count"] == 1, "later_source_evidence_is_still_admitted")
    print(json.dumps({"suite": "v2501.9-desktop-research-acceptance", "ok": True, "passed": len(checks), "failed": 0, "checks": checks, "native_network_contacted": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
