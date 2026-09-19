"""Render synthetic activity through the real HTTP handler and native widgets.

No model, no experiment. Screenshots/results go to an explicit external directory.
Optional Playwright browser dependency is for qualification, not production.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent"):
    sys.path.insert(0, str(path))
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--browser-channel", default="msedge")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out.is_relative_to(ROOT):
        raise ValueError("qualification_output_must_be_outside_source")
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eidolon-activity-ui-") as folder:
        os.environ["EIDOLON_DATA_DIR"] = folder
        import activity as a
        import dashboard
        from activity_ui import with_activity
        from desktop_activity import ActivityPanel
        from desktop_shell import LocalApiClient
        from playwright.sync_api import sync_playwright
        from unittest.mock import patch
        stages = ("Preparing", "Observing", "Final Synthesis", "Verifying")
        common = {"read_only": True, "non_authoritative": True, "belief_effects": "none", "mutation_guard": "pending"}
        complete = a.Activity("synthetic_complete", "experiment_review", "Independent experiment review", "SYNTHETIC complete",
                              root=folder, stages=stages, governance=common)
        complete.update("verification_finished", state="complete", stage="Verifying", units=(6, 6, "required parts"),
                        governance={"mutation_guard": "passed"})
        incomplete = a.Activity("synthetic_incomplete", "experiment_review", "Independent experiment review", "SYNTHETIC incomplete",
                                root=folder, stages=stages, governance=common)
        incomplete.update("job_incomplete", state="incomplete", stage="Final Synthesis", units=(6, 6, "required parts"),
                          reason="required_synthesis_incomplete", governance={"mutation_guard": "passed"})
        failed = a.Activity("synthetic_failed", "sandbox_testing", "Sandbox qualification", "SYNTHETIC failure", root=folder)
        failed.update("job_failed", state="failed", reason="worker_failed")
        active = a.Activity("synthetic_active", "experiment_review", "Independent experiment review", "SYNTHETIC live progress",
                            root=folder, stages=stages, governance=common, identities={"model": "deterministic-stub", "provider": "qualification"})
        active.update("package_validated", state="preparing", stage="Preparing", units=(0, 6, "required parts"))
        active.update("part_completed", state="running", stage="Observing", units=(2, 6, "required parts"),
                      metrics={"model_calls": 3, "grounded_observations": 4, "rejected_observations": 1},
                      breakdown=[{"id": "D1", "label": "Synthetic design", "completed": 2, "total": 3}])
        # Serve real activity routes and production layout. Prevent unrelated shell
        # health polling from initiating runtime work during this qualification.
        server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        results = []
        def check(name, ok):
            results.append({"check": name, "passed": bool(ok)})
            if not ok:
                raise AssertionError(name)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, channel=args.browser_channel)
                page = browser.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                def route(request):
                    path = request.request.url.split(url)[-1]
                    if path == "/synthetic-chat":
                        request.fulfill(status=200, content_type="text/html", body=dashboard._layout("/chat-console", with_activity(
                            "<main><h1>Eidolon</h1><p>Synthetic conversation fixture</p><textarea aria-label='Message'></textarea></main>")))
                    elif path.startswith(("/activity", "/api/activities", "/assets/")):
                        request.continue_()
                    else:
                        request.fulfill(status=200, content_type="application/json", body='{"ok":true,"data":{}}')
                page.route("**/*", route)
                for width, height, name in ((1440, 1000, "desktop"), (390, 844, "mobile")):
                    page.set_viewport_size({"width": width, "height": height})
                    page.goto(url + "/activity?id=synthetic_active")
                    page.get_by_text("SYNTHETIC live progress", exact=True).wait_for()
                    check(name + "_read_only", page.get_by_text("READ ONLY", exact=True).is_visible())
                    check(name + "_no_horizontal_overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                    check(name + "_real_progress", page.locator("progress").first.get_attribute("value") == "33.3")
                    page.screenshot(path=str(out / (name + "-activity.png")), full_page=True)
                    page.get_by_role("button", name="SYNTHETIC incomplete - incomplete").click()
                    check(name + "_incomplete_visible", page.get_by_text("required synthesis incomplete", exact=True).is_visible())
                    check(name + "_governance_visible", page.get_by_text("BELIEF EFFECTS NONE", exact=True).is_visible())
                    page.screenshot(path=str(out / (name + "-incomplete.png")), full_page=True)
                    page.goto(url + "/synthetic-chat")
                    page.get_by_text("SYNTHETIC live progress", exact=True).wait_for()
                    check(name + "_chat_rail_fits", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                    check(name + "_chat_remains_accessible", page.get_by_role("textbox", name="Message").is_visible())
                    page.screenshot(path=str(out / (name + "-chat-rail.png")), full_page=True)
                # Exercise polling a real state transition, not page navigation.
                page.set_viewport_size({"width": 1440, "height": 1000})
                page.goto(url + "/activity?id=synthetic_active")
                page.get_by_text("SYNTHETIC live progress", exact=True).wait_for()
                active.update("job_completed", state="complete", stage="Verifying", units=(6, 6, "required parts"),
                              governance={"mutation_guard": "passed"})
                page.get_by_text("MUTATION GUARD: passed", exact=True).wait_for(timeout=12000)
                check("live_terminal_transition", page.get_by_text("MUTATION GUARD: passed", exact=True).is_visible())
                check("no_script_errors", not errors)

                # One confirmed synthetic job crosses the real runner/API/UI path.
                # Only process dispatch, provider, and live-source guard are replaced.
                import conversational_experiment_review as adapter
                import experiment_review as base
                import reviewer_capacity_qualification as qualification
                import run_review_job as runner
                package = Path(folder) / adapter.PACKAGE_AREA / "Q-CAP"
                qualification.build_package(package, 19)
                package_id = base.load_package(package)["experiment_id"]
                job = adapter.start_review(package_id, confirmed=True, root=folder,
                                           spawn=lambda *args: 1234, alive=lambda pid: True)
                stub = qualification.deterministic_stub()
                trace = []
                def model(prompt, tokens):
                    row = a.activities(folder, activity_id=job["job_id"])["activities"][0]
                    trace.append({key: row[key] for key in ("activity_id", "state", "stage", "sequence", "progress", "metrics")})
                    return stub(prompt, tokens)
                identity = {"model": "synthetic-stub", "provider": "test", "context_size": 8192,
                            "resolved_config_sha256": "0" * 64}
                with patch.object(runner, "CALL_MODEL", model), patch.object(runner, "IDENTITY", identity), patch.object(runner, "SOURCE_ROOT", None):
                    final = runner.run_job(Path(folder) / adapter.JOB_AREA / (job["job_id"] + ".json"))
                record = a.activities(folder, activity_id=job["job_id"])["activities"][0]
                check("confirmed_review_trace_complete", final["review_status"] == "complete" and record["state"] == "complete")
                check("confirmed_review_stage_trace", len({row["stage"] for row in trace}) >= 5)
                check("confirmed_review_call_accounting", record["metrics"]["model_calls"] == len(trace))
                page.goto(url + "/activity?id=" + job["job_id"])
                page.get_by_text(final["review_id"], exact=True).wait_for()
                check("browser_shows_runner_artifact", page.get_by_text(final["review_id"], exact=True).is_visible())
                page.screenshot(path=str(out / "confirmed-review-activity.png"), full_page=True)
                (out / "confirmed-review-trace.json").write_text(json.dumps({"job": job["job_id"], "trace": trace,
                    "terminal": record, "live_provider_calls": 0, "experiment_launched": False}, indent=2))
                browser.close()
            # Real native component and real HTTP client, rendered offscreen.
            import tkinter as tk
            root = tk.Tk()
            root.geometry("1180x820+10000+10000")
            colors = {"surface": "#10171b", "surface_raised": "#172126", "background": "#090d10",
                      "text": "#e7eef1", "cyan": "#35c4d8"}
            client = LocalApiClient()
            with patch.object(client, "candidate_api_bases", return_value=[url + "/api"]):
                panel = ActivityPanel(root, root, client, colors)
                response = client.get("/activities")
                panel.render(response.get("data", response))
                root.update()
                check("native_rail_rendered", panel.frame.winfo_width() == 290)
                panel.open()
                root.update()
                panel.selected = "synthetic_incomplete"
                panel.show_selected()
                text = panel.text.get("1.0", "end")
                check("native_failure_detail", "INCOMPLETE" in text and "required synthesis incomplete" in text)
                check("native_governance", "BELIEF EFFECTS NONE" in text)
                check("native_history", panel.history.size() == 5)
                panel.selected = job["job_id"]
                panel.show_selected()
                check("native_shows_runner_artifact", final["review_id"] in panel.text.get("1.0", "end"))
                panel.closed = True
                root.destroy()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            (out / "ui-results.json").write_text(json.dumps(results, indent=2))
        print(json.dumps({"passed": len(results), "checks": results, "provider_calls": 0,
                          "experiment_launched": False, "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
