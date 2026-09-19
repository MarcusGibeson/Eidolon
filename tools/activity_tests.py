"""Deterministic operational observability qualification. No live model or experiment."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    sys.path.insert(0, str(path))
sys.dont_write_bytecode = True
RUNTIME = tempfile.TemporaryDirectory(prefix="eidolon-activity-tests-")
os.environ["EIDOLON_DATA_DIR"] = RUNTIME.name
import activity as a
import experiment_review as base
import experiment_review_hierarchical as hier
import reviewer_capacity_qualification as q
from review_activity import ReviewActivity
from desktop_activity import detail_text, summary_lines


def tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(root).rglob("*") if p.is_file()}


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="activity-unit-")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def new(self, name="a", **kw):
        return a.Activity(name, "planning", "Planning", "Synthetic target", root=self.root, **kw)

    def test_creation_transitions_progress_and_terminal(self):
        act = self.new(stages=("Preparing", "Running"))
        self.assertEqual(act.record["state"], "queued")
        act.update("started", state="preparing", stage="Preparing")
        act.update("units", state="running", stage="Running", units=(2, 4, "cases"))
        self.assertEqual(act.record["progress"]["percent"], 50)
        self.assertEqual(act.record["stages"][0]["state"], "complete")
        act.update("waiting", state="blocked", reason="operator_input_required")
        act.update("resumed", state="running", units=(3, None, "cases"))
        self.assertIsNone(act.record["progress"]["percent"])
        act.update("done", state="complete", units=(4, 4, "cases"))
        with self.assertRaises(ValueError):
            act.update("not_allowed", state="running")
        self.assertTrue(a.activities(self.root)["activities"][0]["terminal"])
        with self.assertRaises(FileExistsError):
            self.new()

    def test_all_terminal_states_and_elapsed(self):
        for state in a.TERMINAL:
            act = self.new(state, clock=lambda: "2026-01-01T00:00:00Z")
            act.clock = lambda: "2026-01-01T00:02:03Z"
            result = act.update("finished", state=state)
            self.assertEqual(result["elapsed_seconds"], 123)
            self.assertEqual(result["state"], state)
            self.assertEqual(a.project(act.record, "2027-01-01T00:00:00Z")["elapsed_seconds"], 123)
        self.assertEqual({r["state"] for r in a.activities(self.root)["activities"]}, a.TERMINAL)

    def test_validation_read_only_and_path_containment(self):
        before = tree(self.root)
        self.assertEqual(a.activities(self.root)["activities"], [])
        self.assertEqual(before, tree(self.root))
        for token in ("../secret", "a/b", "C:\\file", ".."):
            with self.assertRaises(ValueError):
                a.activities(self.root, activity_id=token)
        for args in ((-1, 4), (5, 4), (True, 1)):
            with self.assertRaises(ValueError):
                a.progress(*args)

    def test_concurrent_reads_order_and_event_bound(self):
        act = self.new()
        def writer():
            for i in range(35):
                act.update("unit_completed", state="running", units=(i, 35, "units"))
        def reader():
            for _ in range(35):
                row = a.activities(self.root)["activities"][0]
                self.assertEqual(row["sequence"], len(row["events"]))
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(writer), *[pool.submit(reader) for _ in range(3)]]
            for future in futures:
                future.result()
        before = tree(self.root)
        for _ in range(10):
            a.activities(self.root)
        self.assertEqual(before, tree(self.root))
        with patch.object(a, "MAX_EVENTS", 3):
            act.update("window")
        self.assertEqual(len(act.record["events"]), 3)
        self.assertEqual(act.record["events_omitted"], act.record["sequence"] - 3)

    def test_stale_and_historical_reconciliation_without_writes(self):
        act = self.new("job_old", clock=lambda: "2020-01-01T00:00:00Z")
        act.update("started", state="running")
        before = tree(self.root)
        self.assertEqual(a.activities(self.root)["current"]["state"], "blocked")
        self.assertEqual(before, tree(self.root))
        jobs = self.root / "research_jobs"
        jobs.mkdir()
        record = {"job_id": "job_old", "status": "completed", "review_status": "incomplete",
                  "started": "2020-01-01T00:00:00Z", "finished": "2020-01-01T00:01:00Z"}
        (jobs / "job_old.json").write_text(json.dumps(record))
        before = tree(self.root)
        self.assertEqual(a.activities(self.root)["activities"][0]["state"], "incomplete")
        self.assertIsNone(a.activities(self.root)["current"])
        self.assertEqual(before, tree(self.root))

    def test_telemetry_write_failure_does_not_fail_work(self):
        act = self.new()
        with patch.object(a, "write_text_atomic", side_effect=OSError("private detail")):
            act.update("finished", state="complete")
        self.assertIn("activity_persistence_failed", act.record["warnings"])
        self.assertNotIn("private detail", json.dumps(act.record))

    def test_both_presentations_keep_critical_state(self):
        act = self.new()
        row = act.update("failed", state="incomplete", reason="missing_required_parts",
                         governance={"belief_effects": "none", "non_authoritative": True, "mutation_guard": "passed"})
        self.assertIn("INCOMPLETE", detail_text(row))
        self.assertIn("BELIEF EFFECTS NONE", "\n".join(summary_lines(row)))
        self.assertIn("missing required parts", detail_text(row))
        from activity_ui import activity_surface
        self.assertIn("data-detail='true'", activity_surface(detail=True))
        js = (ROOT / "conscious_agent/static/activity.js").read_text()
        self.assertIn("a.reason", js)
        self.assertIn("g.belief_effects", js)
        self.assertNotIn("innerHTML", js)
        self.assertNotIn(".title =", js)

    def test_source_inspection_accepts_python_bom_without_skipping_ast(self):
        import release_parity_campaign_binding_checkpoint_v2729_9_2 as gate
        agent = self.root / "conscious_agent"
        agent.mkdir()
        (agent / "bom.py").write_bytes(b"\xef\xbb\xbffrom conscious_agent import forbidden_identity\n")
        for name in ("setup.sh", "run_eidolon.sh"):
            (self.root / name).touch(mode=0o755)
        with patch.object(gate, "package_privacy_summary_for_root", return_value={"ok": True, "source_only": True}), \
             patch.object(gate, "checkpoint_registry_manifest", return_value={"ok": True}):
            result = gate.build_checkpoint(self.root)
        self.assertFalse(result["checks"]["single_internal_import_identity"])

    def test_history_limit_and_older_direct_lookup(self):
        for i in range(4):
            self.new("history" + str(i)).update("complete", state="complete")
        self.assertEqual(len(a.activities(self.root, limit=2)["activities"]), 2)
        before = tree(self.root)
        self.assertEqual(a.activities(self.root, activity_id="history0")["activities"][0]["state"], "complete")
        self.assertEqual(before, tree(self.root))


class ReviewIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="activity-review-")
        cls.root = Path(cls.temp.name)
        cls.pkg = cls.root / "package"
        q.build_package(cls.pkg, 19)
        cls.ident = {"model": "synthetic-stub", "provider": "test", "context_size": 8192,
                     "resolved_config_sha256": "0" * 64}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_review(self, name, telemetry=True, fail=False, broken_observer=False):
        runtime = self.root / name
        runtime.mkdir()
        job = {"job_id": "job_" + name, "package_id": "Q-CAP", "reviewer_contract": hier.CONTRACT_VERSION}
        observer = ReviewActivity(job, self.root / (name + "-telemetry")) if telemetry else None
        calls, snapshots = [], []
        stub = q.deterministic_stub()
        def model(prompt, tokens):
            calls.append((prompt, tokens))
            if observer:
                snapshots.append(a.activities(observer.activity.root)["activities"][0])
            return ("not json", {}) if fail else stub(prompt, tokens)
        original = base._ask
        kw = dict(call_model=model, runtime_root_path=runtime, identity=self.ident, clock=lambda: "2026-01-01T00:00:00Z")
        if observer:
            with observer.observe(hier):
                if broken_observer:
                    with patch.object(observer.activity, "update", side_effect=OSError("observer failure")), patch("logging.Logger.warning"):
                        result = hier.review_experiment(self.pkg, **kw)
                else:
                    result = hier.review_experiment(self.pkg, **kw)
            observer.finish({**job, "status": "completed", "review_id": result["review_id"]}, result)
            self.assertIs(original, base._ask)
        else:
            result = hier.review_experiment(self.pkg, **kw)
        return result, calls, snapshots, observer

    def test_review_is_identical_and_progress_is_real(self):
        before = tree(self.pkg)
        off, off_calls, _, _ = self.run_review("off", telemetry=False)
        on, on_calls, live, obs = self.run_review("on")
        self.assertEqual(off_calls, on_calls)
        for key in ("status", "review", "coverage", "hierarchy", "grounded_observations", "rejected_observations",
                    "ledger", "authority", "runtime_accounting", "non_authoritative"):
            self.assertEqual(off[key], on[key], key)
        self.assertEqual(before, tree(self.pkg))
        self.assertTrue(on["mutation_guard"]["passed"])
        record = a.activities(obs.activity.root)["activities"][0]
        self.assertEqual(record["state"], "complete")
        self.assertEqual(record["metrics"]["model_calls"], len(on_calls))
        self.assertEqual(record["metrics"]["grounded_observations"], len(on["grounded_observations"]))
        self.assertEqual(record["metrics"]["rejected_observations"], len(on["rejected_observations"]))
        self.assertEqual(record["progress"]["completed"], 19)
        self.assertEqual(record["governance"]["mutation_guard"], "passed")
        self.assertEqual(record["governance"]["belief_effects"], "none")
        self.assertTrue(record["governance"]["non_authoritative"])
        self.assertGreater(len({r["stage"] for r in live}), 4)
        self.assertEqual(sum(r["completed"] for r in record["breakdown"]), 19)
        # Persist synthetic smoke evidence outside source only when explicitly requested.
        target = os.environ.get("EIDOLON_ACTIVITY_SMOKE_OUTPUT")
        if target:
            Path(target).mkdir(parents=True, exist_ok=True)
            (Path(target) / "complete.json").write_text(json.dumps(record, indent=2))

    def test_incomplete_and_retries_are_not_software_failure(self):
        result, calls, live, obs = self.run_review("incomplete", fail=True)
        record = a.activities(obs.activity.root)["activities"][0]
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(record["state"], "incomplete")
        self.assertGreater(record["metrics"]["retries"], 0)
        self.assertIn("retry_started", {e["event"] for e in record["events"]})
        self.assertEqual(record["metrics"]["model_calls"], len(calls))
        self.assertEqual(record["progress"]["completed"], 0)
        self.assertIn("incomplete", {r["state"] for r in record["stages"]})
        target = os.environ.get("EIDOLON_ACTIVITY_SMOKE_OUTPUT")
        if target:
            (Path(target) / "incomplete.json").write_text(json.dumps(record, indent=2))

    def test_observer_failure_cannot_change_review(self):
        off, calls, _, _ = self.run_review("control", telemetry=False)
        on, on_calls, _, _ = self.run_review("broken", broken_observer=True)
        self.assertEqual(calls, on_calls)
        self.assertEqual(off["review"], on["review"])
        self.assertEqual(off["coverage"], on["coverage"])

    def test_projection_faults_and_provider_exception_are_inert(self):
        from review_activity import observing_review
        job = {"job_id": "job_fault", "package_id": "synthetic"}
        failure = RuntimeError("private provider detail")
        def provider(prompt, tokens):
            raise failure
        def ask(model, prompt, tokens, accept, ledger, stage, **kwargs):
            return model(prompt, tokens)
        original = base._ask
        with patch.object(base, "_ask", ask):
            with observing_review(job, self.root / "fault-telemetry", hier) as obs:
                # A broken display-stage value must not block the provider invocation.
                with self.assertRaises(RuntimeError) as caught:
                    base._ask(provider, "private prompt", 10, None, [], "observe:")
                self.assertIs(caught.exception, failure)
                self.assertEqual(obs.counts["model_calls"], 1)
                self.assertEqual(obs.counts["responses_received"], 0)
                with patch.object(obs, "_finish", side_effect=ValueError("private projection detail")):
                    obs.finish({"status": "completed"})
                obs.finish({"status": "failed"})
                stored = json.dumps(a.activities(obs.activity.root))
                self.assertNotIn("private prompt", stored)
                self.assertNotIn("private provider detail", stored)
                self.assertNotIn("private projection detail", stored)
                self.assertEqual(obs.activity.record["state"], "failed")
            self.assertIs(base._ask, ask)
        self.assertIs(base._ask, original)

    def test_existing_runner_path_and_confirmations(self):
        import conversational_experiment_review as adapter
        import run_review_job as runner
        import shutil
        root = self.root / "operator"
        pkg = root / adapter.PACKAGE_AREA / "Q-CAP"
        shutil.copytree(self.pkg, pkg)
        package_id = base.load_package(pkg)["experiment_id"]
        with self.assertRaises(PermissionError):
            adapter.start_review(package_id, confirmed=False, root=root)
        self.assertFalse((root / a.AREA).exists())
        job = adapter.start_review(package_id, confirmed=True, root=root, spawn=lambda *args: 1234, alive=lambda pid: True)
        source = self.root / "source"
        # A real source tree is guarded by existing suites; no live repo mutation here.
        with patch.object(runner, "CALL_MODEL", q.deterministic_stub()), patch.object(runner, "IDENTITY", self.ident), patch.object(runner, "SOURCE_ROOT", None):
            final = runner.run_job(root / adapter.JOB_AREA / (job["job_id"] + ".json"))
        self.assertEqual(final["status"], "completed")
        self.assertEqual(final["review_status"], "complete")
        data = a.activities(root)
        self.assertEqual(data["activities"][0]["state"], "complete")
        self.assertEqual(data["activities"][0]["identities"]["review_id"], final["review_id"])
        before = tree(root)
        with patch.dict(os.environ, {"EIDOLON_DATA_DIR": str(root)}):
            self.assertEqual(a.activities(root)["activities"][0]["contract"], "activity.v1")
        self.assertEqual(before, tree(root))


class ApiIntegration(unittest.TestCase):
    def test_real_endpoints_and_confirmation_boundary(self):
        import api_server
        import dashboard
        with tempfile.TemporaryDirectory(prefix="activity-http-") as folder, patch.object(a, "_root", return_value=Path(folder)):
            act = a.Activity("http", "repair_preparation", "Synthetic operation", "Fixture", root=folder)
            act.update("started", state="running", units=(1, 3, "checks"))
            status, payload = api_server.handle_api_get("/api/activities")
            self.assertEqual(status, 200)
            self.assertEqual(payload["data"]["contract"], "activity.v1")
            server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
            before = tree(folder)
            try:
                for path in ("/api/activities", "/api/activities/http"):
                    with urllib.request.urlopen(url + path, timeout=10) as response:
                        self.assertEqual(response.headers["Cache-Control"], "no-store")
                        data = json.load(response)
                        self.assertEqual(data["activities"][0]["state"], "running")
                with urllib.request.urlopen(url + "/assets/activity.js") as response:
                    self.assertIn(b"activity.v1", response.read())
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(urllib.request.Request(url + "/api/activities", data=b"{}",
                                                                  headers={"Origin": "https://hostile.example", "Content-Type": "application/json"}))
                self.assertEqual(context.exception.code, 403)
                context.exception.close()
                self.assertEqual(before, tree(folder))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
