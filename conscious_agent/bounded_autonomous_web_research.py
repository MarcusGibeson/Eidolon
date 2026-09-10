from __future__ import annotations
from research_failure_receipts import sanitize_failures

"""Bounded, session-authorized, read-only autonomous web research.

The v2501.0 lifecycle remains the authority boundary. v2501.2-v2501.8 extend
that same coordinator with content-minimized question decomposition, source
strategy, privacy-safe public query planning, evidence extraction, cross-source
comparison, cited synthesis, and operator-visible progress. Network transport
is still injected through the v2501.1 read-only adapter contract.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Iterable, Mapping, Protocol
from urllib.parse import urlsplit

try:
    from bounded_research_reasoning import assemble_cited_conclusion, build_source_strategy, compare_cross_source_evidence, decompose_research_objective, extract_claim_evidence, plan_public_search_queries, plan_adaptive_follow_up, plan_candidate_evidence_follow_up, select_diverse_sources, validate_research_synthesis
    from bounded_research_history import MAX_HISTORY_RECORDS, build_history_record, compare_reports, render_markdown_export, sanitize_report, validate_history_record
    from research_web_intelligence_v2100 import assess_source_candidate, plan_research
    from research_source_independence import source_evidence_role
except ImportError:
    from bounded_research_reasoning import (
        assemble_cited_conclusion,
        build_source_strategy,
        compare_cross_source_evidence,
        decompose_research_objective,
        extract_claim_evidence,
        plan_public_search_queries,
        plan_adaptive_follow_up,
        plan_candidate_evidence_follow_up,
        select_diverse_sources,
        validate_research_synthesis,
    )
    from bounded_research_history import (
        MAX_HISTORY_RECORDS,
        build_history_record,
        compare_reports,
        render_markdown_export,
        sanitize_report,
        validate_history_record,
    )
    from research_web_intelligence_v2100 import assess_source_candidate, plan_research
    from research_source_independence import source_evidence_role


CONTRACT_VERSION = "v2502.2"
SCHEMA_VERSION = "2"
MAX_CANDIDATE_FOLLOW_UP_FAILURES_PER_CELL = 2
MAX_CANDIDATE_FOLLOW_UP_SEARCH_ATTEMPTS_PER_CELL = 2
CANDIDATE_FOLLOW_UP_SOURCES_PER_CELL = 2
MAX_OBSERVATION_REPLACEMENTS = 3
MAX_REPLACEMENTS_PER_FAILURE = 2
DEFAULT_BUDGET = {
    "max_queries": 8,
    "max_candidates": 16,
    "max_observed_pages": 10,
    "max_total_bytes": 2 * 1024 * 1024,
    "max_elapsed_seconds": 300,
    "max_source_failures": 4,
}
HARD_LIMITS = {
    "max_queries": 20,
    "max_candidates": 32,
    "max_observed_pages": 32,
    "max_total_bytes": 10 * 1024 * 1024,
    "max_elapsed_seconds": 900,
    "max_source_failures": 12,
}

_DENIED = {
    "posting_allowed": False,
    "messaging_allowed": False,
    "account_creation_allowed": False,
    "purchase_allowed": False,
    "upload_allowed": False,
    "credential_use_allowed": False,
    "private_network_allowed": False,
    "destructive_operation_allowed": False,
    "source_mutation_allowed": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "model_management_authorized": False,
    "standing_research_authority_granted": False,
    "release_authority_granted": False,
    "authority_expanded": False,
}
_SENSITIVE = re.compile(
    r"(?:\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|bearer)\b\s*[:=]|\bsk-[A-Za-z0-9_-]{12,})",
    re.I,
)
_LOCK = threading.RLock()
_STAGE_PERCENT = {
    "awaiting_session_authorization": 5,
    "authorized": 10,
    "query_planning": 18,
    "searching": 32,
    "observing": 52,
    "extracting_evidence": 68,
    "comparing_evidence": 80,
    "candidate_evidence_follow_up": 84,
    "assembling_report": 90,
    "completed": 100,
    "cancelled": 100,
    "failed": 100,
}


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clean(value: object, limit: int = 8000) -> str:
    return " ".join(str(value or "").split()).strip()[:limit]


def _hex64(value: object) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid_is_alive(value: object) -> bool:
    try:
        pid = int(value)
    except (TypeError, ValueError, OverflowError):
        return False
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _runtime_root(runtime_root: str | Path | None = None) -> Path:
    configured = runtime_root or os.environ.get("EIDOLON_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".eidolon" / "data").resolve()


def _bounded_budget(values: Mapping[str, Any] | None = None) -> dict[str, int]:
    supplied = dict(values or {})
    result: dict[str, int] = {}
    for key, default in DEFAULT_BUDGET.items():
        try:
            value = int(supplied.get(key, default))
        except (TypeError, ValueError, OverflowError):
            value = default
        result[key] = max(1, min(value, HARD_LIMITS[key]))
    return result


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "sessions": [],
        "history_records": [],
        "reports": {},
        "processed_events": {},
        "updated_at": "",
    }


def _inferred_source_kind(url: str, supplied: str) -> str:
    """Classify a candidate from structural URL signals.

    A handful of enumerated hostnames left almost every source unclassified, and
    an unclassified source can support no evidence dimension - so the gap read as
    poor quality rather than as missing metadata.
    """
    kind = _clean(supplied, 60).lower()
    if kind and kind != "unknown":
        return kind
    from research_source_classification import classify_source_kind
    parsed = urlsplit(str(url or ""))
    path = (parsed.path or "").lower()
    if "/dataset" in path or "/data/" in path:
        return "primary_data"
    if (parsed.hostname or "").lower() in {"g2.com", "www.g2.com", "capterra.com", "www.capterra.com"}:
        return "specialist_secondary"
    return classify_source_kind(url, "unknown")


def _evaluate_evidence_policy(*, payload, citations, assessment_summary, currency_requirement, objective="") -> dict[str, Any]:
    """Measure the shared evidence policy without letting it refuse anything."""
    try:
        from research_evidence_policy import evaluate_policy, policy_for_objective
        findings = (payload or {}).get("findings") if isinstance(payload, Mapping) else None
        finding = findings[0] if isinstance(findings, list) and findings and isinstance(findings[0], Mapping) else {}
        assessments = {
            str(row.get("citation_id") or ""): row
            for row in ((assessment_summary or {}).get("assessments") or [])
            if isinstance(row, Mapping)
        }
        return evaluate_policy(
            policy_for_objective(currency_requirement),
            finding=finding,
            citations=[row for row in (citations or []) if isinstance(row, Mapping)],
            assessments_by_citation=assessments,
            objective=str(objective or ""),
        )
    except Exception:
        # An observation-only measurement must never affect the run it observes.
        return {}


def _replacement_search_query(candidate: Mapping[str, Any], dimension: str) -> str:
    """Build a public replacement query after a source could not be read.

    Terms are reused from the sanitized query that found the failed candidate, so
    no private objective text reaches a new public request. The dimension bias
    aims the retry at evidence that can actually establish the claim rather than
    at more of whatever the first query surfaced.
    """
    terms = [_clean(term, 40) for term in list(candidate.get("_evidence_terms") or [])[:12]]
    bias = {
        "demand": "survey study report respondents",
        "competition": "comparison independent review",
        "free_tier_feasibility": "official documentation pricing limits",
    }.get(str(dimension or ""), "study report")
    return _clean(" ".join([term for term in terms if term] + bias.split()), 320)


def _candidate_follow_up_retry_query(query_row: Mapping[str, Any]) -> str:
    """Build a shorter public retry query without reusing private objective text."""
    candidate_name = _clean(query_row.get("candidate_name"), 140)
    dimension = _clean(query_row.get("evidence_dimension"), 60)
    dimension_labels = {
        "demand": "customer demand problem evidence",
        "competition": "competitors alternatives pricing",
        "implementation_dependencies": "implementation requirements dependencies API",
        "free_tier_feasibility": "free tier pricing limits hosting",
    }
    label = dimension_labels.get(dimension, "independent evidence")
    return _clean(f'"{candidate_name}" {label}', 320)


def _select_candidate_follow_up_sources(
    rows: Iterable[Mapping[str, Any]],
    *,
    evidence_dimension: str,
    existing_hosts: Iterable[str] = (),
    limit: int = CANDIDATE_FOLLOW_UP_SOURCES_PER_CELL,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Prefer distinct sources whose public role can support this matrix cell."""
    dimension = _clean(evidence_dimension, 60)
    prior_hosts = {str(host or "").casefold() for host in existing_hosts if str(host or "").strip()}
    candidates: list[tuple[dict[str, Any], bool]] = []
    for raw in rows:
        row = dict(raw or {})
        role = source_evidence_role({
            "public_url": row.get("public_url"),
            "canonical_url": row.get("canonical_url"),
            "source_kind": row.get("source_kind"),
        })
        supports = bool(role.get("valid_public_url")) and dimension in set(role.get("supportable_dimensions") or [])
        row["_candidate_role_supports_dimension"] = supports
        row["_candidate_evidence_role"] = _clean(role.get("evidence_role"), 60) or "unknown"
        candidates.append((row, supports))
    candidates.sort(key=lambda item: (
        0 if item[1] else 1,
        str(item[0].get("host") or "").casefold() in prior_hosts,
        -float(item[0].get("quality_score") or 0.0),
        str(item[0].get("host") or "").casefold(),
        str(item[0].get("public_url") or ""),
    ))

    selected: list[dict[str, Any]] = []
    selected_hosts: set[str] = set()
    for require_new_host in (True, False):
        for row, _supports in candidates:
            if row in selected:
                continue
            host = str(row.get("host") or "").casefold()
            if require_new_host and host and host in selected_hosts:
                continue
            selected.append(row)
            if host:
                selected_hosts.add(host)
            if len(selected) >= max(1, int(limit)):
                break
        if len(selected) >= max(1, int(limit)):
            break
    alternatives = [row for row, _supports in candidates if row not in selected]
    return selected, alternatives


class ReadOnlyResearchAdapter(Protocol):
    def describe(self) -> Mapping[str, Any]: ...

    def search(self, query: str, *, limit: int, timeout_seconds: float) -> Iterable[Mapping[str, Any]]: ...

    def observe(
        self,
        source_candidate: Mapping[str, Any],
        *,
        plan: Mapping[str, Any],
        max_bytes: int,
        timeout_seconds: float,
    ) -> Mapping[str, Any]: ...


def validate_read_only_adapter(adapter: ReadOnlyResearchAdapter) -> dict[str, Any]:
    try:
        row = dict(adapter.describe() or {})
    except Exception:
        row = {}
    methods = sorted({str(item).upper() for item in row.get("allowed_methods", [])})
    checks = {
        "read_only": row.get("read_only") is True,
        "methods_bounded": bool(methods) and set(methods) <= {"GET", "HEAD"},
        "search_supported": row.get("search_supported") is True,
        "public_network_only": row.get("private_network_allowed") is False,
        "redirects_revalidated": row.get("redirect_revalidation_required") is True,
        "credentials_denied": row.get("credentials_allowed") is False,
        "cookies_denied": row.get("cookies_allowed") is False,
        "uploads_denied": row.get("uploads_allowed") is False,
        "side_effects_denied": row.get("side_effects_allowed") is False,
        "byte_limit_enforced": row.get("max_bytes_enforced") is True,
        "timeout_enforced": row.get("timeout_enforced") is True,
    }
    ok = all(checks.values())
    result = {
        "ok": ok,
        "status": "read_only_research_adapter_accepted" if ok else "read_only_research_adapter_rejected",
        "adapter_code": _clean(row.get("adapter_code"), 80),
        "allowed_methods": methods,
        "checks": checks,
        "adapter_contract_digest": _digest({"adapter_code": row.get("adapter_code"), "allowed_methods": methods, "checks": checks}),
        **_DENIED,
    }
    return result


