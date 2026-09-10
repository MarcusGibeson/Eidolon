from __future__ import annotations

"""Isolated HTTP probe for one Eidolon dashboard route.

The parent release verifier launches one worker process per route. A slow or
wedged renderer can therefore be terminated without leaving handler threads in
the verifier process or contaminating later probes.
"""

import argparse
import json
import sys
import os
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for import_dir in (AGENT, ROOT / "tools"):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))


def probe(path: str, *, timeout: float) -> dict[str, Any]:
    import dashboard

    started = time.monotonic()
    server = HTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
    server.timeout = timeout
    result: dict[str, Any] = {}

    def request_route() -> None:
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}{path}"
            with urllib.request.urlopen(url, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
            crashed = "Dashboard route crashed" in body or "Traceback" in body
            result.update({
                "path": path,
                "status": int(response.status),
                "bytes": len(body),
                "crashed": crashed,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "timeout_seconds": timeout,
                "ok": response.status == 200 and not crashed and len(body) > 500,
            })
        except Exception as exc:
            result.update({
                "path": path,
                "status": 0,
                "bytes": 0,
                "crashed": True,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "timeout_seconds": timeout,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            })

    client = threading.Thread(target=request_route, daemon=True)
    client.start()
    try:
        # Handle exactly one request synchronously. This avoids serve_forever(),
        # shutdown coordination, and lingering handler threads.
        server.handle_request()
        client.join(timeout=2)
    finally:
        server.server_close()
    if not result:
        result.update({
            "path": path,
            "status": 0,
            "bytes": 0,
            "crashed": True,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "timeout_seconds": timeout,
            "ok": False,
            "error": "route request did not produce a result",
        })
    return result


def probe_suite(route_timeouts: dict[str, float]) -> dict[str, Any]:
    routes: dict[str, Any] = {}
    for path, timeout in route_timeouts.items():
        routes[str(path)] = probe(str(path), timeout=max(1.0, float(timeout)))
    return {
        "ok": bool(routes) and all(row.get("ok") is True for row in routes.values()),
        "route_count": len(routes),
        "routes": routes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Eidolon dashboard routes in an isolated worker process.")
    parser.add_argument("--path")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--suite-json", help="JSON object mapping dashboard paths to per-route timeouts.")
    parser.add_argument("--result-file", help="Write the JSON result to this parent-owned temporary file.")
    args = parser.parse_args()
    try:
        if args.suite_json:
            decoded = json.loads(args.suite_json)
            if not isinstance(decoded, dict) or not decoded:
                raise ValueError("suite-json must be a non-empty object")
            result = probe_suite({str(k): float(v) for k, v in decoded.items()})
        elif args.path and args.timeout is not None:
            result = probe(args.path, timeout=max(1.0, args.timeout))
        else:
            raise ValueError("provide --suite-json or both --path and --timeout")
    except Exception as exc:
        result = {
            "path": args.path or "<suite>",
            "status": 0,
            "bytes": 0,
            "crashed": True,
            "elapsed_seconds": 0.0,
            "timeout_seconds": args.timeout,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    payload = json.dumps(result, sort_keys=True)
    if args.result_file:
        result_path = Path(args.result_file)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = result_path.with_suffix(result_path.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, result_path)
    else:
        print(payload)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    exit_code = main()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        os._exit(exit_code)
