from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1500-6-")
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "conscious_agent")]

import dashboard
import dashboard_chat_console


passed = failed = 0


def check(name: str, condition: bool, details: object = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print("PASS", name)
    else:
        failed += 1
        print("FAIL", name, details)


def forbidden(*_args: object, **_kwargs: object) -> object:
    raise AssertionError("deferred dashboard dependency ran during initial render")


dashboard.list_dashboard_chat_turns = forbidden
dashboard_chat_console.dashboard_chat_attention_center_payload = forbidden
dashboard_chat_console.dashboard_session_operation_cue = forbidden

first_html = dashboard.render_chat_console()
started = time.perf_counter()
chat_html = dashboard.render_chat_console()
warm_render_seconds = time.perf_counter() - started

daily_paths = ("/chat-console", "/memory", "/development-campaigns", "/activity", "/settings", "/advanced")
check("chat render defers duplicate transcript and attention scans", bool(chat_html))
check("warm initial chat render stays below one second", warm_render_seconds < 1.0, warm_render_seconds)
check("initial page payload is bounded below 400 KB", len(chat_html.encode("utf-8")) < 400_000, len(chat_html.encode("utf-8")))
check("daily navigation exposes six focused destinations", all(f"href='{path}'" in chat_html for path in daily_paths))
check("ordinary navigation omits historical proof-route clutter", "/dashboard-dispatcher-batch-decomposition-prep-v13" not in chat_html)
check("advanced route preserves historical navigation", "/dashboard-dispatcher-batch-decomposition-prep-v13" in dashboard.render_advanced())
check("attention center has a deferred read-only endpoint", "/api/dashboard-chat/attention-center" in chat_html)
check("project recovery starts after first paint", "window.setTimeout(refreshProjectRecoveryState, 0)" in chat_html)
check(
    "operational status panels live behind conversation options",
    chat_html.index("chat-tools-drawer") < chat_html.index("chat-project-recovery"),
)
check("conversation selector is bounded to thirty sessions", "offset=0, limit=30" in (ROOT / "conscious_agent/dashboard_chat_console.py").read_text(encoding="utf-8"))
check("advanced route is registered exactly once", (ROOT / "conscious_agent/dashboard.py").read_text(encoding="utf-8").count('elif path == "/advanced":') == 1)

release_verify_text = (ROOT / "tools/release_verify.py").read_text(encoding="utf-8")
check("v1500.6 suite registered exactly once", release_verify_text.count("v1500_6_dashboard_simplification_performance_tests.py") == 1)

result = {
    "ok": failed == 0,
    "passed": passed,
    "failed": failed,
    "suite": "v1500.6-dashboard-simplification-performance",
    "warm_render_ms": round(warm_render_seconds * 1000, 3),
    "initial_html_bytes": len(chat_html.encode("utf-8")),
    "provider_contacted": False,
    "source_mutated": False,
    "authority_granted": False,
    "content_free": True,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