@dataclass(frozen=True)
class ResearchSessionRef:
    session_id: str
    session_digest: str


class BoundedResearchSessionStore:
    def __init__(self, runtime_root: str | Path | None = None, *, clock=time.monotonic):
        self.runtime_root = _runtime_root(runtime_root)
        self.path = self.runtime_root / "research" / "bounded_web_research_sessions.json"
        self.lock_path = self.path.with_suffix(".lock")
        self.clock = clock

    @contextmanager
    def _state_lock(self):
        """Serialize durable session transitions across threads and processes."""
        with _LOCK:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            with self.lock_path.open("a+b") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    handle.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return _empty_state()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _empty_state()
        if not isinstance(value, dict):
            return _empty_state()
        value.setdefault("schema_version", SCHEMA_VERSION)
        value.setdefault("contract_version", CONTRACT_VERSION)
        value.setdefault("revision", 0)
        value.setdefault("sessions", [])
        value.setdefault("history_records", [])
        value.setdefault("reports", {})
        value.setdefault("processed_events", {})
        value.setdefault("updated_at", "")
        return value

    def _save(self, state: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2, sort_keys=True) + "\n"
        temp = self.path.with_suffix(f".tmp-{os.getpid()}-{threading.get_ident()}")
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, self.path)

    @staticmethod
    def _public_session(row: Mapping[str, Any]) -> dict[str, Any]:
        keys = (
            "session_id", "session_digest", "plan_digest", "objective_digest", "state",
            "budget", "authorized_at", "started_at", "completed_at", "query_count",
            "candidate_count", "observed_page_count", "observed_bytes", "evidence_count",
            "claim_count", "contradiction_count", "report_digest", "stop_reason",
            "progress_stage", "progress_percent", "decomposition_digest", "source_strategy_digest",
            "subquestion_count", "source_strategy_count", "failure_code", "source_failure_count",
            "semantic_attempt",
        )
        budget = dict(row.get("budget") or {})
        remaining = {
            "queries": max(0, int(budget.get("max_queries") or 0) - int(row.get("query_count") or 0)),
            "candidates": max(0, int(budget.get("max_candidates") or 0) - int(row.get("candidate_count") or 0)),
            "observed_pages": max(0, int(budget.get("max_observed_pages") or 0) - int(row.get("observed_page_count") or 0)),
            "bytes": max(0, int(budget.get("max_total_bytes") or 0) - int(row.get("observed_bytes") or 0)),
        }
        return {key: row.get(key) for key in keys} | {
            "budget_remaining": remaining,
            "objective_text_exposed": False,
            "query_text_exposed": False,
            "private_subquestions_exposed": False,
            "raw_page_content_exposed": False,
            **_DENIED,
        }

    @staticmethod
    def _report_storage_entry(session_id: str, report: Mapping[str, Any] | None) -> dict[str, Any]:
        sanitized = sanitize_report(report)
        report_digest = _hex64(sanitized.get("report_digest"))
        if not report_digest:
            return {}
        payload = {
            "session_id": _clean(session_id, 120),
            "report_digest": report_digest,
            "report": sanitized,
        }
        return payload | {"report_storage_digest": _digest(payload), "stored_at": _now()}

    @staticmethod
    def _validate_report_storage(entry: Mapping[str, Any] | None) -> tuple[bool, dict[str, Any]]:
        row = dict(entry or {})
        supplied = _hex64(row.get("report_storage_digest"))
        payload = {
            "session_id": _clean(row.get("session_id"), 120),
            "report_digest": _hex64(row.get("report_digest")),
            "report": dict(row.get("report") or {}) if isinstance(row.get("report"), Mapping) else {},
        }
        valid = bool(supplied) and supplied == _digest(payload)
        if valid and payload["report_digest"] != _hex64(payload["report"].get("report_digest")):
            valid = False
        return valid, payload

    def _persist_terminal_history(self, state: dict[str, Any], row: dict[str, Any], report: Mapping[str, Any] | None = None) -> str:
        """Persist one terminal content-free catalog row; never repair a conflicting row silently."""
        session_id = _clean(row.get("session_id"), 120)
        records = list(state.get("history_records") or [])
        existing = next((item for item in records if item.get("session_id") == session_id), None)
        if existing is not None:
            validation = validate_history_record(existing, session=row)
            if validation.get("ok"):
                row["history_persistence_status"] = "history_record_already_persisted"
                return "history_record_already_persisted"
            row["history_persistence_status"] = "history_record_conflict_not_repaired"
            return "history_record_conflict_not_repaired"

        report_entry = self._report_storage_entry(session_id, report)
        reports = dict(state.get("reports") or {})
        if report_entry:
            prior = reports.get(session_id)
            if prior:
                valid, payload = self._validate_report_storage(prior)
                if not valid or payload.get("report_digest") != report_entry.get("report_digest"):
                    row["history_persistence_status"] = "report_storage_conflict_not_repaired"
                    return "report_storage_conflict_not_repaired"
            else:
                reports[session_id] = report_entry
                state["reports"] = reports
        record = build_history_record(row, report_entry.get("report") if report_entry else report)
        records.append(record)
        state["history_records"] = records[-MAX_HISTORY_RECORDS:]
        row["history_persistence_status"] = "history_record_persisted"
        return "history_record_persisted"

    def _event_replay(self, state: Mapping[str, Any], event_id: str) -> dict[str, Any] | None:
        row = dict((state.get("processed_events") or {}).get(event_id) or {})
        if not row:
            return None
        return {"ok": row.get("ok", True), "status": row.get("status"), "idempotent": True, "result": row.get("result"), **_DENIED}

    @staticmethod
    def _record_event(state: dict[str, Any], event_id: str, status: str, result: Mapping[str, Any], *, ok: bool = True) -> None:
        events = dict(state.get("processed_events") or {})
        events[event_id] = {"ok": bool(ok), "status": status, "result": dict(result), "recorded_at": _now()}
        state["processed_events"] = dict(list(events.items())[-512:])

    @staticmethod
    def _append_stage(row: dict[str, Any], stage: str) -> None:
        history = list(row.get("stage_history") or [])
        if not history or history[-1].get("stage") != stage:
            history.append({"stage": stage, "occurred_at": _now()})
        row["stage_history"] = history[-32:]
        row["progress_stage"] = stage
        row["progress_percent"] = _STAGE_PERCENT.get(stage, int(row.get("progress_percent") or 0))

    def _set_stage(self, session_id: str, stage: str, **counts: object) -> bool:
        with self._state_lock():
            state = self._load()
            row = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
            if not row or row.get("state") in {"cancelled", "failed"}:
                return False
            self._append_stage(row, stage)
            for key, value in counts.items():
                if key in {
                    "query_count", "candidate_count", "observed_page_count", "observed_bytes",
                    "evidence_count", "claim_count", "contradiction_count", "source_failure_count",
                }:
                    try:
                        row[key] = max(0, int(value))
                    except (TypeError, ValueError, OverflowError):
                        pass
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now()
            self._save(state)
            return True

    def _is_cancelled(self, session_id: str) -> bool:
        with self._state_lock():
            state = self._load()
            row = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
            return bool(row and row.get("state") == "cancelled")

    def create_session(
        self,
        event_id: str,
        *,
        objective: str,
        freshness: str = "",
        budget: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = _clean(event_id, 180)
        text = _clean(objective)
        if not event:
            return {"ok": False, "status": "research_event_id_required", **_DENIED}
        if not text:
            return {"ok": False, "status": "research_objective_required", **_DENIED}
        if _SENSITIVE.search(text):
            return {"ok": False, "status": "research_objective_contains_sensitive_material", **_DENIED}
        bounded = _bounded_budget(budget)
        # Decompose before planning: the objective's shape decides how long its
        # evidence stays valid, and the plan's source-age window follows from
        # that rather than from a fixed 30-day default.
        decomposition = decompose_research_objective(text, freshness=freshness, budget=bounded)
        if not decomposition.get("ok"):
            return dict(decomposition)
        freshness = _clean(decomposition.get("recommended_freshness_policy"), 24) or "current"
        plan = plan_research(text, freshness=freshness, private_context_present=True)
        if not plan.get("ok"):
            return dict(plan)
        source_strategy = build_source_strategy(decomposition)
        if not source_strategy.get("ok"):
            return dict(source_strategy)
        with self._state_lock():
            state = self._load()
            replay = self._event_replay(state, event)
            if replay:
                return replay
            objective_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            semantic = _digest({"objective_digest": objective_digest, "freshness": freshness, "budget": bounded})
            semantic_sessions = [
                row for row in state.get("sessions", [])
                if row.get("semantic_digest") == semantic
            ]
            duplicate = next((
                row for row in semantic_sessions
                if row.get("state") in {"awaiting_session_authorization", "authorized", "running"}
            ), None)
            if duplicate:
                result = self._public_session(duplicate)
                self._record_event(state, event, "duplicate_research_session_reused", result)
                self._save(state)
                return {"ok": True, "status": "duplicate_research_session_reused", "idempotent": True, "result": result, **_DENIED}
            semantic_attempt = len(semantic_sessions) + 1
            session_token = semantic if semantic_attempt == 1 else _digest({
                "semantic_digest": semantic,
                "semantic_attempt": semantic_attempt,
            })
            session_id = f"research-{session_token[:24]}"
            row: dict[str, Any] = {
                "session_id": session_id,
                "session_digest": "",
                "semantic_digest": semantic,
                "semantic_attempt": semantic_attempt,
                "objective": text,
                "objective_digest": objective_digest,
                "plan": plan,
                "plan_digest": plan["plan_digest"],
                "decomposition": decomposition,
                "decomposition_digest": decomposition["decomposition_digest"],
                "subquestion_count": decomposition["subquestion_count"],
                "source_strategy": source_strategy,
                "source_strategy_digest": source_strategy["source_strategy_digest"],
                "source_strategy_count": source_strategy["strategy_count"],
                "freshness": freshness,
                "budget": bounded,
                "state": "awaiting_session_authorization",
                "authorization_digest": "",
                "public_query_confirmed": False,
                "authorized_at": "",
                "started_at": "",
                "completed_at": "",
                "query_count": 0,
                "candidate_count": 0,
                "observed_page_count": 0,
                "observed_bytes": 0,
                "evidence_count": 0,
                "claim_count": 0,
                "contradiction_count": 0,
                "source_failure_count": 0,
                "report_digest": "",
                "failure_code": "",
                "stop_reason": "awaiting_operator_session_authorization",
                "created_at": _now(),
                "stage_history": [],
            }
            self._append_stage(row, "awaiting_session_authorization")
            row["session_digest"] = _digest({
                key: row[key]
                for key in ("session_id", "objective_digest", "plan_digest", "decomposition_digest", "source_strategy_digest", "budget", "semantic_attempt", "created_at")
            })
            state["sessions"] = (list(state.get("sessions", [])) + [row])[-128:]
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now()
            result = self._public_session(row)
            self._record_event(state, event, "research_session_created", result)
            self._save(state)
        return {"ok": True, "status": "research_session_created", "idempotent": False, "result": result, **_DENIED}

    def authorize_session(
        self,
        event_id: str,
        *,
        session_id: str,
        session_digest: str,
        public_query_confirmed: bool,
    ) -> dict[str, Any]:
        event = _clean(event_id, 180)
        with self._state_lock():
            state = self._load()
            replay = self._event_replay(state, event)
            if replay:
                return replay
            row = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
            if not row or row.get("session_digest") != _hex64(session_digest):
                return {"ok": False, "status": "exact_research_session_required", **_DENIED}
            if row.get("state") == "authorized":
                result = self._public_session(row) | {"authorization_digest": row.get("authorization_digest", "")}
                return {"ok": True, "status": "research_session_already_authorized", "idempotent": True, "result": result, **_DENIED}
            if row.get("state") != "awaiting_session_authorization":
                return {"ok": False, "status": "research_session_not_authorizable", **_DENIED}
            if public_query_confirmed is not True:
                return {"ok": False, "status": "public_query_confirmation_required", **_DENIED}
            row["public_query_confirmed"] = True
            row["authorized_at"] = _now()
            row["state"] = "authorized"
            row["stop_reason"] = "ready_for_bounded_read_only_execution"
            self._append_stage(row, "authorized")
            row["authorization_digest"] = _digest({
                "session_id": row["session_id"], "session_digest": row["session_digest"],
                "plan_digest": row["plan_digest"], "decomposition_digest": row.get("decomposition_digest"),
                "source_strategy_digest": row.get("source_strategy_digest"), "budget": row["budget"],
                "public_query_confirmed": True, "authorized_at": row["authorized_at"],
            })
            result = self._public_session(row) | {"authorization_digest": row["authorization_digest"]}
            self._record_event(state, event, "research_session_authorized", result)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now()
            self._save(state)
        return {"ok": True, "status": "research_session_authorized", "idempotent": False, "result": result, **_DENIED}

    def _fail_interrupted_without_replay(self, state: dict[str, Any], row: dict[str, Any], event: str) -> dict[str, Any]:
        row["state"] = "failed"
        row["completed_at"] = _now()
        row["failure_code"] = "interrupted_execution_not_replayed"
        row["stop_reason"] = "restart_detected_inflight_external_operation_fail_closed"
        row["execution_owner_pid"] = 0
        self._append_stage(row, "failed")
        public = self._public_session(row)
        result = {"session": public, "report": {}, "failure_code": row["failure_code"]}
        self._persist_terminal_history(state, row, {})
        public = self._public_session(row)
        result["session"] = public
        self._record_event(state, event, "bounded_research_interrupted_failed_closed", result, ok=False)
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = _now()
        self._save(state)
        return {"ok": False, "status": "bounded_research_interrupted_failed_closed", "idempotent": False, "result": result, **_DENIED}

    def execute_session(
        self,
        event_id: str,
        *,
        session_id: str,
        authorization_digest: str,
        adapter: ReadOnlyResearchAdapter,
        capture_training_evidence: bool = False,
    ) -> dict[str, Any]:
        try:
            from model_training.training_policy import resolve_training_evidence_capture_policy
        except ImportError:
            from model_training.training_policy import resolve_training_evidence_capture_policy
        training_policy = resolve_training_evidence_capture_policy()
        capture_training_evidence = bool(capture_training_evidence or training_policy.research_enabled)
        event = _clean(event_id, 180)
        adapter_contract = validate_read_only_adapter(adapter)
        if not adapter_contract.get("ok"):
            return {"ok": False, "status": "read_only_research_adapter_required", "adapter_contract": adapter_contract, **_DENIED}
        with self._state_lock():
            state = self._load()
            replay = self._event_replay(state, event)
            if replay:
                return replay
            row = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
            if row and row.get("state") == "running" and row.get("authorization_digest") == _hex64(authorization_digest):
                if _pid_is_alive(row.get("execution_owner_pid")):
                    public = self._public_session(row)
                    return {
                        "ok": True,
                        "status": "bounded_research_execution_already_running",
                        "idempotent": True,
                        "result": {"session": public, "report": {}, "failure_code": ""},
                        **_DENIED,
                    }
                return self._fail_interrupted_without_replay(state, row, event)
            if not row or row.get("state") != "authorized" or row.get("authorization_digest") != _hex64(authorization_digest):
                return {"ok": False, "status": "exact_authorized_research_session_required", **_DENIED}
            row["state"] = "running"
            row["started_at"] = row.get("started_at") or _now()
            row["stop_reason"] = "bounded_execution_running"
            row["failure_code"] = ""
            row["execution_owner_pid"] = os.getpid()
            self._append_stage(row, "query_planning")
            self._save(state)
            private_row = dict(row)

        started = self.clock()
        budget = dict(private_row["budget"])
        objective = str(private_row["objective"])
        plan = dict(private_row["plan"])
        decomposition = dict(private_row.get("decomposition") or {})
        source_strategy = dict(private_row.get("source_strategy") or {})
        candidates: dict[str, dict[str, Any]] = {}
        receipts: list[Mapping[str, Any]] = []
        citation_context: dict[str, dict[str, Any]] = {}
        query_count = 0
        observed_bytes = 0
        observed_pages = 0
        source_failure_count = 0
        model_assessment_denial_reason = ""
        evidence_policy_evaluation: dict[str, Any] = {}
        # Initialized here, not at the observation loop: the failure report reads it,
        # and a run that dies before collection must not raise a second error while
        # trying to describe the first.
        skipped_unreadable_host_count = 0
        source_failure_code_digests: list[str] = []
        source_failure_receipts: list[dict[str, Any]] = []
        extraction: dict[str, Any] = {"evidence_count": 0, "evidence": [], "contradicted_claim_codes": []}
        comparison: dict[str, Any] = {"claims": [], "conflicted_claim_codes": []}
        conclusion: dict[str, Any] = {}
        validated_synthesis: dict[str, Any] = {}
        synthesis_result: dict[str, Any] = {"ok": False, "status": "research_synthesis_not_available", "provider_contacted": False, "provider_request_count": 0}
        discovery_synthesis_result: dict[str, Any] = {"ok": False, "status": "candidate_discovery_not_available", "provider_contacted": False, "provider_request_count": 0}
        validated_candidate_discovery: dict[str, Any] = {}
        synthesis_provider_request_count = 0
        synthesis_provider_contacted = False
        evidence_directions = {"status": "evidence_directions_unavailable", "directions": []}
        candidate_follow_up: dict[str, Any] = {
            "ok": True,
            "status": "candidate_evidence_follow_up_not_available",
            "queries": [],
            "query_count": 0,
            "candidate_count": 0,
            "evidence_dimensions": [],
            "candidate_follow_up_plan_digest": "",
        }
        completed_candidate_follow_up_cells: set[str] = set()
        failure = ""
        cancelled = False
        try:
            requested_result_count = int(decomposition.get("requested_result_count") or 0)
            narrow_demand = decomposition.get("objective_shape") == "single_candidate_dimension" and any(
                row.get("evidence_dimension") == "demand" for row in decomposition.get("subquestions", [])
            )
            required_dimension = (
                str((decomposition.get("subquestions") or [{}])[0].get("evidence_dimension") or "")
                if decomposition.get("objective_shape") == "single_candidate_dimension" else ""
            )
            subquestion_count = int(decomposition.get("subquestion_count") or 0)
            candidate_follow_up_slots = min(
                12,
                requested_result_count * 4,
                max(0, budget["max_queries"] - subquestion_count),
                max(0, budget["max_observed_pages"] - max(1, subquestion_count)),
            ) if requested_result_count else 0
            reserved_follow_up_pages = min(
                budget["max_observed_pages"],
                candidate_follow_up_slots * CANDIDATE_FOLLOW_UP_SOURCES_PER_CELL,
            )
            reserved_follow_up_candidates = min(
                budget["max_candidates"],
                candidate_follow_up_slots * CANDIDATE_FOLLOW_UP_SOURCES_PER_CELL,
            )
            adaptive_slot_available = (
                budget["max_queries"] >= 3
                and subquestion_count < budget["max_queries"]
            )
            reserved_follow_up_slots = candidate_follow_up_slots or (1 if adaptive_slot_available else 0)
            initial_query_limit = max(1, budget["max_queries"] - reserved_follow_up_slots)
            query_plan = plan_public_search_queries(
                objective,
                decomposition,
                source_strategy,
                max_queries=initial_query_limit,
            )
            if not query_plan.get("ok"):
                raise RuntimeError("privacy_safe_search_query_unavailable")
            self._set_stage(session_id, "searching")
            adaptive_follow_up_possible = reserved_follow_up_slots > 0
            initial_candidate_cap = (
                max(1, budget["max_candidates"] - reserved_follow_up_candidates)
                if adaptive_follow_up_possible and budget["max_candidates"] > 1
                else budget["max_candidates"]
            )
            query_rows = list(query_plan.get("queries") or [])[:initial_query_limit]
            for query_index, query_row in enumerate(query_rows):
                if self._is_cancelled(session_id):
                    cancelled = True
                    break
                if self.clock() - started >= budget["max_elapsed_seconds"]:
                    break
                remaining = initial_candidate_cap - len(candidates)
                if remaining <= 0:
                    break
                remaining_queries = max(1, len(query_rows) - query_index)
                per_query_limit = max(1, (remaining + remaining_queries - 1) // remaining_queries)
                if narrow_demand:
                    per_query_limit = min(3, per_query_limit)
                query_count += 1
                query = _clean(query_row.get("query"), 320)
                try:
                    found = adapter.search(query, limit=per_query_limit, timeout_seconds=max(0.001, min(30.0, budget["max_elapsed_seconds"] - (self.clock() - started))))
                except Exception as search_error:
                    source_failure_count += 1
                    source_code = _clean(getattr(search_error, "code", ""), 120) or type(search_error).__name__
                    source_failure_code_digests.append(hashlib.sha256(source_code.encode("utf-8")).hexdigest())
                    self._set_stage(
                        session_id,
                        "searching",
                        query_count=query_count,
                        candidate_count=len(candidates),
                        source_failure_count=source_failure_count,
                    )
                    if source_failure_count >= budget["max_source_failures"]:
                        break
                    continue
                terms = [token for token in query.split() if token][:24]
                for raw in list(found or [])[:per_query_limit]:
                    url = str(raw.get("url") or "")
                    source_kind = _inferred_source_kind(url, str(raw.get("source_kind") or "unknown"))
                    assessed = assess_source_candidate(
                        url=url,
                        source_kind=source_kind,
                        published_at=str(raw.get("published_at") or ""),
                        fetched_at=str(raw.get("fetched_at") or ""),
                        freshness_policy=str(private_row.get("freshness") or "current"),
                        plan_digest=str(private_row.get("plan_digest") or ""),
                    )
                    # Generic definition pages cannot support a candidate-specific
                    # claim; avoid spending the bounded observation budget on them.
                    if source_evidence_role({"public_url": url}).get("evidence_role") == "generic_definition":
                        continue
                    if assessed.get("ok"):
                        assessed["subquestion_id"] = _clean(query_row.get("subquestion_id"), 32) or "rq1"
                        assessed["preferred_source_kind"] = _clean(query_row.get("preferred_source_kind"), 60)
                        if narrow_demand:
                            assessed["evidence_dimension"] = "demand"
                        assessed["_evidence_terms"] = terms
                        key = str(assessed.get("public_url") or assessed.get("source_candidate_digest") or "")
                        candidates.setdefault(key, assessed)
                self._set_stage(session_id, "searching", query_count=query_count, candidate_count=len(candidates))

            ordered = select_diverse_sources(candidates.values(), limit=budget["max_candidates"])
            if required_dimension:
                # A promotional page cannot establish a required dimension, so it must
                # not consume an observation slot ahead of a source that can. This is a
                # stable sort, so diversity ordering survives within each group.
                ordered.sort(key=lambda row: bool(
                    source_evidence_role({"public_url": row.get("public_url")}).get("promotional_or_listicle")
                ))
            initial_page_limit = max(1, budget["max_observed_pages"] - reserved_follow_up_pages) if adaptive_follow_up_possible else budget["max_observed_pages"]
            if not cancelled:
                self._set_stage(session_id, "observing", query_count=query_count, candidate_count=len(candidates))
            observation_queue = list(ordered)
            failed_hosts: set[str] = set()
            replacement_searches_used = 0
            queue_index = 0
            while queue_index < len(observation_queue):
                candidate = observation_queue[queue_index]
                queue_index += 1
                if cancelled or self._is_cancelled(session_id):
                    cancelled = True
                    break
                if observed_pages >= initial_page_limit or observed_bytes >= budget["max_total_bytes"]:
                    break
                elapsed = self.clock() - started
                if elapsed >= budget["max_elapsed_seconds"]:
                    break
                if str(candidate.get("host") or "").casefold() in failed_hosts:
                    # A host that already refused to yield readable text in this run
                    # will refuse again. Spending another failure to learn the same
                    # thing can exhaust the budget on a single unreadable domain.
                    skipped_unreadable_host_count += 1
                    continue
                remaining_bytes = budget["max_total_bytes"] - observed_bytes
                try:
                    observation = dict(adapter.observe(
                        candidate,
                        plan=plan,
                        max_bytes=remaining_bytes,
                        timeout_seconds=max(1.0, min(30.0, budget["max_elapsed_seconds"] - elapsed)),
                    ) or {})
                except Exception as source_error:
                    source_failure_count += 1
                    source_code = _clean(getattr(source_error, "code", ""), 120) or type(source_error).__name__
                    source_failure_code_digests.append(hashlib.sha256(source_code.encode("utf-8")).hexdigest())
                    source_failure_receipts.append({"public_url": candidate.get("public_url"),
                        "source_candidate_digest": candidate.get("source_candidate_digest"),
                        "failure_code_digest": source_failure_code_digests[-1]})
                    failed_host = str(candidate.get("host") or "").casefold()
                    if failed_host:
                        failed_hosts.add(failed_host)
                    self._set_stage(
                        session_id,
                        "observing",
                        observed_page_count=observed_pages,
                        observed_bytes=observed_bytes,
                        query_count=query_count,
                        candidate_count=len(candidates),
                        source_failure_count=source_failure_count,
                    )
                    if source_failure_count >= budget["max_source_failures"]:
                        break
                    # The candidate list is fixed before observation begins, so an
                    # unreadable source otherwise shrinks the evidence pool by one and
                    # the run finishes short while query budget sits unused.
                    if (
                        replacement_searches_used < MAX_OBSERVATION_REPLACEMENTS
                        and query_count < budget["max_queries"]
                        and len(candidates) < budget["max_candidates"]
                        and self.clock() - started < budget["max_elapsed_seconds"]
                    ):
                        replacement_searches_used += 1
                        query_count += 1
                        try:
                            replacements = list(adapter.search(
                                _replacement_search_query(candidate, required_dimension),
                                limit=6,
                                timeout_seconds=max(1.0, min(30.0, budget["max_elapsed_seconds"] - (self.clock() - started))),
                            ) or [])
                        except Exception:
                            replacements = []
                        added = 0
                        for raw in replacements:
                            if added >= MAX_REPLACEMENTS_PER_FAILURE or len(candidates) >= budget["max_candidates"]:
                                break
                            url = str(raw.get("url") or "")
                            if not url or str(urlsplit(url).hostname or "").casefold() in failed_hosts:
                                continue
                            role = source_evidence_role({"public_url": url})
                            if role.get("evidence_role") == "generic_definition":
                                continue
                            if required_dimension and role.get("promotional_or_listicle"):
                                continue
                            replacement = assess_source_candidate(
                                url=url,
                                source_kind=_inferred_source_kind(url, str(raw.get("source_kind") or "unknown")),
                                published_at=str(raw.get("published_at") or ""),
                                fetched_at=str(raw.get("fetched_at") or ""),
                                freshness_policy=str(private_row.get("freshness") or "current"),
                                plan_digest=str(private_row.get("plan_digest") or ""),
                            )
                            if not replacement.get("ok"):
                                continue
                            key = str(replacement.get("public_url") or replacement.get("source_candidate_digest") or "")
                            if not key or key in candidates:
                                continue
                            replacement["subquestion_id"] = _clean(candidate.get("subquestion_id"), 32) or "rq1"
                            replacement["preferred_source_kind"] = _clean(candidate.get("preferred_source_kind"), 60)
                            if narrow_demand:
                                replacement["evidence_dimension"] = "demand"
                            replacement["_evidence_terms"] = list(candidate.get("_evidence_terms") or [])
                            candidates[key] = replacement
                            observation_queue.append(replacement)
                            added += 1
                        self._set_stage(
                            session_id,
                            "observing",
                            observed_page_count=observed_pages,
                            observed_bytes=observed_bytes,
                            query_count=query_count,
                            candidate_count=len(candidates),
                            source_failure_count=source_failure_count,
                        )
                    continue
                try:
                    byte_count = max(0, min(int(observation.get("observed_bytes") or 0), remaining_bytes))
                except (TypeError, ValueError, OverflowError):
                    byte_count = 0
                observed_bytes += byte_count
                observed_pages += 1
                receipts.append(observation)
                citation_id = _clean(observation.get("citation_id"), 80)
                if citation_id:
                    citation_context[citation_id] = {
                        "public_url": str(candidate.get("public_url") or ""),
                        "host": str(candidate.get("host") or ""),
                        "source_kind": str(candidate.get("source_kind") or "unknown"),
                        "subquestion_id": str(candidate.get("subquestion_id") or "rq1"),
                        "source_digest": str(candidate.get("source_candidate_digest") or ""),
                        "canonical_url": str(candidate.get("canonical_url") or ""),
                        "publisher_id": str(candidate.get("publisher_id") or ""),
                        "lineage_origin_digest": str(candidate.get("lineage_origin_digest") or ""),
                        "mirror_of_source_digest": str(candidate.get("mirror_of_source_digest") or ""),
                        "syndicated_from_source_digest": str(candidate.get("syndicated_from_source_digest") or ""),
                        "attribution_source_digest": str(candidate.get("attribution_source_digest") or ""),
                        "attribution_digest": str(candidate.get("attribution_digest") or ""),
                        "content_similarity_digest": str(candidate.get("content_similarity_digest") or ""),
                        "content_similarity_confidence": str(candidate.get("content_similarity_confidence") or ""),
                    }
                self._set_stage(
                    session_id,
                    "observing",
                    observed_page_count=observed_pages,
                    observed_bytes=observed_bytes,
                    query_count=query_count,
                    candidate_count=len(candidates),
                )

            if not cancelled:
                self._set_stage(session_id, "extracting_evidence")
                extraction = extract_claim_evidence(plan_digest=str(private_row["plan_digest"]), observations=receipts, citation_context=citation_context)
                self._set_stage(session_id, "extracting_evidence", evidence_count=int(extraction.get("evidence_count") or 0))

                self._set_stage(session_id, "comparing_evidence")
                comparison = compare_cross_source_evidence(extraction)
                self._set_stage(
                    session_id,
                    "comparing_evidence",
                    claim_count=int(comparison.get("claim_count") or 0),
                    contradiction_count=len(comparison.get("conflicted_claim_codes") or []),
                )

                # v2503.2: identify concrete products, then spend only the
                # reserved budget on their weakest evidence dimensions.
                existing_query_digests = [str(row.get("query_digest") or "") for row in list(query_plan.get("queries") or [])]
                initial_citation_rows = [
                    {
                        "citation_id": _clean(row.get("citation_id"), 80),
                        "public_url": _clean(row.get("public_url"), 2048),
                        "host": _clean(row.get("source_identity"), 255).casefold(),
                        "source_kind": _clean(row.get("source_kind"), 60) or "unknown",
                        "freshness": _clean(row.get("freshness"), 16) or "unknown",
                        "quality_score": float(row.get("quality_score") or 0.0),
                        "relevance_score": float(row.get("relevance_score") or 0.0),
                        "source_digest": _hex64(row.get("source_digest")),
                        "candidate_digest": _hex64(row.get("candidate_digest")),
                        "evidence_dimension": _clean(row.get("evidence_dimension"), 60),
                        "stance": _clean(row.get("stance"), 20) or "unknown",
                        "source_identity_digest": _hex64(row.get("source_identity_digest")),
                        "canonical_page_digest": _hex64(row.get("canonical_page_digest")),
                        "publisher_digest": _hex64(row.get("publisher_digest")),
                        "explicit_origin_digest": _hex64(row.get("explicit_origin_digest")),
                        "attribution_digest": _hex64(row.get("attribution_digest")),
                        "content_similarity_digest": _hex64(row.get("content_similarity_digest")),
                        "content_similarity_confidence": _clean(row.get("content_similarity_confidence"), 24),
                    }
                    for row in list(extraction.get("evidence") or [])
                ]
                discover_candidates = getattr(adapter, "discover_candidates", None)
                if requested_result_count and callable(discover_candidates) and initial_citation_rows and candidate_follow_up_slots:
                    set_time_budget = getattr(adapter, "set_synthesis_time_budget", None)
                    if callable(set_time_budget):
                        set_time_budget(budget["max_elapsed_seconds"] - (self.clock() - started))
                    discovery_synthesis_result = dict(discover_candidates(
                        decomposition=decomposition,
                        citations=initial_citation_rows,
                    ) or {})
                    if not discovery_synthesis_result.get("ok"):
                        repair_discovery = getattr(adapter, "repair_candidate_discovery", None)
                        if callable(repair_discovery):
                            first_request_count = int(discovery_synthesis_result.get("provider_request_count") or 0)
                            repaired_discovery = dict(repair_discovery(
                                decomposition=decomposition,
                                citations=initial_citation_rows,
                            ) or {})
                            repaired_discovery["provider_request_count"] = (
                                first_request_count + int(repaired_discovery.get("provider_request_count") or 0)
                            )
                            repaired_discovery["semantic_repair_used"] = True
                            repaired_discovery["initial_validation_diagnostics"] = {}
                            discovery_synthesis_result = repaired_discovery
                    if discovery_synthesis_result.get("ok"):
                        discovered = validate_research_synthesis(
                            discovery_synthesis_result.get("payload") if isinstance(discovery_synthesis_result.get("payload"), Mapping) else {},
                            citations=initial_citation_rows,
                            requested_result_count=requested_result_count,
                            require_recommendation=False,
                            allow_generic_opportunity_names=True,
                        )
                        initial_discovery_diagnostics = {
                            "input_opportunity_count": int(discovered.get("input_opportunity_count") or 0),
                            "admitted_opportunity_count": int(discovered.get("admitted_opportunity_count") or 0),
                            "rejected_opportunity_reason_counts": dict(discovered.get("rejected_opportunity_reason_counts") or {}),
                            "recommendation_admitted": bool(discovered.get("recommendation_admitted")),
                        }
                        discovery_synthesis_result["validation_status"] = str(discovered.get("status") or "")
                        discovery_is_only_generic = bool(
                            discovered.get("ok")
                            and requested_result_count
                            and int(discovered.get("candidate_specificity_limited_count") or 0) >= requested_result_count
                        )
                        if (not discovered.get("ok") or discovery_is_only_generic) and not discovery_synthesis_result.get("semantic_repair_used"):
                            repair_discovery = getattr(adapter, "repair_candidate_discovery", None)
                            if callable(repair_discovery):
                                first_request_count = int(discovery_synthesis_result.get("provider_request_count") or 0)
                                repaired_discovery = dict(repair_discovery(
                                    decomposition=decomposition,
                                    citations=initial_citation_rows,
                                ) or {})
                                repaired_discovery["provider_request_count"] = (
                                    first_request_count + int(repaired_discovery.get("provider_request_count") or 0)
                                )
                                repaired_discovery["semantic_repair_used"] = True
                                repaired_discovery["initial_validation_diagnostics"] = initial_discovery_diagnostics
                                discovery_synthesis_result = repaired_discovery
                                if discovery_synthesis_result.get("ok"):
                                    discovered = validate_research_synthesis(
                                        discovery_synthesis_result.get("payload") if isinstance(discovery_synthesis_result.get("payload"), Mapping) else {},
                                        citations=initial_citation_rows,
                                        requested_result_count=requested_result_count,
                                        require_recommendation=False,
                                        allow_generic_opportunity_names=True,
                                    )
                                    discovery_synthesis_result["validation_status"] = str(discovered.get("status") or "")
                        discovery_synthesis_result["validation_diagnostics"] = {
                            "input_opportunity_count": int(discovered.get("input_opportunity_count") or 0),
                            "admitted_opportunity_count": int(discovered.get("admitted_opportunity_count") or 0),
                            "rejected_opportunity_reason_counts": dict(discovered.get("rejected_opportunity_reason_counts") or {}),
                            "recommendation_admitted": bool(discovered.get("recommendation_admitted")),
                        }
                        if discovered.get("ok"):
                            validated_candidate_discovery = discovered
                            candidate_follow_up = plan_candidate_evidence_follow_up(
                                discovered,
                                remaining_query_budget=budget["max_queries"] - query_count,
                                remaining_page_budget=budget["max_observed_pages"] - observed_pages,
                                remaining_failure_budget=budget["max_source_failures"] - source_failure_count,
                                existing_query_digests=existing_query_digests,
                                max_followups=candidate_follow_up_slots,
                            )

                # v2502.7 fallback: one generic adaptive follow-up may address
                # a material gap when candidate discovery was unavailable.
                follow_up = plan_adaptive_follow_up(
                    decomposition,
                    source_strategy,
                    comparison,
                    remaining_query_budget=budget["max_queries"] - query_count,
                    remaining_page_budget=budget["max_observed_pages"] - observed_pages,
                    remaining_failure_budget=budget["max_source_failures"] - source_failure_count,
                    existing_query_digests=existing_query_digests,
                    max_followups=(2 if narrow_demand else 1) if budget["max_queries"] >= 3 else 0,
                )
                candidate_follow_up_queries = list(candidate_follow_up.get("queries") or [])
                direction_planner = getattr(adapter, "plan_demand_follow_up", None)
                if narrow_demand and callable(direction_planner) and follow_up.get("queries"):
                    try:
                        evidence_directions = direction_planner(decomposition=decomposition,
                            citations=initial_citation_rows, fallback=list(follow_up["queries"]))
                    except Exception:
                        evidence_directions = {"status": "evidence_direction_planning_failed", "directions": []}
                    if evidence_directions.get("status") == "evidence_directions_ready":
                        follow_up["queries"] = list(evidence_directions["queries"])
                        follow_up["public_summary"] = [{k: row[k] for k in (
                            "subquestion_id", "query_digest", "preferred_source_kind", "follow_up_reason", "private_context_removed")}
                            for row in follow_up["queries"]]
                        follow_up["follow_up_plan_digest"] = _digest(follow_up["public_summary"])
                follow_up_queries = (
                    candidate_follow_up_queries[:candidate_follow_up_slots]
                    if candidate_follow_up_queries
                    else list(follow_up.get("queries") or [])[:2 if narrow_demand else 1]
                )
                if follow_up_queries and not self._is_cancelled(session_id) and self.clock() - started < budget["max_elapsed_seconds"]:
                    self._set_stage(
                        session_id,
                        "candidate_evidence_follow_up" if candidate_follow_up_queries else "adaptive_follow_up",
                    )
                    existing_hosts = {str(row.get("host") or "").casefold() for row in citation_context.values() if row.get("host")}
                    follow_candidates: dict[str, dict[str, Any]] = {}
                    follow_alternatives: dict[str, list[dict[str, Any]]] = {}
                    for follow_index, query_row in enumerate(follow_up_queries):
                        if query_count >= budget["max_queries"] or len(candidates) >= budget["max_candidates"]:
                            break
                        remaining_candidates = budget["max_candidates"] - len(candidates)
                        remaining_follow_queries = max(1, len(follow_up_queries) - follow_index)
                        per_follow_query_limit = max(1, (remaining_candidates + remaining_follow_queries - 1) // remaining_follow_queries)
                        if narrow_demand:
                            per_follow_query_limit = min(3, per_follow_query_limit)
                        search_result_limit = 6 if candidate_follow_up_queries else per_follow_query_limit
                        found = None
                        successful_query = _clean(query_row.get("query"), 320)
                        search_attempt_limit = (
                            MAX_CANDIDATE_FOLLOW_UP_SEARCH_ATTEMPTS_PER_CELL
                            if candidate_follow_up_queries
                            else 1
                        )
                        for search_attempt in range(search_attempt_limit):
                            if (
                                query_count >= budget["max_queries"]
                                or source_failure_count >= budget["max_source_failures"]
                                or self.clock() - started >= budget["max_elapsed_seconds"]
                            ):
                                break
                            successful_query = (
                                _clean(query_row.get("query"), 320)
                                if search_attempt == 0
                                else _candidate_follow_up_retry_query(query_row)
                            )
                            query_count += 1
                            try:
                                found = adapter.search(
                                    successful_query,
                                    limit=search_result_limit,
                                    timeout_seconds=min(
                                        30.0,
                                        max(1.0, budget["max_elapsed_seconds"] - (self.clock() - started)),
                                    ),
                                )
                                break
                            except Exception as search_error:
                                source_failure_count += 1
                                source_code = _clean(getattr(search_error, "code", ""), 120) or type(search_error).__name__
                                source_failure_code_digests.append(hashlib.sha256(source_code.encode("utf-8")).hexdigest())
                                self._set_stage(
                                    session_id,
                                    "candidate_evidence_follow_up" if candidate_follow_up_queries else "adaptive_follow_up",
                                    query_count=query_count,
                                    candidate_count=len(candidates),
                                    source_failure_count=source_failure_count,
                                )
                        if found is None:
                            continue
                        attribution_planner = getattr(adapter, "attribution_candidates", None)
                        if narrow_demand and callable(attribution_planner):
                            # These candidates use existing page slots and the normal
                            # assessment/fetch path, including DNS and peer checks.
                            hints = attribution_planner(known_urls=list(candidates))
                            found = (list(hints)[:1] + list(found))[:search_result_limit]
                        if candidate_follow_up_queries:
                            completed_cell = _clean(query_row.get("subquestion_id"), 80)
                            if completed_cell:
                                completed_candidate_follow_up_cells.add(completed_cell)
                        terms = [token for token in successful_query.split() if token][:24]
                        eligible_for_query: list[dict[str, Any]] = []
                        for raw in list(found or [])[:search_result_limit]:
                            url = str(raw.get("url") or "")
                            source_kind = _inferred_source_kind(url, str(raw.get("source_kind") or "unknown"))
                            assessed = assess_source_candidate(
                                url=url, source_kind=source_kind, published_at=str(raw.get("published_at") or ""),
                                fetched_at=str(raw.get("fetched_at") or ""), freshness_policy=str(private_row.get("freshness") or "current"),
                                plan_digest=str(private_row.get("plan_digest") or ""),
                            )
                            if not assessed.get("ok"):
                                continue
                            assessed["subquestion_id"] = _clean(query_row.get("subquestion_id"), 32) or "rq1"
                            assessed["preferred_source_kind"] = _clean(query_row.get("preferred_source_kind"), 60)
                            assessed["candidate_digest"] = _hex64(query_row.get("candidate_digest"))
                            assessed["evidence_dimension"] = "demand" if narrow_demand else _clean(query_row.get("evidence_dimension"), 60)
                            assessed["_candidate_name"] = _clean(query_row.get("candidate_name"), 140)
                            assessed["_evidence_terms"] = terms
                            key = str(assessed.get("public_url") or assessed.get("source_candidate_digest") or "")
                            if key in candidates:
                                continue
                            eligible_for_query.append(assessed)
                        if candidate_follow_up_queries:
                            subquestion_id = _clean(query_row.get("subquestion_id"), 32)
                            eligible_for_query, alternatives = _select_candidate_follow_up_sources(
                                eligible_for_query,
                                evidence_dimension=_clean(query_row.get("evidence_dimension"), 60),
                                existing_hosts=existing_hosts,
                            )
                            follow_alternatives[subquestion_id] = alternatives
                        for assessed in eligible_for_query:
                            key = str(assessed.get("public_url") or assessed.get("source_candidate_digest") or "")
                            candidates[key] = assessed
                            follow_candidates[key] = assessed
                    follow_ordered = select_diverse_sources(follow_candidates.values(), limit=max(0, budget["max_observed_pages"] - observed_pages))
                    follow_ordered.sort(key=lambda row: (str(row.get("host") or "").casefold() in existing_hosts, -float(row.get("quality_score") or 0.0)))
                    follow_cell_failure_counts: dict[str, int] = {}
                    late_attribution_count = 0
                    for candidate in follow_ordered:
                        if self._is_cancelled(session_id):
                            cancelled = True
                            break
                        if observed_pages >= budget["max_observed_pages"] or observed_bytes >= budget["max_total_bytes"] or source_failure_count >= budget["max_source_failures"]:
                            break
                        elapsed = self.clock() - started
                        if elapsed >= budget["max_elapsed_seconds"]:
                            break
                        # A previous page in this batch may have revealed an original.
                        # Replace an unobserved slot, never append an unbounded crawl.
                        attribution_planner = getattr(adapter, "attribution_candidates", None)
                        if narrow_demand and callable(attribution_planner) and late_attribution_count < 2:
                            hints = attribution_planner(known_urls=list(candidates))
                            if hints:
                                linked = assess_source_candidate(
                                    url=str(hints[0].get("url") or ""), source_kind="unknown",
                                    published_at="", fetched_at="",
                                    freshness_policy=str(private_row.get("freshness") or "current"),
                                    plan_digest=str(private_row.get("plan_digest") or ""))
                                if linked.get("ok"):
                                    old_key = str(candidate.get("public_url") or "")
                                    linked.update({key: candidate.get(key) for key in (
                                        "subquestion_id", "evidence_dimension", "_evidence_terms", "_candidate_name")})
                                    candidates.pop(old_key, None)
                                    candidates[str(linked["public_url"])] = linked
                                    candidate = linked
                                    late_attribution_count += 1
                        remaining_bytes = budget["max_total_bytes"] - observed_bytes
                        subquestion_id = _clean(candidate.get("subquestion_id"), 32)
                        if follow_cell_failure_counts.get(subquestion_id, 0) >= MAX_CANDIDATE_FOLLOW_UP_FAILURES_PER_CELL:
                            continue
                        if str(candidate.get("host") or "").casefold() in failed_hosts:
                            skipped_unreadable_host_count += 1
                            continue
                        while True:
                            try:
                                observation = dict(adapter.observe(candidate, plan=plan, max_bytes=remaining_bytes, timeout_seconds=max(1.0, min(30.0, budget["max_elapsed_seconds"] - elapsed))) or {})
                                break
                            except Exception as source_error:
                                source_failure_count += 1
                                follow_cell_failure_counts[subquestion_id] = follow_cell_failure_counts.get(subquestion_id, 0) + 1
                                source_code = _clean(getattr(source_error, "code", ""), 120) or type(source_error).__name__
                                source_failure_code_digests.append(hashlib.sha256(source_code.encode("utf-8")).hexdigest())
                                source_failure_receipts.append({"public_url": candidate.get("public_url"),
                                    "source_candidate_digest": candidate.get("source_candidate_digest"),
                                    "failure_code_digest": source_failure_code_digests[-1]})
                                alternatives = follow_alternatives.get(subquestion_id, [])
                                replacement = None
                                while alternatives:
                                    possible = alternatives.pop(0)
                                    possible_key = str(possible.get("public_url") or possible.get("source_candidate_digest") or "")
                                    if possible_key and possible_key not in candidates:
                                        replacement = possible
                                        break
                                if (
                                    replacement is None
                                    or follow_cell_failure_counts.get(subquestion_id, 0) >= MAX_CANDIDATE_FOLLOW_UP_FAILURES_PER_CELL
                                    or source_failure_count >= budget["max_source_failures"]
                                    or self.clock() - started >= budget["max_elapsed_seconds"]
                                ):
                                    observation = None
                                    break
                                failed_key = str(candidate.get("public_url") or candidate.get("source_candidate_digest") or "")
                                candidates.pop(failed_key, None)
                                candidate = replacement
                                replacement_key = str(candidate.get("public_url") or candidate.get("source_candidate_digest") or "")
                                candidates[replacement_key] = candidate
                        if observation is None:
                            continue
                        try:
                            byte_count = max(0, min(int(observation.get("observed_bytes") or 0), remaining_bytes))
                        except (TypeError, ValueError, OverflowError):
                            byte_count = 0
                        observed_bytes += byte_count
                        observed_pages += 1
                        receipts.append(observation)
                        citation_id = _clean(observation.get("citation_id"), 80)
                        if citation_id:
                            citation_context[citation_id] = {
                                "public_url": str(candidate.get("public_url") or ""), "host": str(candidate.get("host") or ""),
                                "source_kind": str(candidate.get("source_kind") or "unknown"),
                                "subquestion_id": str(candidate.get("subquestion_id") or "rq1"),
                                "source_digest": str(candidate.get("source_candidate_digest") or ""),
                                "candidate_digest": str(candidate.get("candidate_digest") or ""),
                                "evidence_dimension": str(candidate.get("evidence_dimension") or ""),
                                "canonical_url": str(candidate.get("canonical_url") or ""),
                                "publisher_id": str(candidate.get("publisher_id") or ""),
                                "lineage_origin_digest": str(candidate.get("lineage_origin_digest") or ""),
                                "mirror_of_source_digest": str(candidate.get("mirror_of_source_digest") or ""),
                                "syndicated_from_source_digest": str(candidate.get("syndicated_from_source_digest") or ""),
                                "attribution_source_digest": str(candidate.get("attribution_source_digest") or ""),
                                "attribution_digest": str(candidate.get("attribution_digest") or ""),
                                "content_similarity_digest": str(candidate.get("content_similarity_digest") or ""),
                                "content_similarity_confidence": str(candidate.get("content_similarity_confidence") or ""),
                            }
                    if not cancelled:
                        self._set_stage(session_id, "extracting_evidence")
                        extraction = extract_claim_evidence(plan_digest=str(private_row["plan_digest"]), observations=receipts, citation_context=citation_context)
                        comparison = compare_cross_source_evidence(extraction)
                        self._set_stage(session_id, "comparing_evidence", evidence_count=int(extraction.get("evidence_count") or 0), claim_count=int(comparison.get("claim_count") or 0), contradiction_count=len(comparison.get("conflicted_claim_codes") or []), query_count=query_count, candidate_count=len(candidates), observed_page_count=observed_pages, observed_bytes=observed_bytes, source_failure_count=source_failure_count)

                claim_labels = {
                    _clean(row.get("subquestion_id"), 32): (
                        _clean(row.get("report_label"), 240)
                        or f"{(_clean(row.get('question_kind'), 32) or 'factual').capitalize()} research question {index}"
                    )
                    for index, row in enumerate(list(decomposition.get("subquestions") or []), 1)
                    if _clean(row.get("subquestion_id"), 32)
                }
                citation_rows = [
                    {
                        "citation_id": _clean(row.get("citation_id"), 80),
                        "public_url": _clean(row.get("public_url"), 2048),
                        "host": _clean(row.get("source_identity"), 255).casefold(),
                        "source_kind": _clean(row.get("source_kind"), 60) or "unknown",
                        "freshness": _clean(row.get("freshness"), 16) or "unknown",
                        "quality_score": float(row.get("quality_score") or 0.0),
                        "relevance_score": float(row.get("relevance_score") or 0.0),
                        "source_digest": _hex64(row.get("source_digest")),
                        "candidate_digest": _hex64(row.get("candidate_digest")),
                        "evidence_dimension": _clean(row.get("evidence_dimension"), 60),
                        "stance": _clean(row.get("stance"), 20) or "unknown",
                        "source_identity_digest": _hex64(row.get("source_identity_digest")),
                        "canonical_page_digest": _hex64(row.get("canonical_page_digest")),
                        "publisher_digest": _hex64(row.get("publisher_digest")),
                        "explicit_origin_digest": _hex64(row.get("explicit_origin_digest")),
                        "attribution_digest": _hex64(row.get("attribution_digest")),
                        "content_similarity_digest": _hex64(row.get("content_similarity_digest")),
                        "content_similarity_confidence": _clean(row.get("content_similarity_confidence"), 24),
                    }
                    for row in list(extraction.get("evidence") or [])
                ]
                self._set_stage(session_id, "assembling_report")
                conclusion = assemble_cited_conclusion(comparison, claim_labels=claim_labels, citations=citation_rows)
                synthesize = getattr(adapter, "synthesize", None)
                final_synthesis_allowed = (
                    not requested_result_count
                    or not callable(discover_candidates)
                    or bool(validated_candidate_discovery)
                )
                within_time_budget = self.clock() - started < budget["max_elapsed_seconds"]
                if callable(synthesize) and citation_rows and not cancelled and final_synthesis_allowed and within_time_budget:
                    set_time_budget = getattr(adapter, "set_synthesis_time_budget", None)
                    if callable(set_time_budget):
                        set_time_budget(budget["max_elapsed_seconds"] - (self.clock() - started))
                    synthesis_result = dict(synthesize(decomposition=decomposition, citations=citation_rows) or {})
                    if synthesis_result.get("ok"):
                        expected_dimensions = {
                            "demand", "competition", "implementation_dependencies", "free_tier_feasibility",
                        }
                        candidate_research_matrix_complete = bool(
                            requested_result_count
                            and int(candidate_follow_up.get("candidate_count") or 0) == requested_result_count
                            and int(candidate_follow_up.get("query_count") or 0) >= requested_result_count * len(expected_dimensions)
                            and len(completed_candidate_follow_up_cells) >= requested_result_count * len(expected_dimensions)
                            and set(candidate_follow_up.get("evidence_dimensions") or []) == expected_dimensions
                        )
                        validated_synthesis = validate_research_synthesis(
                            synthesis_result.get("payload") if isinstance(synthesis_result.get("payload"), Mapping) else {},
                            citations=citation_rows,
                            requested_result_count=int(decomposition.get("requested_result_count") or 0),
                            candidate_identities=validated_candidate_discovery,
                            require_candidate_specific_coverage=bool(requested_result_count),
                            candidate_research_matrix_complete=candidate_research_matrix_complete,
                            required_evidence_dimension=(
                                str((decomposition.get("subquestions") or [{}])[0].get("evidence_dimension") or "")
                                if decomposition.get("objective_shape") == "single_candidate_dimension" else ""
                            ),
                        )
                        if not validated_synthesis.get("ok") and decomposition.get("objective_shape") == "single_candidate_dimension":
                            from research_claim_assessment import model_assessed_conclusion
                            assessed = model_assessed_conclusion(
                                synthesis_result.get("payload") or {},
                                assessment_summary=synthesis_result.get("source_assessment_summary") or {},
                                citations=citation_rows,
                                dimension=str((decomposition.get("subquestions") or [{}])[0].get("evidence_dimension") or ""),
                            )
                            if assessed.get("ok"):
                                validated_synthesis = assessed
                            else:
                                model_assessment_denial_reason = _clean(assessed.get("denial_reason"), 80)
                        # Report-only: measure the shared evidence policy against this
                        # run without letting it refuse anything. General research is
                        # currently admitted on far less than a demand claim, and the
                        # gap has to be measured on real corpora before either side is
                        # recalibrated.
                        evidence_policy_evaluation = _evaluate_evidence_policy(
                            payload=synthesis_result.get("payload"),
                            citations=citation_rows,
                            assessment_summary=synthesis_result.get("source_assessment_summary"),
                            currency_requirement=str(decomposition.get("evidence_currency_requirement") or ""),
                            # Read to judge whether the finding answers what was
                            # asked. The measurement returns condition codes and
                            # counts, so the objective text never reaches a receipt.
                            objective=objective,
                        )
                        synthesis_result["validation_status"] = str(validated_synthesis.get("status") or "")
                        if capture_training_evidence:
                            try:
                                from model_training.training_capture_adapters import capture_research_synthesis
                            except ImportError:
                                try:
                                    from model_training.training_capture_adapters import capture_research_synthesis
                                except ImportError:
                                    capture_research_synthesis = None
                            if capture_research_synthesis is not None:
                                try:
                                    capture_receipt = capture_research_synthesis(
                                        runtime_root=self.runtime_root,
                                        capture_authorized=True,
                                        research_context={
                                            "decomposition": decomposition,
                                            "citation_ids": [str(row.get("citation_id") or "") for row in citation_rows],
                                            "candidate_follow_up": candidate_follow_up,
                                        },
                                        model_output=synthesis_result.get("payload") if isinstance(synthesis_result.get("payload"), Mapping) else {},
                                        validation={
                                            "passed": bool(validated_synthesis.get("ok") is True and validated_synthesis.get("status") != "research_model_assessed_inference"),
                                            "deterministic": True,
                                            "validator": "validate_research_synthesis",
                                            "status": str(validated_synthesis.get("status") or ""),
                                        },
                                        provenance={
                                            "session_digest": _digest(session_id),
                                            "authorization_digest": _hex64(authorization_digest),
                                            "synthesis_phase": "final",
                                        },
                                        auto_sanitize=training_policy.auto_sanitize_enabled,
                                    )
                                except Exception as exc:
                                    try:
                                        from model_training.training_capture_runtime import persist_capture_failure
                                    except ImportError:
                                        from model_training.training_capture_runtime import persist_capture_failure
                                    capture_receipt = persist_capture_failure(
                                        runtime_root=self.runtime_root, capability="research",
                                        status="training_capture_failed", failure_class=type(exc).__name__,
                                    )
                                synthesis_result["training_capture_status"] = str(capture_receipt.get("status") or "")
                                synthesis_result["training_sanitization_status"] = str(capture_receipt.get("sanitization_status") or "")
                        # Preserve the deterministic, citation-bound report when
                        # model prose is malformed or fails candidate admission.
                        # Comparative sessions still remain insufficient unless
                        # the stricter candidate-specific gate passes below.
                        if validated_synthesis.get("ok") is True:
                            conclusion = validated_synthesis
                        else:
                            conclusion = assemble_cited_conclusion(
                                comparison,
                                claim_labels=claim_labels,
                                citations=citation_rows,
                            )
                            conclusion["synthesis_rejected"] = True
                            conclusion["synthesis_rejection_status"] = str(validated_synthesis.get("status") or "research_synthesis_rejected")
                            if validated_synthesis.get("rejected_opportunity_reason_counts", {}).get("independent_dimension_support_missing"):
                                conclusion.setdefault("limitations", []).insert(0,
                                    "The admitted observations do not establish two independently supported, current sources for the requested dimension. "
                                    "Vendor offerings, repeated citations and keyword matches do not establish customer demand. Unsupported model conclusions were withheld."
                                )
                synthesis_provider_request_count = (
                    int(discovery_synthesis_result.get("provider_request_count") or 0)
                    + int(synthesis_result.get("provider_request_count") or 0)
                )
                synthesis_provider_contacted = bool(
                    discovery_synthesis_result.get("provider_contacted")
                    or synthesis_result.get("provider_contacted")
                )
            # Exhausting the source-failure budget without observing any usable page is
            # a terminal evidence-acquisition failure, not a completed research session.
            if source_failure_count > 0 and observed_pages == 0:
                raise RuntimeError("source_failure_budget_exhausted")
            report_status = "research_report_insufficient_evidence"
            synthesis_admitted = (
                not requested_result_count and decomposition.get("objective_shape") != "single_candidate_dimension"
            ) or bool(validated_synthesis.get("ok"))
            if synthesis_admitted and conclusion and (conclusion.get("verified_findings") or conclusion.get("reasonable_inferences") or conclusion.get("unresolved_disagreements")):
                report_status = "research_report_ready"
            compatibility_claims = []
            for claim in list(comparison.get("claims") or []):
                compatibility_claims.append({
                    "ok": True,
                    "status": "research_claim_support_assessed",
                    "claim_code": claim.get("claim_code"),
                    "support_state": "conflicted" if claim.get("state") == "conflicted" else "supported" if claim.get("state") == "supported" else "refuted" if claim.get("state") == "refuted" else "insufficient_current_evidence",
                    "supporting_citations": list(claim.get("supporting_citations") or []),
                    "refuting_citations": list(claim.get("refuting_citations") or []),
                    "incomplete_citations": list(claim.get("incomplete_citations") or []),
                    "stale_citations": list(claim.get("stale_citations") or []),
                    "independent_source_count": int(claim.get("independent_source_count") or 0),
                    "independent_evidence_count": int(claim.get("independent_evidence_count") or 0),
                    "duplicate_evidence_count": int(claim.get("duplicate_evidence_count") or 0),
                    "max_quality": float(claim.get("max_quality") or 0.0),
                    "max_relevance": float(claim.get("max_relevance") or 0.0),
                    "contradiction_preserved": bool(claim.get("contradiction_preserved")),
                    "citation_required": True,
                    "internal_knowledge_is_current_evidence": False,
                    "generated_prose_is_evidence": False,
                })
            report = {
                "contract_version": CONTRACT_VERSION,
                "session_id": private_row["session_id"],
                "session_digest": private_row["session_digest"],
                "plan_digest": private_row["plan_digest"],
                "decomposition_digest": private_row.get("decomposition_digest", ""),
                "source_strategy_digest": private_row.get("source_strategy_digest", ""),
                "status": "research_report_cancelled" if cancelled else report_status,
                "claim_assessments": compatibility_claims,
                "verified_findings": list(conclusion.get("verified_findings") or []),
                "reasonable_inferences": list(conclusion.get("reasonable_inferences") or []),
                "unresolved_disagreements": list(conclusion.get("unresolved_disagreements") or []),
                "missing_evidence": list(conclusion.get("missing_evidence") or []),
                "limitations": list(conclusion.get("limitations") or []),
                # Never render a synthesized answer when the report itself remains
                # evidence-incomplete. Reviewers may inspect structured gaps instead.
                "rendered_answer": str(conclusion.get("rendered_answer") or "") if report_status == "research_report_ready" else "",
                "citations": list(conclusion.get("citations") or []),
                "citation_count": int(conclusion.get("citation_count") or 0),
                "contradicted_claim_codes": list(comparison.get("conflicted_claim_codes") or []),
                "uncertainty_preserved": bool(conclusion.get("unresolved_disagreements") or conclusion.get("missing_evidence") or not compatibility_claims),
                "externally_verifiable_claims_traceable": bool(conclusion.get("externally_verifiable_claims_traceable", True)),
                "raw_page_content_persisted": False,
                "raw_query_text_exposed": False,
                "private_objective_exposed": False,
                "generated_prose_is_evidence": False,
                "research_intelligence_version": "v2503.2",
                "source_independence_version": "v2503.3",
                "requested_result_count": int(decomposition.get("requested_result_count") or 0),
                "synthesis_status": str(synthesis_result.get("validation_status") or synthesis_result.get("status") or "research_synthesis_not_available"),
                "model_assessment_denial_reason": model_assessment_denial_reason,
                "evidence_policy_evaluation": evidence_policy_evaluation,
                "source_assessment_summary": dict(synthesis_result.get("source_assessment_summary") or {}),
                "candidate_discovery_synthesis_status": str(discovery_synthesis_result.get("validation_status") or discovery_synthesis_result.get("status") or "candidate_discovery_not_available"),
                "candidate_follow_up_status": str(candidate_follow_up.get("status") or "candidate_evidence_follow_up_not_available"),
                "candidate_follow_up_plan_digest": _hex64(candidate_follow_up.get("candidate_follow_up_plan_digest")),
                "candidate_follow_up_query_count": int(candidate_follow_up.get("query_count") or 0),
                "candidate_follow_up_completed_query_count": len(completed_candidate_follow_up_cells),
                "candidate_follow_up_candidate_count": int(candidate_follow_up.get("candidate_count") or 0),
                "candidate_follow_up_dimensions": list(candidate_follow_up.get("evidence_dimensions") or []),
                "candidate_identity_binding_count": max(
                    int(conclusion.get("candidate_identity_binding_count") or 0),
                    int(candidate_follow_up.get("candidate_count") or 0),
                ),
                "candidate_specificity_limited_count": int(conclusion.get("candidate_specificity_limited_count") or 0),
                "candidate_identity_binding_required": bool(conclusion.get("candidate_identity_binding_required")),
                "candidate_specific_coverage_required": bool(conclusion.get("candidate_specific_coverage_required")) or int(decomposition.get("requested_result_count") or 0) > 1,
                "candidate_specific_coverage_complete": bool(conclusion.get("candidate_specific_coverage_complete")),
                "candidate_research_matrix_complete": bool(conclusion.get("candidate_research_matrix_complete")),
                "candidate_evidence_matrix": list(conclusion.get("candidate_evidence_matrix") or []),
                "recommendation_confidence_assessments": list(conclusion.get("recommendation_confidence_assessments") or []),
                "recommendation_confidence_threshold": str(conclusion.get("recommendation_confidence_threshold") or "moderate-confidence"),
                "strongest_opportunity_admitted": bool(conclusion.get("strongest_opportunity_admitted")),
                "source_independence_summary": dict(conclusion.get("source_independence_summary") or {}),
                "recommendation_deterministic_fallback_used": bool(conclusion.get("recommendation_deterministic_fallback_used")),
                "candidate_identity_exposed_in_public_receipt": False,
                "provider_contacted": synthesis_provider_contacted,
                "provider_request_count": synthesis_provider_request_count,
                "evidence_direction_status": evidence_directions.get("status"),
                "evidence_directions": list(evidence_directions.get("directions") or []),
                "synthesis_provider_contacted": synthesis_provider_contacted,
                "synthesis_provider_request_count": synthesis_provider_request_count,
                "candidate_discovery_retry_used": bool(discovery_synthesis_result.get("generation_retry_used")),
                "candidate_discovery_semantic_repair_used": bool(discovery_synthesis_result.get("semantic_repair_used")),
                "candidate_discovery_initial_validation_diagnostics": dict(discovery_synthesis_result.get("initial_validation_diagnostics") or {}),
                "candidate_discovery_validation_diagnostics": dict(discovery_synthesis_result.get("validation_diagnostics") or {}),
                "final_synthesis_retry_used": bool(synthesis_result.get("generation_retry_used")),
                "private_objective_sent_to_provider": bool(synthesis_result.get("private_objective_sent_to_provider", False)),
                "material_conclusion_traceability": list(conclusion.get("material_conclusion_traceability") or []),
                "all_material_conclusions_evidence_bound_or_labeled_inference": bool(conclusion.get("all_material_conclusions_evidence_bound_or_labeled_inference", True)),
                "repeated_source_citation_count": int(conclusion.get("repeated_source_citation_count") or 0),
                "repeated_or_derivative_citation_count": int((conclusion.get("source_independence_summary") or {}).get("repeated_or_derivative_citation_count") or 0),
                "independent_lineage_count": int((conclusion.get("source_independence_summary") or {}).get("independent_lineage_count") or 0),
                "uncertain_lineage_count": int((conclusion.get("source_independence_summary") or {}).get("uncertain_lineage_count") or 0),
                "repeated_citations_count_as_independent_confirmation": False,
                "minority_and_contradictory_evidence_preserved": bool(conclusion.get("minority_and_contradictory_evidence_preserved", True)),
                "adapter_contract_digest": adapter_contract["adapter_contract_digest"],
                "source_failure_count": source_failure_count,
                "skipped_unreadable_host_count": skipped_unreadable_host_count,
                "source_failure_code_digests": sorted(set(source_failure_code_digests)),
                "source_failure_receipts": sanitize_failures(source_failure_receipts),
                "collection_stop_reason": (
                    "source_failure_budget_reached" if source_failure_count >= budget["max_source_failures"] else
                    "time_budget_reached" if self.clock() - started >= budget["max_elapsed_seconds"] else
                    "page_budget_reached" if observed_pages >= budget["max_observed_pages"] else
                    "byte_budget_reached" if observed_bytes >= budget["max_total_bytes"] else
                    "planned_collection_finished"),
                "pdf_extraction_failure_count": sum(source_failure_code_digests.count(
                    hashlib.sha256(code.encode("ascii")).hexdigest()) for code in (
                        "public_pdf_invalid_or_oversize", "public_pdf_extraction_timeout", "public_pdf_extraction_failed",
                        "public_pdf_encrypted", "public_pdf_page_limit", "public_pdf_content_limit",
                        "public_pdf_text_limit", "public_pdf_no_readable_text", "public_pdf_resource_limit_unavailable")),
                "readable_content_failure_count": source_failure_code_digests.count(
                    hashlib.sha256(b"public_web_demand_readable_content_unavailable").hexdigest()),
                **_DENIED,
            }
            if report.get("candidate_specific_coverage_required") and not report.get("candidate_specific_coverage_complete", True) and not any(
                str(row.get("claim_code") or "").endswith("_candidate_evidence")
                for row in report.get("missing_evidence") or []
                if isinstance(row, Mapping)
            ):
                report.setdefault("missing_evidence", []).append({
                    "claim_code": "candidate_matrix_candidate_evidence",
                    "finding": "Complete candidate-specific evidence coverage",
                    "reason": "The candidate evidence matrix remains incomplete, so a rendered conclusion is suppressed.",
                    "citations": [],
                    "classification": "evidence_gap",
                    "traceable": True,
                })
                report["uncertainty_preserved"] = True
            report["report_digest"] = _digest(report)
        except Exception as error:
            report = {
                "status": "research_report_insufficient_evidence",
                "session_id": session_id,
                "source_failure_count": source_failure_count,
                "skipped_unreadable_host_count": skipped_unreadable_host_count,
                # A run that ends without observing anything is the case most in need
                # of a post-mortem, so its diagnostics must survive the failure path.
                "readable_content_failure_count": source_failure_code_digests.count(
                    hashlib.sha256(b"public_web_demand_readable_content_unavailable").hexdigest()),
                "query_count": query_count,
                "candidate_count": len(candidates),
                "observed_page_count": observed_pages,
                "source_failure_receipts": sanitize_failures(source_failure_receipts),
                "collection_stop_reason": "source_failure_budget_reached" if source_failure_count >= budget["max_source_failures"] else "adapter_execution_failed_safely",
                "verified_findings": [], "citations": [],
                "limitations": ["Research execution failed; retained diagnostics are not research findings."],
                **_DENIED,
            }
            report["report_digest"] = _digest(report)
            failure = _clean(getattr(error, "code", ""), 120) or _clean(str(error), 120) or type(error).__name__

        with self._state_lock():
            state = self._load()
            current = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
            if not current:
                return {"ok": False, "status": "research_session_disappeared", **_DENIED}
            if current.get("state") == "cancelled" or cancelled:
                if current.get("state") != "cancelled":
                    current["state"] = "cancelled"
                    current["completed_at"] = _now()
                    current["stop_reason"] = "operator_cancelled"
                    current["execution_owner_pid"] = 0
                    self._append_stage(current, "cancelled")
                if report.get("report_digest"):
                    current["report_digest"] = str(report.get("report_digest") or "")
                self._persist_terminal_history(state, current, report)
                public = self._public_session(current)
                result = {"session": public, "report": report, "failure_code": ""}
                self._record_event(state, event, "bounded_research_cancelled", result)
                state["revision"] = int(state.get("revision") or 0) + 1
                state["updated_at"] = _now()
                self._save(state)
                return {"ok": True, "status": "bounded_research_cancelled", "idempotent": False, "result": result, **_DENIED}

            current.update({
                "state": "failed" if failure else "completed",
                "completed_at": _now(),
                "query_count": query_count,
                "candidate_count": len(candidates),
                "observed_page_count": observed_pages,
                "observed_bytes": observed_bytes,
                "evidence_count": int(extraction.get("evidence_count") or 0),
                "claim_count": int(comparison.get("claim_count") or 0),
                "contradiction_count": len(comparison.get("conflicted_claim_codes") or []),
                "source_failure_count": source_failure_count,
                "report_digest": str(report.get("report_digest") or ""),
                "failure_code": failure,
                "stop_reason": (
                    "adapter_execution_failed_safely" if failure else
                    "source_failure_budget_reached" if source_failure_count >= budget.get("max_source_failures", 999999) else
                    "time_budget_reached" if self.clock() - started >= budget["max_elapsed_seconds"] else
                    "page_budget_reached" if observed_pages >= budget["max_observed_pages"] else
                    "byte_budget_reached" if observed_bytes >= budget["max_total_bytes"] else
                    "query_budget_reached" if query_count >= budget["max_queries"] else
                    "evidence_threshold_reached" if comparison.get("claims") and all(
                        str(claim.get("state") or "") in {"supported", "refuted"} and int(claim.get("independent_source_count") or 0) >= 2
                        for claim in list(comparison.get("claims") or [])
                    ) else
                    "bounded_research_evidence_gap_preserved"
                ),
                "execution_owner_pid": 0,
            })
            self._append_stage(current, "failed" if failure else "completed")
            self._persist_terminal_history(state, current, report)
            public = self._public_session(current)
            result = {"session": public, "report": report, "failure_code": failure}
            status = "bounded_research_failed_safely" if failure else "bounded_research_completed"
            self._record_event(state, event, status, result, ok=not failure)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now()
            self._save(state)
        return {"ok": not failure, "status": status, "idempotent": False, "result": result, **_DENIED}

    def cancel_session(self, event_id: str, *, session_id: str, session_digest: str) -> dict[str, Any]:
        event = _clean(event_id, 180)
        with self._state_lock():
            state = self._load()
            replay = self._event_replay(state, event)
            if replay:
                return replay
            row = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
            if not row or row.get("session_digest") != _hex64(session_digest):
                return {"ok": False, "status": "exact_research_session_required", **_DENIED}
            if row.get("state") in {"completed", "failed", "cancelled"}:
                return {"ok": False, "status": "terminal_research_session_unchanged", **_DENIED}
            row["state"] = "cancelled"
            row["completed_at"] = _now()
            row["stop_reason"] = "operator_cancelled"
            row["execution_owner_pid"] = 0
            self._append_stage(row, "cancelled")
            self._persist_terminal_history(state, row, {})
            result = self._public_session(row)
            self._record_event(state, event, "research_session_cancelled", result)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now()
            self._save(state)
        return {"ok": True, "status": "research_session_cancelled", "result": result, **_DENIED}

    def history_catalog(self, *, limit: int = 64) -> dict[str, Any]:
        """Inspect terminal session history without exposing objectives, queries, or raw content."""
        bounded = max(1, min(int(limit), 128))
        with self._state_lock():
            state = self._load()
            sessions = {str(row.get("session_id") or ""): dict(row) for row in state.get("sessions", [])}
            reports = dict(state.get("reports") or {})
            records = [dict(row) for row in state.get("history_records", [])][-bounded:]
            revision = max(0, int(state.get("revision") or 0))
        projections: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in reversed(records):
            session_id = _clean(record.get("session_id"), 120)
            seen.add(session_id)
            report_entry = reports.get(session_id)
            report_valid, report_payload = self._validate_report_storage(report_entry) if report_entry else (False, {})
            validation = validate_history_record(
                record,
                session=sessions.get(session_id),
                report=report_payload.get("report") if report_valid else None,
            )
            public = {key: record.get(key) for key in (
                "history_schema_version", "history_record_digest", "session_id", "session_digest",
                "plan_digest", "decomposition_digest", "source_strategy_digest", "created_at",
                "authorized_at", "started_at", "completed_at", "terminal_status", "report_digest",
                "report_structure_digest", "evidence_count", "claim_count", "contradiction_count",
                "citation_count", "source_failure_count", "freshness_bands", "quality_bands",
            )}
            public["integrity_status"] = "valid" if validation.get("ok") else "invalid"
            public["integrity_issues"] = list(validation.get("issues") or [])
            public["report_storage_valid"] = bool(report_valid) if record.get("report_digest") else True
            public["private_objective_exposed"] = False
            public["query_text_exposed"] = False
            public["raw_page_content_exposed"] = False
            projections.append(public)
        missing = []
        for session_id, session in sessions.items():
            if session.get("state") in {"completed", "cancelled", "failed"} and session_id not in seen:
                missing.append({
                    "session_id": session_id,
                    "session_digest": session.get("session_digest"),
                    "terminal_status": "interrupted" if session.get("failure_code") == "interrupted_execution_not_replayed" else session.get("state"),
                    "integrity_status": "missing",
                    "integrity_issues": ["terminal_history_record_missing"],
                })
        return {
            "ok": not any(row.get("integrity_status") == "invalid" for row in projections) and not missing,
            "status": "research_history_catalog_inspected",
            "contract_version": CONTRACT_VERSION,
            "store_revision": revision,
            "history_count": len(projections),
            "sessions": projections,
            "missing_records": missing,
            "duplicate_persistence_idempotent": True,
            "silent_repair_performed": False,
            "network_contacted": False,
            "private_objective_exposed": False,
            "query_text_exposed": False,
            "raw_page_content_exposed": False,
            **_DENIED,
        }

    def inspect_completed_report(self, session_id: str, *, session_digest: str) -> dict[str, Any]:
        """Load one exact completed sanitized report only when history/report integrity is valid."""
        token = _clean(session_id, 120)
        expected = _hex64(session_digest)
        with self._state_lock():
            state = self._load()
            session = next((dict(row) for row in state.get("sessions", []) if row.get("session_id") == token), None)
            record = next((dict(row) for row in state.get("history_records", []) if row.get("session_id") == token), None)
            entry = dict((state.get("reports") or {}).get(token) or {})
        if not session or session.get("state") != "completed" or session.get("session_digest") != expected:
            return {"ok": False, "status": "exact_completed_research_session_required", "network_contacted": False, **_DENIED}
        report_valid, payload = self._validate_report_storage(entry)
        validation = validate_history_record(record, session=session, report=payload.get("report") if report_valid else None)
        if not report_valid or not validation.get("ok"):
            return {
                "ok": False,
                "status": "research_history_integrity_failure",
                "history_issues": list(validation.get("issues") or []) + ([] if report_valid else ["report_storage_digest_invalid"]),
                "silent_repair_performed": False,
                "network_contacted": False,
                **_DENIED,
            }
        return {
            "ok": True,
            "status": "completed_research_report_inspected",
            "session": self._public_session(session),
            "history_record": record,
            "report": dict(payload.get("report") or {}),
            "network_contacted": False,
            "runtime_mutated": False,
            **_DENIED,
        }

    def compare_sessions(
        self,
        *,
        left_session_id: str,
        left_session_digest: str,
        right_session_id: str,
        right_session_digest: str,
    ) -> dict[str, Any]:
        left = self.inspect_completed_report(left_session_id, session_digest=left_session_digest)
        right = self.inspect_completed_report(right_session_id, session_digest=right_session_digest)
        if not left.get("ok") or not right.get("ok"):
            return {
                "ok": False,
                "status": "research_sessions_not_meaningfully_comparable",
                "left_status": left.get("status"),
                "right_status": right.get("status"),
                "comparison_reason": "Both exact sessions must be completed and integrity-valid.",
                "network_contacted": False,
                **_DENIED,
            }
        return compare_reports(
            dict(left.get("history_record") or {}),
            dict(left.get("report") or {}),
            dict(right.get("history_record") or {}),
            dict(right.get("report") or {}),
        )

    def export_report_markdown(
        self,
        event_id: str,
        *,
        session_id: str,
        session_digest: str,
    ) -> dict[str, Any]:
        """Persist one exact operator-selected Markdown export under the external runtime root."""
        event = _clean(event_id, 180)
        if not event:
            return {"ok": False, "status": "research_event_id_required", **_DENIED}
        with self._state_lock():
            state = self._load()
            replay = self._event_replay(state, event)
            if replay:
                return replay
        inspected = self.inspect_completed_report(session_id, session_digest=session_digest)
        if not inspected.get("ok"):
            return dict(inspected)
        export = render_markdown_export(session_id, dict(inspected.get("report") or {}))
        if not export.get("ok"):
            return dict(export)
        file_name = f"{_clean(session_id, 120)}_{str(export.get('export_digest') or '')[:16]}.md"
        export_dir = self.runtime_root / "research" / "exports"
        export_path = export_dir / file_name
        payload = str(export.get("markdown") or "").encode("utf-8")
        export_dir.mkdir(parents=True, exist_ok=True)
        if export_path.exists():
            existing = export_path.read_bytes()
            if hashlib.sha256(existing).hexdigest() != hashlib.sha256(payload).hexdigest():
                return {
                    "ok": False,
                    "status": "research_export_conflict_not_overwritten",
                    "file_name": file_name,
                    "network_contacted": False,
                    "uploaded": False,
                    **_DENIED,
                }
        else:
            temp = export_path.with_suffix(f".tmp-{os.getpid()}-{threading.get_ident()}")
            temp.write_bytes(payload)
            os.replace(temp, export_path)
        result = {
            "session_id": _clean(session_id, 120),
            "session_digest": _hex64(session_digest),
            "report_digest": export.get("report_digest"),
            "export_schema_version": export.get("export_schema_version"),
            "export_digest": export.get("export_digest"),
            "export_byte_count": len(payload),
            "file_name": file_name,
            "local_runtime_export": True,
            "uploaded": False,
            "transmitted": False,
            "private_path_exposed": False,
            **_DENIED,
        }
        with self._state_lock():
            state = self._load()
            replay = self._event_replay(state, event)
            if replay:
                return replay
            self._record_event(state, event, "bounded_research_report_exported", result)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = _now()
            self._save(state)
        return {"ok": True, "status": "bounded_research_report_exported", "idempotent": False, "result": result, **_DENIED}

    def inspection_summary(self) -> dict[str, Any]:
        with self._state_lock():
            state = self._load()
        sessions = [self._public_session(row) for row in state.get("sessions", [])]
        return {
            "ok": True,
            "status": "bounded_research_sessions_inspected",
            "contract_version": CONTRACT_VERSION,
            "session_count": len(sessions),
            "sessions": sessions,
            "objective_text_exposed": False,
            "query_text_exposed": False,
            "private_subquestions_exposed": False,
            "raw_page_content_exposed": False,
            "provider_neutral": True,
            "one_authorization_per_session": True,
            "per_page_approval_required": False,
            "interrupted_external_operation_replayed": False,
            **_DENIED,
        }

    def inspect_session(self, session_id: str, *, session_digest: str = "") -> dict[str, Any]:
        """Return one content-free durable session projection without mutation or web contact."""
        token = _clean(session_id, 120)
        expected_digest = _hex64(session_digest) if session_digest else ""
        with self._state_lock():
            state = self._load()
            row = next((item for item in state.get("sessions", []) if item.get("session_id") == token), None)
            revision = max(0, int(state.get("revision") or 0))
        if not row or (expected_digest and row.get("session_digest") != expected_digest):
            return {
                "ok": False,
                "status": "exact_research_session_not_found",
                "store_revision": revision,
                "session": {},
                "network_contacted": False,
                "runtime_mutated": False,
                **_DENIED,
            }
        public = self._public_session(row)
        return {
            "ok": True,
            "status": "bounded_research_session_inspected",
            "store_revision": revision,
            "session": public,
            "network_contacted": False,
            "runtime_mutated": False,
            **_DENIED,
        }


__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_BUDGET",
    "HARD_LIMITS",
    "ReadOnlyResearchAdapter",
    "ResearchSessionRef",
    "validate_read_only_adapter",
    "BoundedResearchSessionStore",
]
