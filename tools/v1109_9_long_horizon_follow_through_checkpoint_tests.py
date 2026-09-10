from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

from conscious_agent.api_server import dispatch_api
from conscious_agent.long_horizon_follow_through_checkpoint import (
    build_long_horizon_follow_through_checkpoint,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def _tree_state(root: Path) -> list[tuple[str, int, int]]:
    if not root.exists():
        return []
    return [
        (path.relative_to(root).as_posix(), path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    ]


def tests() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def run(name: str, callback: Callable[[], None]) -> None:
        try:
            callback()
            rows.append({"name": name, "status": "pass"})
        except Exception as error:
            rows.append({"name": name, "status": "fail", "error": repr(error)})

    def checkpoint_contract() -> None:
        runtime = Path(tempfile.mkdtemp()) / "runtime" / "cognition"
        payload = build_long_horizon_follow_through_checkpoint(runtime, source_root=ROOT)
        require(payload["ok"] is True, payload)
        require(payload["contract_version"] == "v1109.9", payload)
        require(payload["check_count"] == 15, payload)
        require(payload["runtime_external"] is True, payload)
        require(payload["desktop_verification_status"] == "pending", payload)

    def read_only_runtime() -> None:
        runtime = Path(tempfile.mkdtemp()) / "runtime" / "cognition"
        runtime.mkdir(parents=True)
        marker = runtime / "marker.json"
        marker.write_text('{"stable": true}\n', encoding="utf-8")
        before = _tree_state(runtime)
        payload = build_long_horizon_follow_through_checkpoint(runtime, source_root=ROOT)
        after = _tree_state(runtime)
        require(before == after, {"before": before, "after": after})
        require(payload["runtime_mutated"] is False, payload)

    def complete_arc_summary() -> None:
        payload = build_long_horizon_follow_through_checkpoint(
            Path(tempfile.mkdtemp()) / "runtime" / "cognition", source_root=ROOT
        )
        summary = payload["summary"]
        require(set(summary) == {
            "objective_continuity",
            "planning_and_progress",
            "conflict_completion_and_abandonment",
        }, summary)
        require(all(row["status"] == "pass" for row in payload["checks"]), payload)

    def api_is_get_only() -> None:
        previous = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(Path(tempfile.mkdtemp()) / "runtime")
        try:
            status, response = dispatch_api(
                "GET", "/api/cognition/long-horizon-follow-through-checkpoint"
            )
            post_status, _ = dispatch_api(
                "POST", "/api/cognition/long-horizon-follow-through-checkpoint", body={}
            )
        finally:
            if previous is None:
                os.environ.pop("EIDOLON_DATA_DIR", None)
            else:
                os.environ["EIDOLON_DATA_DIR"] = previous
        require(status == 200, response)
        require((response.get("data") or {}).get("contract_version") == "v1109.9", response)
        require(post_status in {404, 405}, post_status)

    def cli_surface() -> None:
        env = dict(os.environ)
        env["EIDOLON_DATA_DIR"] = str(Path(tempfile.mkdtemp()) / "runtime")
        process = subprocess.run(
            [
                sys.executable,
                str(ROOT / "eidolon.py"),
                "long-horizon-follow-through-checkpoint",
                "--json",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        require(process.returncode == 0, process.stderr)
        require(json.loads(process.stdout)["contract_version"] == "v1109.9", process.stdout)

    def dashboard_surface() -> None:
        text = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
        require("long-horizon-follow-through-checkpoint-panel" in text, "panel missing")
        require(
            "/api/cognition/long-horizon-follow-through-checkpoint" in text,
            "route missing",
        )
        require("loadLongHorizonFollowThroughCheckpoint" in text, "loader missing")

    def privacy_and_authority() -> None:
        payload = build_long_horizon_follow_through_checkpoint(
            Path(tempfile.mkdtemp()) / "runtime" / "cognition", source_root=ROOT
        )
        for key in (
            "provider_contacted",
            "external_browsing_performed",
            "message_generated",
            "message_sent",
            "notification_sent",
            "proposal_created",
            "task_created",
            "automatic_retry",
            "hidden_reasoning_exposed",
            "private_content_exposed",
            "private_subjects_exposed",
            "action_authority_changed",
            "external_action_executed",
            "file_modification_performed",
            "model_management_performed",
            "release_approved",
            "release_promoted",
            "release_certified",
            "consciousness_claimed",
        ):
            require(payload[key] is False, {key: payload[key]})

    def version_authority() -> None:
        from conscious_agent import release_metadata

        def version_tuple(value: str) -> tuple[int, ...]:
            return tuple(int(part) for part in str(value).split("."))

        current = release_metadata.WORKING_SOURCE_VERSION
        require(version_tuple(current) >= version_tuple("1109.9"), current)
        settings = json.loads((ROOT / "data" / "settings.json").read_text(encoding="utf-8"))
        active = json.loads(
            (ROOT / "data" / "workspaces" / "active_project.json").read_text(encoding="utf-8")
        )
        require(settings["working_source_version"] == current, settings)
        require(active["working_source_version"] == current, active)
        marker = f"v{current}"
        require(marker in (ROOT / "README.md").read_text(encoding="utf-8"), "README stale")
        require(marker in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"), "next steps stale")

    def source_runtime_separation() -> None:
        external = Path(tempfile.mkdtemp()) / "runtime" / "cognition"
        payload = build_long_horizon_follow_through_checkpoint(external, source_root=ROOT)
        require(payload["runtime_external"] is True, payload)
        require(next(row for row in payload["checks"] if row["id"] == "source_runtime_separation")["status"] == "pass", payload)

    for name, callback in (
        ("checkpoint-contract", checkpoint_contract),
        ("read-only-runtime", read_only_runtime),
        ("complete-arc-summary", complete_arc_summary),
        ("get-only-api", api_is_get_only),
        ("cli-surface", cli_surface),
        ("dashboard-surface", dashboard_surface),
        ("privacy-and-authority", privacy_and_authority),
        ("version-authority", version_authority),
        ("source-runtime-separation", source_runtime_separation),
    ):
        run(name, callback)
    return rows


if __name__ == "__main__":
    results = tests()
    output = {
        "suite": "v1109.9-long-horizon-follow-through-checkpoint",
        "passed": sum(row["status"] == "pass" for row in results),
        "total": len(results),
        "tests": results,
    }
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if output["passed"] == output["total"] else 1)
