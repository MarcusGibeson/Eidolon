from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1250-8-"))

import api_catalog  # noqa: E402
import api_http_runtime  # noqa: E402
import api_server  # noqa: E402
from api_surface_runtime_decomposition import (  # noqa: E402
    AUTHORITY_FLAGS,
    BASELINE_NORMALIZED_INDEX_SHA256,
    BASELINE_PARENT_LINE_COUNT,
    CONTRACT_VERSION,
    validate_api_surface_runtime_decomposition,
)
from api_surface_runtime_decomposition_checkpoint import build_api_surface_runtime_decomposition_checkpoint  # noqa: E402
from checkpoint_registry import lookup_checkpoint, validate_checkpoint_report  # noqa: E402

from release_authority import WORKING_SOURCE_VERSION
checks: list[bool] = []


def require(value: object) -> None:
    ok = bool(value)
    checks.append(ok)
    assert ok


validation = validate_api_surface_runtime_decomposition(source_root=ROOT)
checkpoint = build_api_surface_runtime_decomposition_checkpoint(source_root=ROOT)
checkpoint_validation = validate_checkpoint_report(checkpoint, source_root=ROOT)
parent_source = (ROOT / "conscious_agent/api_server.py").read_text(encoding="utf-8")
catalog_source = (ROOT / "conscious_agent/api_catalog.py").read_text(encoding="utf-8")
runtime_source = (ROOT / "conscious_agent/api_http_runtime.py").read_text(encoding="utf-8")
index = api_server._api_index()

require(CONTRACT_VERSION == "v1250.8")
require(api_catalog.CONTRACT_VERSION == "v1250.8")
require(api_http_runtime.CONTRACT_VERSION == "v1250.8")
require(BASELINE_PARENT_LINE_COUNT == 10377)
require(BASELINE_NORMALIZED_INDEX_SHA256 == "c8750522096806b8aa334c1bc2a381bd52cf499f9d719b14bbb34d1f5e3d5027")
require(validation["ok"] is True)
require(validation["status"] == "api_surface_runtime_decomposed")
require(validation["passed"] == validation["total"] == 17)
require(all(validation["checks"].values()))
require(validation["parent_line_count"] < 9727)
require(650 <= validation["catalog_line_count"] <= 720)
require(120 <= validation["runtime_line_count"] <= 180)
require(validation["endpoint_count"] == 649)
require(validation["normalized_index_sha256"] == BASELINE_NORMALIZED_INDEX_SHA256)
require(len(validation["validation_digest"]) == 64)
require(index == api_catalog.build_api_index(api_server.API_VERSION))
require(index["version"] == WORKING_SOURCE_VERSION)
require(index["name"] == "Eidolon Local API")
require(len(index["endpoints"]) == 649)
require("Local-only by default" in index["safety"])
require("approval" in index["safety"].lower())
require("def _api_index()" in parent_source)
require("def build_api_index(" in catalog_source)
require("def handle_api_get(" in parent_source)
require("def handle_api_post(" in parent_source)
require("def dispatch_api(" in parent_source)
require("def handle_api_get(" not in runtime_source)
require("def handle_api_post(" not in runtime_source)
require("class EidolonApiHandler" in runtime_source)
require("ApiRuntimeDependencies" in runtime_source)
require("serve_api" in parent_source)
require("load_settings=load_settings" in parent_source)
require(api_server.EidolonApiHandler.__module__ == "api_http_runtime")
require(api_server.EidolonApiHandler.server_version == "EidolonAPI/10.0")
require(issubclass(api_server.EidolonApiHandler, api_http_runtime.BaseHTTPRequestHandler))
original_dispatch = api_server.dispatch_api
def _probe_dispatch(method: str, path: str, **_kwargs: object) -> tuple[int, dict[str, object]]:
    return 200, {"ok": True, "data": {"method": method, "path": path, "late_bound": True}}
api_server.dispatch_api = _probe_dispatch
server = ThreadingHTTPServer(("127.0.0.1", 0), api_server.EidolonApiHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/late-binding-probe", timeout=5) as response:
        probe_payload = json.loads(response.read().decode("utf-8"))
    require(probe_payload["data"]["late_bound"] is True)
    require(probe_payload["data"]["path"] == "/api/late-binding-probe")
finally:
    api_server.dispatch_api = original_dispatch
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
require(not thread.is_alive())
status, payload = api_server.dispatch_api("GET", "/api")
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["version"] == WORKING_SOURCE_VERSION)
status, payload = api_server.dispatch_api("GET", "/api/definitely-not-a-route")
require(status == 404)
require(payload["ok"] is False)
require("Unknown API endpoint" in payload["error"])
status, payload = api_server.dispatch_api("DELETE", "/api")
require(status == 405)
require(payload["ok"] is False)
require("shell=True" not in runtime_source)
require("subprocess" not in runtime_source)
require("provider" not in runtime_source.lower())
require("project_mutation_authorized" not in runtime_source)
require(lookup_checkpoint("1250.8") is not None)
require(lookup_checkpoint("1250.8").title == "API Catalog and HTTP Runtime Decomposition")
require(checkpoint["ok"] is True)
require(checkpoint["checkpoint_version"] == "1250.8")
require(checkpoint["status"] == "api_surface_runtime_decomposition_ready")
require(checkpoint["passed"] == checkpoint["total"] == 4)
require(checkpoint["details"]["endpoint_count"] == 649)
require(checkpoint_validation["ok"] is True)
require(checkpoint_validation["passed"] == checkpoint_validation["total"])
require("v1250.8 API Catalog and HTTP Runtime Decomposition" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
for key, expected in AUTHORITY_FLAGS.items():
    require(expected is False)
    require(validation[key] is False)
    require(checkpoint.get(key, False) is False)

result = {"suite": "v1250.8-api-catalog-http-runtime-decomposition", "ok": all(checks), "passed": sum(checks), "total": len(checks)}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
