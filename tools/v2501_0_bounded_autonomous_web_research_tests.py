from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2501-data-")

from conscious_agent.bounded_autonomous_web_research import (  # noqa: E402
    BoundedResearchSessionStore,
    HARD_LIMITS,
    validate_read_only_adapter,
)
from conscious_agent.research_web_intelligence_v2100 import (  # noqa: E402
    NATIVE_RECEIPT_CONTRACT_VERSION,
)


checks: list[str] = []


def require(value: object, name: str) -> None:
    checks.append(name)
    assert value, name


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def native_receipt(kind: str, **values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "contract_version": NATIVE_RECEIPT_CONTRACT_VERSION,
        "receipt_kind": kind,
        "authoritative": True,
        "terminal": True,
        "operation_digest": "8" * 64,
        "terminal_result_digest": "9" * 64,
        **values,
    }
    row["receipt_digest"] = digest(row)
    return row


class FixtureAdapter:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.search_calls = 0
        self.observe_calls = 0

    def describe(self) -> dict[str, object]:
        return {
            "adapter_code": "deterministic-fixture",
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

    def search(self, query: str, *, limit: int, timeout_seconds: float):
        self.search_calls += 1
        if self.fail:
            raise RuntimeError("fixture transport failure")
        return [
            {
                "url": "https://docs.example.com/report?private=query",
                "source_kind": "primary_official",
                "fetched_at": "2026-08-26T00:00:00+00:00",
            },
            {
                "url": "https://analysis.example.org/report",
                "source_kind": "reputable_secondary",
                "fetched_at": "2026-08-26T00:00:00+00:00",
            },
            {"url": "http://127.0.0.1/private", "source_kind": "unknown"},
        ][:limit]

    def observe(self, source_candidate, *, plan, max_bytes: int, timeout_seconds: float):
        self.observe_calls += 1
        stance = "supports" if self.observe_calls == 1 else "refutes"
        return native_receipt(
            "source_observation",
            plan_digest=plan["plan_digest"],
            source_observed=True,
            source_candidate_digest=source_candidate["source_candidate_digest"],
            claim_code="opportunity-supported",
            stance=stance,
            evidence_digest=hashlib.sha256(f"evidence-{self.observe_calls}".encode()).hexdigest(),
            citation_id=f"citation-{self.observe_calls}",
            source_kind=source_candidate["source_kind"],
            quality_score=source_candidate["quality_score"],
            freshness_known=True,
            fresh_enough=True,
            observed_bytes=min(512, max_bytes),
        )


class UnsafeAdapter(FixtureAdapter):
    def describe(self) -> dict[str, object]:
        row = super().describe()
        row.update({"allowed_methods": ["GET", "POST"], "cookies_allowed": True})
        return row


root = Path(os.environ["EIDOLON_DATA_DIR"])
store = BoundedResearchSessionStore(root)
adapter = FixtureAdapter()

require(validate_read_only_adapter(adapter)["ok"], "strict_read_only_adapter_accepted")
unsafe = validate_read_only_adapter(UnsafeAdapter())
require(not unsafe["ok"] and not unsafe["checks"]["methods_bounded"], "write_capable_adapter_rejected")
require(not unsafe["checks"]["cookies_denied"], "credential_state_adapter_rejected")

missing = store.create_session("create-missing", objective="")
require(missing["status"] == "research_objective_required", "objective_required")
secret = store.create_session("create-secret", objective="Compare vendors using api_key=supersecret")
require(secret["status"] == "research_objective_contains_sensitive_material", "sensitive_objective_rejected")

objective = "Find promising zero-budget SaaS opportunities and compare supporting evidence"
created = store.create_session(
    "create-1",
    objective=objective,
    budget={key: value * 100 for key, value in HARD_LIMITS.items()},
)
require(created["ok"] and created["status"] == "research_session_created", "bounded_session_created")
session = created["result"]
require(session["budget"] == HARD_LIMITS, "hard_budgets_clamp_operator_request")
require(objective not in json.dumps(created), "private_objective_absent_from_public_result")
require(all(value is False for key, value in created.items() if key.endswith("_authorized") or key.endswith("_allowed")), "authority_remains_denied")

duplicate = store.create_session("create-2", objective=objective, budget={key: value * 100 for key, value in HARD_LIMITS.items()})
require(duplicate["status"] == "duplicate_research_session_reused", "semantic_duplicate_reused")
replay = store.create_session("create-1", objective="a different objective")
require(replay["idempotent"] and replay["result"]["session_id"] == session["session_id"], "create_event_exactly_once")

wrong = store.authorize_session(
    "authorize-wrong",
    session_id=session["session_id"],
    session_digest="0" * 64,
    public_query_confirmed=True,
)
require(wrong["status"] == "exact_research_session_required", "exact_session_digest_required")
unconfirmed = store.authorize_session(
    "authorize-unconfirmed",
    session_id=session["session_id"],
    session_digest=session["session_digest"],
    public_query_confirmed=False,
)
require(unconfirmed["status"] == "public_query_confirmation_required", "public_query_confirmation_required")
authorized = store.authorize_session(
    "authorize-1",
    session_id=session["session_id"],
    session_digest=session["session_digest"],
    public_query_confirmed=True,
)
require(authorized["ok"] and authorized["result"]["authorization_digest"], "single_session_authorization_created")

blocked = store.execute_session(
    "execute-blocked",
    session_id=session["session_id"],
    authorization_digest="0" * 64,
    adapter=adapter,
)
require(blocked["status"] == "exact_authorized_research_session_required", "execution_requires_exact_authorization")
require(adapter.search_calls == 0 and adapter.observe_calls == 0, "blocked_execution_does_not_contact_adapter")

executed = store.execute_session(
    "execute-1",
    session_id=session["session_id"],
    authorization_digest=authorized["result"]["authorization_digest"],
    adapter=adapter,
)
require(executed["ok"] and executed["status"] == "bounded_research_completed", "bounded_multi_step_research_completes")
report = executed["result"]["report"]
require(adapter.search_calls >= 1 and adapter.observe_calls == 2, "one_authorization_covers_multiple_read_only_pages")
require(report["contradicted_claim_codes"] == ["opportunity-supported"], "contradictory_evidence_preserved")
require(report["claim_assessments"][0]["support_state"] == "conflicted", "conflicted_conclusion_remains_uncertain")
require(all("?" not in row["public_url"] for row in report["citations"]), "citation_urls_remove_query_fragments")
require(report["raw_page_content_persisted"] is False and report["raw_query_text_exposed"] is False, "report_is_content_minimized")

calls = (adapter.search_calls, adapter.observe_calls)
execute_replay = store.execute_session(
    "execute-1",
    session_id=session["session_id"],
    authorization_digest=authorized["result"]["authorization_digest"],
    adapter=adapter,
)
require(execute_replay["idempotent"] and calls == (adapter.search_calls, adapter.observe_calls), "execution_event_exactly_once")

restarted = BoundedResearchSessionStore(root).inspection_summary()
require(restarted["session_count"] == 1 and restarted["sessions"][0]["state"] == "completed", "state_survives_restart")
persisted = store.path.read_text(encoding="utf-8")
require(objective in persisted, "private_objective_retained_only_in_external_runtime")
require("private=query" not in persisted and "evidence-1" not in persisted, "raw_query_and_page_content_not_persisted")

failed_created = store.create_session("create-failure", objective="Research a separate transport failure scenario")
failed_session = failed_created["result"]
failed_auth = store.authorize_session(
    "authorize-failure",
    session_id=failed_session["session_id"],
    session_digest=failed_session["session_digest"],
    public_query_confirmed=True,
)
failed = store.execute_session(
    "execute-failure",
    session_id=failed_session["session_id"],
    authorization_digest=failed_auth["result"]["authorization_digest"],
    adapter=FixtureAdapter(fail=True),
)
require(not failed["ok"] and failed["status"] == "bounded_research_failed_safely", "adapter_failure_is_terminal_and_safe")

cancel_created = store.create_session("create-cancel", objective="Research a distinct cancellation scenario")
cancel_session = cancel_created["result"]
cancelled = store.cancel_session(
    "cancel-1",
    session_id=cancel_session["session_id"],
    session_digest=cancel_session["session_digest"],
)
require(cancelled["ok"] and cancelled["status"] == "research_session_cancelled", "operator_can_cancel_before_execution")

print(json.dumps({
    "suite": "v2501.0-bounded-autonomous-web-research",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
}, sort_keys=True))
