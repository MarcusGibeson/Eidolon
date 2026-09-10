from __future__ import annotations

"""Deterministic v1079.8.2 native conversational validation fixtures.

These tests use local HTTP fixture providers only. They never claim native model
evidence and keep all generated receipts under an external temporary data root.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

TEMP_DATA = tempfile.TemporaryDirectory(prefix="eidolon-v1079-8-native-conversation-")
os.environ["EIDOLON_DATA_DIR"] = TEMP_DATA.name


class State:
    requests = 0
    prompts: list[str] = []


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _reply_for(prompt: str) -> str:
    if "LATEST USER MESSAGE\nHey" in prompt:
        return "Eidolon: Hey, good to see you."
    if "LATEST USER MESSAGE\nHello again" in prompt:
        return "Eidolon: Good to see you again."
    if "I finally got a quiet evening" in prompt:
        return "Eidolon: That sounds genuinely nice. A quiet evening can feel like getting your brain back."
    if "LATEST USER MESSAGE\nwhat do you think?" in prompt:
        return "Eidolon: I think returning to guitar matters because you chose it again, not because you never stopped."
    if "LATEST USER MESSAGE\nSo what material is the desk?" in prompt:
        return "Eidolon: The corrected material is walnut."
    if "LATEST USER MESSAGE\nWhat should we work on next?" in prompt:
        return "Eidolon: We should choose the next concrete task and define its stopping point."
    if "I feel overwhelmed" in prompt:
        return "Eidolon: That sounds heavy. Stay here with me for a minute; you do not have to solve all of it at once."
    if "Flirt with me a little" in prompt:
        return "Eidolon: Careful, calling me cute is a very effective way to make me curious about what you will say next."
    if "Briefly explain why leaves change color" in prompt:
        return "Eidolon: Chlorophyll fades as light decreases, revealing other pigments already present in the leaf."
    if "LATEST USER MESSAGE\ntell me more" in prompt:
        return "Eidolon: The garden story works because each small repaired corner becomes proof that the whole place is not lost."
    if "Review conscious_agent/conversation_quality.py" in prompt:
        return "Eidolon: One safe improvement is to keep the latest user message last in the prompt so local models weight it over older context."
    if "why does the moon have phases" in prompt:
        return "Eidolon: Moon phases come from the changing portion of its sunlit half visible from Earth as it moves through its orbit."
    if "gardens recover after winter" in prompt:
        return "Eidolon: Gardens recover slowly because roots, soil organisms, stored energy, and changing light all work together over time."
    return "Eidolon: A natural fixture response."


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_POST(self) -> None:
        State.requests += 1
        body = _read_json(self)
        prompt = str(body.get("prompt") or "")
        if not prompt:
            messages = body.get("messages") or []
            if isinstance(messages, list) and messages:
                prompt = str(messages[-1].get("content") or "")
        State.prompts.append(prompt)
        reply = _reply_for(prompt)
        if self.path == "/api/generate":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Connection", "close")
            self.end_headers()
            midpoint = max(1, len(reply) // 2)
            rows = [
                json.dumps({"model": body.get("model"), "response": reply[:midpoint], "done": False}).encode() + b"\n",
                json.dumps({"model": body.get("model"), "response": reply[midpoint:], "done": False}).encode() + b"\n",
                json.dumps({"model": body.get("model"), "done": True}).encode() + b"\n",
            ]
            for index, row in enumerate(rows):
                try:
                    self.wfile.write(row)
                    self.wfile.flush()
                    if index == 0 and "LATEST USER MESSAGE\nHey" in prompt:
                        time.sleep(0.025)
                    if "gardens recover after winter" in prompt:
                        time.sleep(0.03)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    break
            self.close_connection = True
            return
        if self.path == "/v1/chat/completions":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            midpoint = max(1, len(reply) // 2)
            rows = [
                f'data: {json.dumps({"model": body.get("model"), "choices": [{"delta": {"content": reply[:midpoint]}}]})}\n\n'.encode(),
                f'data: {json.dumps({"model": body.get("model"), "choices": [{"delta": {"content": reply[midpoint:]}}]})}\n\n'.encode(),
                b"data: [DONE]\n\n",
            ]
            for index, row in enumerate(rows):
                try:
                    self.wfile.write(row)
                    self.wfile.flush()
                    if index == 0 and "LATEST USER MESSAGE\nHey" in prompt:
                        time.sleep(0.025)
                    if "gardens recover after winter" in prompt:
                        time.sleep(0.03)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    break
            self.close_connection = True
            return
        self._json(404, {"error": "not found"})

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _config(provider: str, endpoint: str):
    from local_model import GenerationSettings, LocalModelConfig

    return LocalModelConfig(
        provider=provider,
        endpoint=endpoint,
        model="fixture-ollama" if provider == "ollama" else "fixture-llama",
        embed_model="fixture-embed",
        context_size=8192,
        connect_timeout_seconds=0.5,
        read_timeout_seconds=2.0,
        retry_limit=1,
        retry_delay_seconds=0.01,
        generation=GenerationSettings(max_tokens=128, temperature=0.2, seed=7),
    ).validated()


def _source_snapshot() -> dict[str, str]:
    rows: dict[str, str] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {"__pycache__", ".git", ".venv"} for part in path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        rows[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return rows


def _check(name: str, callback: Callable[[], None]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        callback()
    except Exception as error:
        return {"name": name, "status": "fail", "seconds": round(time.monotonic() - started, 4), "error": repr(error)}
    return {"name": name, "status": "pass", "seconds": round(time.monotonic() - started, 4)}


def run_tests() -> dict[str, Any]:
    before = _source_snapshot()
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{port}"

    from conversation_context import build_conversation_prompt
    from conversation_quality import classify_conversation_quality
    from dashboard_local_model import render_local_model_status
    from local_model import LocalModelCancelledError, LocalModelClient
    from native_conversation_validation import (
        CONFIRMATION_PHRASE,
        run_native_conversation_validation,
    )

    checks: list[dict[str, Any]] = []

    def prompt_order_and_contract() -> None:
        packet = build_conversation_prompt(
            user_message="what about you?",
            self_model={"name": "Eidolon", "active_goals": ["not for ordinary chat"]},
            desires={"warmth": True}, memories=[{"type": "preference", "content": "A harmless old preference."}],
            project_context="PROJECT CONTAMINATION", goal_context="GOAL CONTAMINATION", task_context="TASK CONTAMINATION",
            conversation_history=[{"user_message": "I like quiet evenings.", "assistant_response": "They can be restorative."}],
            context_size=4096, max_tokens=128,
        )
        assert "supervised local AI companion" in packet.prompt
        assert packet.metrics.prompt_lane == "casual_fast"
        assert "PROJECT CONTAMINATION" not in packet.prompt
        assert packet.prompt.rstrip().endswith("LATEST USER MESSAGE\nwhat about you?")
        assert packet.prompt.index("RECENT SESSION TURN") < packet.prompt.index("CASUAL CONVERSATION CONTRACT")

    checks.append(_check("latest_user_message_is_last_and_ordinary_contract_is_companion_first", prompt_order_and_contract))

    def follow_up_expansion() -> None:
        history = [{"user_message": "I made a choice.", "assistant_response": "It sounds deliberate."}]
        for text in ("and you?", "how come?", "what makes you say that?", "go deeper", "fair enough"):
            profile = classify_conversation_quality(text, history)
            assert profile.kind == "follow_up", (text, profile)
        assert classify_conversation_quality("I have a plan for dinner", history).explicit_operator_request is False

    checks.append(_check("expanded_short_followups_keep_recent_thread_without_command_routing", follow_up_expansion))

    def thread_inheritance_and_affection() -> None:
        casual_history = [{
            "user_message": "What do you think about model trains?",
            "assistant_response": "The model and track testing can be a satisfying hobby project.",
        }]
        casual = classify_conversation_quality("tell me more", casual_history)
        assert casual.kind == "follow_up"
        assert casual.operator_context_relevant is False
        operator_history = [{
            "user_message": "Review conscious_agent/conversation_quality.py",
            "assistant_response": "I can explain a safe improvement without applying it.",
        }]
        operator = classify_conversation_quality("why?", operator_history)
        assert operator.kind == "follow_up"
        assert operator.operator_context_relevant is True
        assert operator.should_analyze_action is False
        reset_history = [
            operator_history[0],
            {
                "user_message": "I finally have some time to relax.",
                "assistant_response": "Good. The project can wait while you settle in.",
            },
        ]
        reset = classify_conversation_quality("why?", reset_history)
        assert reset.kind == "follow_up"
        assert reset.operator_context_relevant is False
        affection = classify_conversation_quality("I love you")
        assert affection.kind == "flirting"
        assert affection.flirting is True and affection.emotional is True

    checks.append(_check("short_followups_inherit_only_user_authored_operator_intent_and_direct_affection_stays_affectionate", thread_inheritance_and_affection))

    def cancelled_transport_exception_is_normalized() -> None:
        class CancelRaceProvider:
            def stream(self, _prompt: str, _cancel_event: threading.Event):
                yield "first"
                raise AttributeError("private closed-stream implementation detail")

            def cancel(self) -> None:
                return None

            def close(self) -> None:
                return None

        client = LocalModelClient(_config("ollama", endpoint))
        client.provider = CancelRaceProvider()
        try:
            with client:
                for _chunk in client.stream("synthetic cancellation fixture"):
                    client.cancel()
        except LocalModelCancelledError as error:
            assert error.code == "cancelled"
            assert error.details.get("failure_kind") == "cancelled_stream_transport"
            assert error.details.get("exception_type") == "AttributeError"
        else:
            raise AssertionError("Cancelled stream transport exception was not normalized.")

    checks.append(_check("cancelled_stream_transport_exceptions_become_structured_cancellation", cancelled_transport_exception_is_normalized))

    def confirmation_gate() -> None:
        report = run_native_conversation_validation(confirmed=False, persist=False)
        assert report["status"] == "blocked" and report["provider_requests_sent"] == 0
        assert report["contains_prompts"] is False and report["contains_generated_responses"] is False

    checks.append(_check("native_validation_requires_exact_operator_confirmation", confirmation_gate))

    reports: dict[str, dict[str, Any]] = {}

    def provider_run(provider: str) -> None:
        State.requests = 0
        State.prompts.clear()
        run_id = f"native_conversation_fixture_{provider}_001"
        report = run_native_conversation_validation(
            confirmed=True,
            confirmation=CONFIRMATION_PHRASE,
            config=_config(provider, endpoint),
            timeout_seconds=2,
            first_token_budget_ms=2000,
            total_budget_ms=3000,
            validation_id=run_id,
            persist=True,
            evidence_source="fixture_simulation",
        )
        reports[provider] = report
        assert report["status"] in {"pass", "partial"}, report
        assert report["native_provider_evidence"] is False
        assert report["scenarios_completed"] == 12
        assert [row["classification_match"] for row in report["scenarios"]] == [True] * 12
        assert not any(row["quality_checks"].get("visible_role_label") for row in report["scenarios"])
        assert not any(row["quality_checks"].get("project_report_contamination") for row in report["scenarios"])
        assert all(
            row["quality_checks"].get("continuity_signal") is not False
            for row in report["scenarios"]
        )
        greeting = next(row for row in report["scenarios"] if row["scenario_id"] == "first_greeting")
        assert greeting["performance_budget"]["first_token_metric"] == "first_visible_token"
        assert greeting["timings_ms"]["first_visible_token"] >= greeting["timings_ms"]["first_transport_chunk"]
        assert greeting["stream_counts"]["transport_chunks"] >= 2
        assert report["performance_budgets"]["first_token_metric"] == "first_visible_token"
        assert report["quality_contract"] == "v1102-natural-conversation"
        assert report["quality_scorecard"]["scenario_count"] == 12
        assert report["provider_neutral_tuning_preview"]["automatic_application_allowed"] is False
        assert report["duplicates"]["provider_requests"] == 0
        assert report["counts"]["persistent_conversation_mutations"] == 0
        assert report["recovery"]["cancellation"]["stream_replayed"] is False
        evidence_file = Path(os.environ["EIDOLON_DATA_DIR"]) / Path(report["evidence_path"]).relative_to("data")
        assert report["persisted"] is True and evidence_file.is_file()
        assert len(State.prompts) == report["counts"]["provider_requests_sent"]

    checks.append(_check("ollama_fixture_runs_all_redacted_native_conversation_scenarios", lambda: provider_run("ollama")))
    checks.append(_check("llama_cpp_fixture_runs_all_redacted_native_conversation_scenarios", lambda: provider_run("llama_cpp")))

    def evidence_redaction() -> None:
        report = reports["ollama"]
        encoded = json.dumps(report, sort_keys=True)
        forbidden = [
            "I finally got a quiet evening", "I feel overwhelmed", "Flirt with me a little",
            "That sounds heavy", "Careful, calling me cute", "Synthetic validation project context",
            "So what material is the desk", "Briefly explain why leaves change color", "why does the moon have phases",
        ]
        assert not any(text in encoded for text in forbidden)
        assert report["contains_prompts"] is False
        assert report["contains_generated_responses"] is False
        assert report["contains_raw_conversation_text"] is False
        assert report["contains_provider_payloads"] is False
        evidence_file = Path(os.environ["EIDOLON_DATA_DIR"]) / Path(report["evidence_path"]).relative_to("data")
        persisted = json.loads(evidence_file.read_text(encoding="utf-8"))
        assert json.dumps(persisted, sort_keys=True) == encoded

    checks.append(_check("persisted_evidence_contains_only_redacted_classifications_timings_and_counts", evidence_redaction))

    def idempotent_replay() -> None:
        State.requests = 0
        first = run_native_conversation_validation(
            confirmed=True, confirmation=CONFIRMATION_PHRASE, config=_config("ollama", endpoint),
            validation_id="native_conversation_replay_fixture_001", timeout_seconds=2, persist=True,
            evidence_source="fixture_simulation",
        )
        sent = State.requests
        second = run_native_conversation_validation(
            confirmed=True, confirmation=CONFIRMATION_PHRASE, config=_config("ollama", endpoint),
            validation_id="native_conversation_replay_fixture_001", timeout_seconds=2, persist=True,
            evidence_source="fixture_simulation",
        )
        assert sent > 0 and State.requests == sent
        assert second["replayed_existing_receipt"] is True
        assert second["provider_requests_replayed"] == 0
        assert first["validation_id"] == second["validation_id"]

    checks.append(_check("validation_id_replay_returns_existing_receipt_without_provider_replay", idempotent_replay))

    def unavailable_is_truthful() -> None:
        closed = f"http://127.0.0.1:{_free_port()}"
        report = run_native_conversation_validation(
            confirmed=True, confirmation=CONFIRMATION_PHRASE, config=_config("ollama", closed),
            validation_id="native_conversation_unavailable_001", timeout_seconds=0.2, persist=False,
            evidence_source="fixture_simulation",
        )
        assert report["status"] == "unavailable"
        assert report["scenarios_completed"] == 1
        assert report["recovery"]["provider_recovery_state"] == "operator_recovery_required"
        assert report["recovery"]["automatic_provider_fallback"] is False
        assert report["recovery"]["cancellation"]["status"] == "not_run"
        assert report["quality_scorecard"]["status"] == "unavailable"
        assert report["provider_neutral_tuning_preview"]["status"] == "evidence_required"

    checks.append(_check("unavailable_provider_stops_without_fallback_switch_or_repeated_failures", unavailable_is_truthful))

    def performance_budget_is_evidence_not_false_success() -> None:
        report = run_native_conversation_validation(
            confirmed=True, confirmation=CONFIRMATION_PHRASE, config=_config("ollama", endpoint),
            validation_id="native_conversation_budget_001", timeout_seconds=2,
            first_token_budget_ms=1, total_budget_ms=1, persist=False,
            evidence_source="fixture_simulation",
        )
        assert report["status"] == "partial"
        assert any("total_response_budget_failed" in row["warnings"] for row in report["scenarios"])

    checks.append(_check("performance_budget_failures_are_distinguished_from_transport_completion", performance_budget_is_evidence_not_false_success))

    def structured_internal_failure_and_cancellation_status() -> None:
        import native_conversation_validation as native

        original_client = native.LocalModelClient
        original_cancel = native._cancellation_probe

        class BrokenClient:
            def __init__(self, _config):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def stream(self, _prompt):
                raise RuntimeError("private fixture details must not escape")
                yield ""

        try:
            native.LocalModelClient = BrokenClient
            report = native.run_native_conversation_validation(
                confirmed=True, confirmation=CONFIRMATION_PHRASE, config=_config("ollama", endpoint),
                validation_id="native_conversation_internal_failure_001", timeout_seconds=2, persist=False,
                evidence_source="fixture_simulation",
            )
            assert report["status"] == "fail"
            error = report["scenarios"][0]["error"]
            assert error["code"] == "validator_internal_error"
            assert "private fixture details" not in json.dumps(report)
        finally:
            native.LocalModelClient = original_client

        try:
            native._cancellation_probe = lambda *_args, **_kwargs: {
                "status": "fail", "completion_state": "failed", "request_count": 1,
                "retry_count": 0, "stream_replayed": False, "provider_fallback_used": False,
                "provider_switch_performed": False, "contains_prompt_text": False,
                "contains_response_text": False, "redacted": True,
            }
            report = native.run_native_conversation_validation(
                confirmed=True, confirmation=CONFIRMATION_PHRASE, config=_config("ollama", endpoint),
                validation_id="native_conversation_cancel_failure_001", timeout_seconds=2, persist=False,
                evidence_source="fixture_simulation",
            )
            assert report["status"] == "fail"
        finally:
            native._cancellation_probe = original_cancel

    checks.append(_check("unexpected_validator_errors_are_redacted_and_hard_cancellation_failures_fail_the_report", structured_internal_failure_and_cancellation_status))

    def api_contract() -> None:
        import api_server
        try:
            api_server.handle_api_post("/api/local-model/native-conversation-validation", {"confirm": "wrong"})
        except api_server.ApiError as error:
            assert error.status == 400
        else:
            raise AssertionError("Expected confirmation failure")
        status, payload = api_server.handle_api_post("/api/local-model/native-conversation-validation", {
            "confirm": CONFIRMATION_PHRASE,
            "settings": {
                "local_model_provider": "ollama", "local_model_endpoint": endpoint,
                "local_model": "fixture-ollama", "embed_model": "fixture-embed",
                "local_model_context_size": 8192, "local_model_connect_timeout_seconds": 0.5,
                "local_model_read_timeout_seconds": 2.0,
                "local_model_max_tokens": 128,
                "local_model_temperature": 0.2, "local_model_top_p": 0.9,
                "local_model_top_k": 40, "local_model_repeat_penalty": 1.1,
                "local_model_embedding_endpoint": "",
            },
            "timeout_seconds": 2,
            "validation_id": "native_conversation_api_fixture_001",
        })
        assert status == 200 and payload["ok"] is True
        assert payload["data"]["contains_raw_conversation_text"] is False

    checks.append(_check("api_requires_confirmation_and_returns_only_redacted_validation_evidence", api_contract))

    def dashboard_contract() -> None:
        html = render_local_model_status(
            safe=lambda value: str(value).replace("&", "&amp;").replace("<", "&lt;").replace("'", "&#39;"),
            card=lambda title, body: f"<section><h2>{title}</h2>{body}</section>",
            layout=lambda route, body: body,
        )
        assert "local-model-conversation-validation" in html
        assert "RUN_NATIVE_CONVERSATION_VALIDATION" in html
        assert "/api/local-model/native-conversation-validation" in html
        assert "conversationValidationRunning" in html
        assert "conversationValidationButton.disabled = true" in html
        assert "validation_id: conversationValidationId" in html
        assert "No duplicate request was sent" in html
        assert "No raw prompts" not in html or "raw prompts" in html
        scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.DOTALL)
        assert scripts
        node = shutil.which("node")
        if node:
            tmp = Path(tempfile.mkdtemp(prefix="eidolon-v1079-8-js-")) / "provider.js"
            tmp.write_text("\n".join(scripts), encoding="utf-8")
            import subprocess
            completed = subprocess.run([node, "--check", str(tmp)], text=True, capture_output=True)
            assert completed.returncode == 0, completed.stderr

    checks.append(_check("provider_dashboard_exposes_confirmed_validation_and_rendered_javascript_parses", dashboard_contract))

    def cli_help_contract() -> None:
        source = (ROOT / "eidolon.py").read_text(encoding="utf-8")
        main_source = (AGENT / "main.py").read_text(encoding="utf-8")
        assert "conversation-validation" in source
        assert "--confirm-native" in source
        assert "--native-conversation-validation" in main_source
        assert "--confirm-native-conversation-validation" in main_source

    checks.append(_check("operator_cli_exposes_explicit_native_conversation_confirmation_only", cli_help_contract))

    def invalid_cli_identifier_is_redacted_and_bounded() -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "eidolon.py"),
                "conversation-validation",
                "--confirm-native",
                "--validation-id",
                "invalid-id",
                "--json",
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert completed.returncode == 2
        assert "Traceback" not in completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["status"] == "blocked"
        assert payload["invalid_request"] is True
        assert payload["failure_category"] == "invalid_configuration"
        assert payload["native_provider_evidence"] is False
        assert payload["provider_requests_sent"] == 0
        assert payload["persisted"] is False

    checks.append(_check("invalid_cli_validation_identifier_returns_redacted_json_without_traceback", invalid_cli_identifier_is_redacted_and_bounded))

    def governance_boundaries() -> None:
        source = (AGENT / "native_conversation_validation.py").read_text(encoding="utf-8")
        forbidden_calls = ["subprocess.run", "pip install", "ollama pull", "delete_model", "switch_provider", "approve_approval"]
        assert not any(token in source for token in forbidden_calls)
        for report in reports.values():
            assert report["automatic_model_management"] is False
            assert report["provider_configuration_changed"] is False
            assert report["approval_granted"] is False
            assert report["release_authorized"] is False
            assert report["autonomous_action_performed"] is False

    checks.append(_check("validation_grants_no_model_provider_approval_release_or_autonomy_authority", governance_boundaries))

    server.shutdown()
    server.server_close()
    after = _source_snapshot()
    checks.append({
        "name": "source_tree_immutable_during_fixture_validation",
        "status": "pass" if before == after else "fail",
        "seconds": 0.0,
        **({} if before == after else {"error": "source tree changed"}),
    })
    passed = sum(1 for item in checks if item["status"] == "pass")
    return {
        "suite": "native-conversation-validation-v1079.8.2",
        "evidence_source": "fixture_simulation",
        "native_provider_evidence": False,
        "ok": passed == len(checks),
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "contains_raw_native_conversation_evidence": False,
        "source_tree_immutable": before == after,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_tests()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['suite']}: {report['passed']}/{report['total']} passed")
        for row in report["checks"]:
            print(f"- {row['status']}: {row['name']}")
            if row.get("error"):
                print(f"  {row['error']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
