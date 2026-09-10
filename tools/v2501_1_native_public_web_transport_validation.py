from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from conscious_agent.governed_public_web_research_adapter import (  # noqa: E402
    GovernedPublicWebResearchAdapter,
    PublicWebResearchError,
)
from conscious_agent.research_web_intelligence_v2100 import (  # noqa: E402
    assess_source_candidate,
    plan_research,
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an explicit content-free native v2501.1 transport probe.")
    parser.add_argument("--confirm-native", action="store_true")
    parser.add_argument("--include-search", action="store_true")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    if not args.confirm_native:
        print(json.dumps({
            "suite": "v2501.1-native-public-web-transport",
            "ok": False,
            "blocked": True,
            "reason": "explicit_native_confirmation_required",
            "network_contacted": False,
        }, sort_keys=True))
        return 2

    adapter = GovernedPublicWebResearchAdapter()
    plan = plan_research(
        "Validate one public read-only source without retaining its content",
        freshness="stable",
    )
    candidate = assess_source_candidate(
        url="https://example.com/",
        source_kind="primary_official",
        freshness_policy="stable",
        plan_digest=plan["plan_digest"],
    )
    started = time.perf_counter()
    try:
        receipt = adapter.observe(candidate, plan=plan, max_bytes=250_000, timeout_seconds=args.timeout)
        observe_ms = round((time.perf_counter() - started) * 1000, 3)
        search_count = 0
        search_ms = None
        search_digest = ""
        if args.include_search:
            search_started = time.perf_counter()
            results = adapter.search("Python language documentation", limit=3, timeout_seconds=args.timeout)
            search_ms = round((time.perf_counter() - search_started) * 1000, 3)
            search_count = len(results)
            search_digest = _digest([
                {"digest": row.get("search_result_digest", ""), "kind": row.get("source_kind", "")}
                for row in results
            ])
        payload = {
            "suite": "v2501.1-native-public-web-transport",
            "ok": True,
            "blocked": False,
            "network_contacted": True,
            "method": "GET",
            "observe_ms": observe_ms,
            "observed_bytes": int(receipt.get("observed_bytes", 0)),
            "redirect_count": int(receipt.get("redirect_count", 0)),
            "receipt_digest": receipt.get("receipt_digest", ""),
            "content_digest": receipt.get("content_digest", ""),
            "raw_content_included": bool(receipt.get("raw_content_included")),
            "credentials_sent": bool(receipt.get("credentials_sent")),
            "cookies_sent": bool(receipt.get("cookies_sent")),
            "write_method_used": bool(receipt.get("write_method_used")),
            "search_included": bool(args.include_search),
            "search_result_count": search_count,
            "search_ms": search_ms,
            "search_evidence_digest": search_digest,
        }
        print(json.dumps(payload, sort_keys=True))
        return 0
    except PublicWebResearchError as error:
        print(json.dumps({
            "suite": "v2501.1-native-public-web-transport",
            "ok": False,
            "blocked": False,
            "network_contacted": True,
            "failure_code": error.code,
            "raw_content_included": False,
            "credentials_sent": False,
            "cookies_sent": False,
            "write_method_used": False,
        }, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
