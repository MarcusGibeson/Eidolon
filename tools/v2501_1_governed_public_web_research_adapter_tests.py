from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2501-1-data-")

from conscious_agent.bounded_autonomous_web_research import (  # noqa: E402
    BoundedResearchSessionStore,
    validate_read_only_adapter,
)
from conscious_agent.governed_public_web_research_adapter import (  # noqa: E402
    GovernedPublicWebResearchAdapter,
    PublicWebResearchError,
)
from conscious_agent.research_web_intelligence_v2100 import (  # noqa: E402
    assess_source_candidate,
    capture_research_evidence,
    plan_research,
)


checks: list[str] = []


def require(value: object, name: str) -> None:
    checks.append(name)
    assert value, name


def resolver(host: str, port: int, **kwargs):
    try:
        socket.inet_pton(socket.AF_INET, host)
        address = host
    except OSError:
        address = "93.184.216.34"
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]


class FakeCookies:
    def __init__(self) -> None:
        self.clear_count = 0

    def clear(self) -> None:
        self.clear_count += 1


class FakeSocket:
    def getpeername(self):
        return ("93.184.216.34", 443)


class FakeConnection:
    def __init__(self) -> None:
        self.sock = FakeSocket()


class FakeRaw:
    def __init__(self) -> None:
        self._connection = FakeConnection()


class FakeResponse:
    def __init__(self, body: bytes = b"", *, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self.body = body
        self.status_code = status
        self.headers = headers or {"Content-Type": "text/html", "Content-Length": str(len(body))}
        self.raw = FakeRaw()

    def iter_content(self, chunk_size: int):
        for index in range(0, len(self.body), max(1, min(chunk_size, 7))):
            yield self.body[index:index + max(1, min(chunk_size, 7))]


class FakeSession:
    def __init__(self, factory: "FakeFactory", response: FakeResponse) -> None:
        self.factory = factory
        self.response = response
        self.cookies = FakeCookies()
        self.trust_env = True
        self.closed = False

    def get(self, url: str, **kwargs):
        self.factory.calls.append({"url": url, "kwargs": kwargs, "trust_env": self.trust_env})
        return self.response

    def close(self) -> None:
        self.closed = True


class FakeFactory:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        if not self.responses:
            raise AssertionError("fixture response exhausted")
        session = FakeSession(self, self.responses.pop(0))
        self.sessions.append(session)
        return session


def adapter_for(*responses: FakeResponse, custom_resolver=resolver) -> tuple[GovernedPublicWebResearchAdapter, FakeFactory]:
    factory = FakeFactory(list(responses))
    adapter = GovernedPublicWebResearchAdapter(resolver=custom_resolver, session_factory=factory)
    return adapter, factory


base, base_factory = adapter_for(FakeResponse(b"<html></html>"))
contract = validate_read_only_adapter(base)
require(contract["ok"], "production_adapter_satisfies_v2501_session_contract")
require(base.describe()["ambient_proxy_or_auth_inherited"] is False, "ambient_proxy_and_auth_denied")

peer_mismatch, _ = adapter_for(FakeResponse(b"content"), custom_resolver=lambda host, port, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.35", port))])
try:
    peer_mismatch._fetch("https://example.com/", max_bytes=100, timeout_seconds=2)
    peer_mismatch_rejected = False
except PublicWebResearchError as error:
    peer_mismatch_rejected = error.code == "public_web_connected_peer_dns_mismatch"
require(peer_mismatch_rejected, "connected_peer_must_match_prevalidated_dns_set")

try:
    GovernedPublicWebResearchAdapter(search_endpoint="http://user:pass@example.com/search")
    credentialed_rejected = False
except PublicWebResearchError as error:
    credentialed_rejected = error.code == "public_search_endpoint_rejected"
require(credentialed_rejected, "credentialed_search_endpoint_rejected")

private, _ = adapter_for(FakeResponse(b"private"))
try:
    private._fetch("http://127.0.0.1/private", max_bytes=100, timeout_seconds=2)
    private_rejected = False
except PublicWebResearchError as error:
    private_rejected = error.code == "public_web_private_or_non_global_target_rejected"
require(private_rejected, "literal_private_network_target_rejected_before_request")

redirect, redirect_factory = adapter_for(
    FakeResponse(status=302, headers={"Location": "http://127.0.0.1/private", "Content-Type": "text/html"}),
)
try:
    redirect._fetch("https://example.com/start", max_bytes=100, timeout_seconds=2)
    redirect_rejected = False
except PublicWebResearchError as error:
    redirect_rejected = error.code == "public_web_private_or_non_global_target_rejected"
require(redirect_rejected and len(redirect_factory.calls) == 1, "redirect_target_revalidated_before_follow")

dns_calls = 0
def rebinding_resolver(host: str, port: int, **kwargs):
    global dns_calls
    dns_calls += 1
    address = "93.184.216.34" if dns_calls == 1 else "93.184.216.35"
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

rebinding, _ = adapter_for(FakeResponse(b"content"), custom_resolver=rebinding_resolver)
try:
    rebinding._fetch("https://example.com/", max_bytes=100, timeout_seconds=2)
    rebind_rejected = False
except PublicWebResearchError as error:
    rebind_rejected = error.code == "public_web_dns_rebinding_rejected"
require(rebind_rejected, "dns_rebinding_change_rejected")

oversized, _ = adapter_for(FakeResponse(b"small", headers={"Content-Type": "text/html", "Content-Length": "9999"}))
try:
    oversized._fetch("https://example.com/", max_bytes=10, timeout_seconds=2)
    length_rejected = False
except PublicWebResearchError as error:
    length_rejected = error.code == "public_web_content_length_exceeded"
require(length_rejected, "declared_oversized_response_rejected")

streamed, _ = adapter_for(FakeResponse(b"0123456789", headers={"Content-Type": "text/html"}))
try:
    streamed._fetch("https://example.com/", max_bytes=5, timeout_seconds=2)
    stream_rejected = False
except PublicWebResearchError as error:
    stream_rejected = error.code == "public_web_stream_byte_limit_exceeded"
require(stream_rejected, "streaming_byte_overrun_rejected")

search_html = b"""
<a class='result__a' href='/l/?uddg=https%3A%2F%2Fdocs.example.com%2Freport%3Fsecret%3Dgone'>One</a>
<a class='result__a' href='http://127.0.0.1/private'>Private</a>
<a class='result__a' href='https://analysis.example.org/second'>Two</a>
"""
search_adapter, search_factory = adapter_for(FakeResponse(search_html))
results = search_adapter.search("private operator research objective", limit=5, timeout_seconds=5)
require(len(results) == 2, "search_returns_only_distinct_public_results")
require(results[0]["url"].startswith("https://docs.example.com/report"), "wrapped_search_target_decoded")
require(all(row["raw_search_content_exposed"] is False for row in results), "search_results_are_content_minimized")
request = search_factory.calls[0]
require(request["kwargs"]["allow_redirects"] is False and request["kwargs"]["stream"] is True, "http_client_uses_manual_redirects_and_streaming")
require(request["trust_env"] is False and search_factory.sessions[0].cookies.clear_count >= 2, "ambient_auth_and_cookie_state_cleared")
require(set(request["kwargs"]) <= {"headers", "allow_redirects", "stream", "timeout"}, "search_uses_get_without_body_upload_or_auth")

plan = plan_research("What evidence supports the public claim?", freshness="stable")
candidate = assess_source_candidate(
    url="https://docs.example.com/report?private=removed",
    source_kind="primary_official",
    freshness_policy="stable",
    plan_digest=plan["plan_digest"],
)
page = b"<html><script>secret script text</script><body>Public source evidence.</body></html>"
observe_adapter, _ = adapter_for(FakeResponse(page))
receipt = observe_adapter.observe(candidate, plan=plan, max_bytes=4096, timeout_seconds=5)
bundle = capture_research_evidence(plan_digest=plan["plan_digest"], observations=[receipt])
require(bundle["evidence_count"] == 1, "signed_native_observation_receipt_is_accepted")
require(receipt["raw_content_included"] is False and b"Public source evidence" not in json.dumps(receipt).encode(), "raw_page_content_never_enters_receipt")
require("?" not in receipt["public_url"] and receipt["write_method_used"] is False, "receipt_url_is_sanitized_and_read_only")
require(receipt["connected_peer_validated"] is True, "receipt_confirms_connected_peer_validation")

coordinator_search = FakeResponse(b"<a class='result__a' href='https://docs.example.com/report'>One</a>")
coordinator_page = FakeResponse(b"<html><body>Observed public evidence.</body></html>")
coordinator_adapter, coordinator_factory = adapter_for(coordinator_search, coordinator_page)
store = BoundedResearchSessionStore(Path(os.environ["EIDOLON_DATA_DIR"]))
created = store.create_session("create", objective="Research one public evidence claim", freshness="stable", budget={"max_queries": 1, "max_candidates": 2, "max_observed_pages": 1})
session = created["result"]
authorized = store.authorize_session("authorize", session_id=session["session_id"], session_digest=session["session_digest"], public_query_confirmed=True)
executed = store.execute_session("execute", session_id=session["session_id"], authorization_digest=authorized["result"]["authorization_digest"], adapter=coordinator_adapter)
require(executed["ok"] and executed["result"]["session"]["observed_page_count"] == 1, "real_adapter_contract_completes_bounded_coordinator_cycle")
require(len(coordinator_factory.calls) == 2, "bounded_cycle_uses_one_search_and_one_page_get")
replay = store.execute_session("execute", session_id=session["session_id"], authorization_digest=authorized["result"]["authorization_digest"], adapter=coordinator_adapter)
require(replay["idempotent"] and len(coordinator_factory.calls) == 2, "coordinator_replay_never_recontacts_public_web")

print(json.dumps({
    "suite": "v2501.1-governed-public-web-research-adapter",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
    "native_network_contacted": False,
    "write_method_used": False,
    "authority_expanded": False,
}, sort_keys=True))
