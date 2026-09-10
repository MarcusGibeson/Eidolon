from __future__ import annotations

"""Deterministic v1079.2 provider evidence and configuration-hardening fixtures.

All HTTP activity targets local fixture servers. The suite never claims native
Ollama, llama.cpp, Windows, model-file, or operator certification evidence.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
TOOLS = ROOT / "tools"
for item in (str(AGENT), str(TOOLS), str(ROOT)):
    if item not in sys.path:
        sys.path.insert(0, item)
EXTERNAL_DATA_DIR = Path(os.environ.get("EIDOLON_DATA_DIR") or (ROOT / "data")).resolve()


def _load_application_modules() -> None:
    global InvalidConfigurationError, LocalModelConfig, MalformedResponseError
    global EndpointState, FixtureServer, _config
    global EVIDENCE_SOURCE_FIXTURE, EVIDENCE_SOURCE_NATIVE
    global build_receipt, configuration_digest, drift_report
    global normalize_evidence_source, redact_error, sanitize_endpoint
    global _snapshot_source, native_model_smoke, provider_readiness

    from local_model import InvalidConfigurationError, LocalModelConfig, MalformedResponseError
    from local_model_configuration_tests import EndpointState, FixtureServer, _config
    from local_model_evidence import (
        EVIDENCE_SOURCE_FIXTURE,
        EVIDENCE_SOURCE_NATIVE,
        build_receipt,
        configuration_digest,
        drift_report,
        normalize_evidence_source,
        redact_error,
        sanitize_endpoint,
    )
    from local_model_integration_tests import _snapshot_source
    from local_model_readiness import native_model_smoke, provider_readiness


def _readiness(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("evidence_source", EVIDENCE_SOURCE_FIXTURE)
    return provider_readiness(*args, **kwargs)


def _smoke(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("evidence_source", EVIDENCE_SOURCE_FIXTURE)
    return native_model_smoke(*args, **kwargs)


def _subprocess_json(code: str, data_dir: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env.update({
        "EIDOLON_DATA_DIR": str(data_dir),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join([str(AGENT), str(TOOLS), str(ROOT)]),
    })
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if completed.returncode != 0:
        raise AssertionError({"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
    return json.loads(completed.stdout)


def _run_tests_destructive() -> dict[str, Any]:
    before = _snapshot_source()
    results: list[dict[str, Any]] = []

    def case(name: str, callback: Callable[[], None]) -> None:
        started = time.monotonic()
        try:
            callback()
        except Exception as error:
            results.append({
                "name": name,
                "status": "fail",
                "seconds": round(time.monotonic() - started, 4),
                "error": repr(error),
            })
        else:
            results.append({"name": name, "status": "pass", "seconds": round(time.monotonic() - started, 4)})

    def receipt_contract(provider: str) -> None:
        generation = EndpointState(provider=provider, models=["gen-model"])
        embedding = EndpointState(provider=provider, models=["embed-model"])
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            config = _config(provider, gen_server.endpoint, embed_server.endpoint)
            readiness = _readiness(config=config)
            assert readiness["status"] == "ready", readiness
            digest = configuration_digest(config)
            assert readiness["configuration_digest"] == digest
            readiness_receipt = readiness["evidence_receipt"]
            assert readiness_receipt["receipt_type"] == "provider_readiness"
            assert readiness_receipt["evidence_source"] == EVIDENCE_SOURCE_FIXTURE
            assert readiness_receipt["native_provider_evidence"] is False
            assert readiness_receipt["configuration_digest"] == digest
            assert readiness_receipt["provider"] == provider
            assert readiness_receipt["generation_model"] == "gen-model"
            assert readiness_receipt["embedding_model"] == "embed-model"
            assert readiness_receipt["timestamp"].endswith("Z")
            smoke = _smoke(
                config=config,
                confirmed=True,
                timeout_seconds=1.5,
                readiness_configuration_digest=digest,
            )
            assert smoke["status"] == "pass", smoke
            assert smoke["configuration_drift"]["status"] == "matched"
            nested_readiness = smoke["checks"][0]["details"]
            assert nested_readiness["configuration_digest"] == digest
            assert nested_readiness["evidence_receipt"]["configuration_digest"] == digest
            receipt = smoke["evidence_receipt"]
            assert receipt["receipt_type"] == "native_provider_smoke"
            assert receipt["native_provider_evidence"] is False
            assert receipt["embedding_dimensions"] in {3, 4}
            assert {row["name"] for row in receipt["tested_capabilities"]} == {
                "health_and_model_readiness", "bounded_generation", "bounded_streaming", "bounded_embedding"
            }
            serialized = json.dumps(receipt, sort_keys=True)
            for forbidden in (
                "EIDOLON_NATIVE_OK", "EIDOLON_STREAM_OK", "SEPARATE_OK",
                "traceback", "Authorization",
            ):
                assert forbidden not in serialized, (forbidden, serialized)
            assert receipt["contains_prompts"] is False
            assert receipt["contains_generated_responses"] is False
            assert receipt["contains_credentials"] is False
            assert receipt["contains_raw_events"] is False
            assert receipt["persisted"] is False

    def configuration_drift_blocks_requests() -> None:
        first_state = EndpointState(provider="ollama", models=["gen-model", "embed-model"])
        second_state = EndpointState(provider="ollama", models=["gen-model", "embed-model"])
        with FixtureServer(first_state) as first_server, FixtureServer(second_state) as second_server:
            first = _config("ollama", first_server.endpoint)
            second = _config("ollama", second_server.endpoint)
            readiness = _readiness(config=first)
            before_requests = len(second_state.requests)
            report = _smoke(
                config=second,
                confirmed=True,
                timeout_seconds=1.0,
                readiness_configuration_digest=readiness["configuration_digest"],
            )
            assert report["status"] == "blocked", report
            assert report["native_evidence"] is False
            assert report["configuration_drift"]["status"] == "detected"
            assert report["issues"][0]["classification"] == "configuration_drift"
            assert len(second_state.requests) == before_requests

    def evidence_labels_fail_closed() -> None:
        config = LocalModelConfig()
        check = {
            "name": "health_and_model_readiness",
            "status": "pass",
            "capability": "health",
            "service": "generation",
            "elapsed_seconds": 0.01,
        }
        unknown = build_receipt(
            receipt_type="native_provider_smoke",
            config=config,
            result="pass",
            checks=[check],
            elapsed_seconds=0.01,
            evidence_source="misspelled-native-source",
        )
        assert normalize_evidence_source("misspelled-native-source") == EVIDENCE_SOURCE_FIXTURE
        assert unknown["evidence_source"] == EVIDENCE_SOURCE_FIXTURE
        assert unknown["native_provider_evidence"] is False

        zero_request = build_receipt(
            receipt_type="native_provider_smoke",
            config=config,
            result="blocked",
            checks=[],
            elapsed_seconds=0.0,
            evidence_source=EVIDENCE_SOURCE_NATIVE,
            configuration_drift=drift_report("a" * 64, "b" * 64),
        )
        assert zero_request["evidence_source"] == EVIDENCE_SOURCE_NATIVE
        assert zero_request["tested_capabilities"] == []
        assert zero_request["native_provider_evidence"] is False

    def synthetic_missing_model_issues_are_redacted() -> None:
        state = EndpointState(provider="ollama", models=["different-model"])
        with FixtureServer(state) as server:
            config = _config("ollama", server.endpoint)
            report = _readiness(config=config)
            missing = [
                issue for issue in report["issues"]
                if issue.get("classification") in {"missing_model", "missing_embedding_model"}
            ]
            assert missing, report
            assert all(issue.get("redacted") is True for issue in missing)
            assert all(issue.get("endpoint") == sanitize_endpoint(server.endpoint) for issue in missing)

    def invalid_readiness_digest_is_bounded() -> None:
        state = EndpointState(provider="ollama", models=["gen-model", "embed-model"])
        with FixtureServer(state) as server:
            config = _config("ollama", server.endpoint)
            before_requests = len(state.requests)
            report = _smoke(
                config=config,
                confirmed=True,
                timeout_seconds=1.0,
                readiness_configuration_digest="secret-query-data=" + ("x" * 10000),
            )
            assert report["status"] == "blocked", report
            assert report["configuration_drift"]["status"] == "invalid_expected_digest"
            assert report["configuration_drift"]["expected_configuration_digest"] == "[invalid-digest]"
            assert "secret-query-data" not in json.dumps(report)
            assert len(state.requests) == before_requests

    def redacted_error_contract() -> None:
        raw = MalformedResponseError(
            "Malformed response from http://user:secret@127.0.0.1:8080/private?token=abc#frag",
            provider="llama_cpp",
            endpoint="http://user:secret@127.0.0.1:8080/private?token=abc#frag",
            model="gen-model",
            details={
                "body": "SECRET_RESPONSE_BODY",
                "response": {"raw": "SECRET_EVENT"},
                "line": "SECRET_STREAM_LINE",
                "exception_type": "JSONDecodeError",
            },
        )
        safe = redact_error(raw, service="generation", capability="generation")
        serialized = json.dumps(safe, sort_keys=True)
        assert safe["endpoint"] == "http://127.0.0.1:8080/private"
        assert safe["details"] == {"exception_type": "JSONDecodeError"}
        for secret in ("user", "secret", "token=abc", "SECRET_RESPONSE_BODY", "SECRET_EVENT", "SECRET_STREAM_LINE"):
            assert secret not in serialized, serialized
        assert safe["redacted"] is True

    def invalid_sensitive_urls() -> None:
        for endpoint in (
            "http://user:password@127.0.0.1:8080",
            "http://127.0.0.1:8080?token=secret",
            "http://127.0.0.1:8080#fragment",
        ):
            try:
                LocalModelConfig(provider="ollama", endpoint=endpoint, model="m", embed_model="e").validated()
            except InvalidConfigurationError as error:
                assert "credentials" in str(error) or "query" in str(error) or "fragment" in str(error)
            else:
                raise AssertionError(f"Sensitive endpoint was accepted: {endpoint}")
        assert sanitize_endpoint("http://user:password@127.0.0.1:8080/private?token=secret#frag") == "http://127.0.0.1:8080/private"

    def malformed_api_is_bounded_and_redacted() -> None:
        generation = EndpointState(provider="ollama", models=["gen-model"], scenario="malformed")
        embedding = EndpointState(provider="ollama", models=["embed-model"])
        with FixtureServer(generation) as gen_server, FixtureServer(embedding) as embed_server:
            from api_server import handle_api_post
            settings = {
                "local_model_provider": "ollama",
                "local_model_endpoint": gen_server.endpoint,
                "local_model_embedding_endpoint": embed_server.endpoint,
                "local_model": "gen-model",
                "embed_model": "embed-model",
                "local_model_context_size": 4096,
                "local_model_connect_timeout_seconds": 0.2,
                "local_model_read_timeout_seconds": 1.0,
                "local_model_max_tokens": 24,
                "local_model_temperature": 0.0,
                "local_model_top_p": 0.9,
                "local_model_top_k": 20,
                "local_model_repeat_penalty": 1.05,
            }
            status, payload = handle_api_post("/api/local-model/readiness", {"settings": settings})
            assert status == 200
            data = payload["data"]
            assert data["status"] == "blocked"
            serialized = json.dumps(payload)
            assert "{bad-json" not in serialized
            assert "Traceback" not in serialized
            assert all(item.get("redacted") is True for item in data["issues"])
            assert len(serialized) < 30000

    def settings_survive_restart_and_switching() -> None:
        with tempfile.TemporaryDirectory(prefix="eidolon-v1079-2-restart-") as temp:
            data_dir = Path(temp)
            save_code = '''
import json
from local_model_configuration import save_local_model_configuration
payload = json.loads(%r)
print(json.dumps(save_local_model_configuration(payload)))
'''
            ollama = {
                "local_model_provider": "ollama",
                "local_model_endpoint": "http://127.0.0.1:11434",
                "local_model_embedding_endpoint": "",
                "local_model": "ollama-gen",
                "embed_model": "ollama-embed",
                "local_model_context_size": 8192,
                "local_model_connect_timeout_seconds": 3.0,
                "local_model_read_timeout_seconds": 60.0,
                "local_model_max_tokens": 128,
                "local_model_temperature": 0.4,
                "local_model_top_p": 0.9,
                "local_model_top_k": 40,
                "local_model_repeat_penalty": 1.1,
            }
            _subprocess_json(save_code % json.dumps(ollama), data_dir)
            full_restart = _subprocess_json(
                "import json; from local_model import LocalModelConfig; c=LocalModelConfig.from_settings(); print(json.dumps({'provider':c.provider,'endpoint':c.endpoint,'embedding':c.resolved_embedding_endpoint,'model':c.model,'embed_model':c.embed_model}))",
                data_dir,
            )
            assert full_restart == {
                "provider": "ollama", "endpoint": "http://127.0.0.1:11434",
                "embedding": "http://127.0.0.1:11434", "model": "ollama-gen", "embed_model": "ollama-embed",
            }
            dashboard_restart = _subprocess_json(
                "import json; from local_model_configuration import configuration_payload; print(json.dumps(configuration_payload()))",
                data_dir,
            )
            assert dashboard_restart["values"]["local_model_provider"] == "ollama"
            assert dashboard_restart["embedding_endpoint_uses_generation_fallback"] is True

            llama = dict(ollama)
            llama.update({
                "local_model_provider": "llama_cpp",
                "local_model_endpoint": "http://127.0.0.1:8080",
                "local_model_embedding_endpoint": "http://127.0.0.1:8081",
                "local_model": "llama-gen",
                "embed_model": "llama-embed",
            })
            _subprocess_json(save_code % json.dumps(llama), data_dir)
            switched = _subprocess_json(
                "import json; from local_model import LocalModelConfig; c=LocalModelConfig.from_settings(); print(json.dumps({'provider':c.provider,'endpoint':c.endpoint,'embedding':c.resolved_embedding_endpoint,'model':c.model,'embed_model':c.embed_model}))",
                data_dir,
            )
            assert switched == {
                "provider": "llama_cpp", "endpoint": "http://127.0.0.1:8080",
                "embedding": "http://127.0.0.1:8081", "model": "llama-gen", "embed_model": "llama-embed",
            }

    def dashboard_digest_handoff_present() -> None:
        import html
        from dashboard_local_model import render_local_model_status
        rendered = render_local_model_status(
            safe=lambda value: html.escape(str(value), quote=True),
            card=lambda title, body: f"<section><h3>{title}</h3>{body}</section>",
            layout=lambda route, body: body,
        )
        assert "readinessConfigurationDigest" in rendered
        assert "readiness_configuration_digest" in rendered
        assert "Configuration drift" in rendered
        assert "native_provider_evidence" in rendered
        assert "native evidence:" in rendered
        assert "error.message" not in rendered
        assert "unknown browser error" not in rendered
        assert "title=" not in rendered.lower()

    for name, callback in [
        ("ollama_structured_redacted_receipts", lambda: receipt_contract("ollama")),
        ("llama_cpp_structured_redacted_receipts", lambda: receipt_contract("llama_cpp")),
        ("configuration_drift_blocks_native_requests", configuration_drift_blocks_requests),
        ("evidence_labels_fail_closed_without_native_requests", evidence_labels_fail_closed),
        ("synthetic_missing_model_issues_are_redacted", synthetic_missing_model_issues_are_redacted),
        ("invalid_readiness_digest_is_bounded", invalid_readiness_digest_is_bounded),
        ("provider_error_redaction_contract", redacted_error_contract),
        ("sensitive_endpoint_validation", invalid_sensitive_urls),
        ("api_errors_are_bounded_and_redacted", malformed_api_is_bounded_and_redacted),
        ("settings_survive_dashboard_full_restart_and_switching", settings_survive_restart_and_switching),
        ("dashboard_readiness_smoke_digest_handoff", dashboard_digest_handoff_present),
    ]:
        case(name, callback)

    after = _snapshot_source()
    unchanged = before == after
    if not unchanged:
        results.append({"name": "source_tree_immutability", "status": "fail", "error": "Source tree changed during v1079.2 fixtures."})
    passed = sum(item["status"] == "pass" for item in results)
    ok = unchanged and passed == len(results)
    return {
        "suite": "v1079.2 native provider certification and configuration hardening fixtures",
        "evidence_type": EVIDENCE_SOURCE_FIXTURE,
        "native_provider_evidence": False,
        "ok": ok,
        "status": "pass" if ok else "fail",
        "passed": passed,
        "total": len(results),
        "source_tree_unchanged": unchanged,
        "results": results,
    }


def _runtime_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "files": {}, "directories": []}
    files: dict[str, str] = {}
    directories: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(relative)
        elif path.is_file():
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"exists": True, "files": files, "directories": directories}


def run_tests() -> dict[str, Any]:
    runtime_before = _runtime_snapshot(EXTERNAL_DATA_DIR)
    original_exists = EXTERNAL_DATA_DIR.exists()
    backup_root = Path(tempfile.mkdtemp(prefix="eidolon-local-model-certification-backup-"))
    backup_data = backup_root / "data"
    if original_exists:
        shutil.copytree(EXTERNAL_DATA_DIR, backup_data)
    restore_error: str | None = None
    try:
        _load_application_modules()
        report = _run_tests_destructive()
    except Exception as error:
        report = {
            "suite": "v1079.2 native provider certification and configuration hardening fixtures",
            "evidence_type": "fixture_simulation",
            "native_provider_evidence": False,
            "status": "fail",
            "passed": 0,
            "total": 0,
            "source_tree_unchanged": False,
            "results": [{"name": "fixture_suite_execution", "status": "fail", "error": f"{type(error).__name__}: {error}"}],
        }
    finally:
        try:
            shutil.rmtree(EXTERNAL_DATA_DIR, ignore_errors=True)
            if original_exists:
                shutil.copytree(backup_data, EXTERNAL_DATA_DIR)
        except Exception as error:
            restore_error = f"{type(error).__name__}: {error}"
        finally:
            shutil.rmtree(backup_root, ignore_errors=True)

    runtime_restored = restore_error is None and runtime_before == _runtime_snapshot(EXTERNAL_DATA_DIR)
    results = list(report.get("results") or [])
    results.append({
        "name": "external_runtime_seed_restored_after_fixture_suite",
        "status": "pass" if runtime_restored else "fail",
        **({} if runtime_restored else {"error": restore_error or "external runtime data changed"}),
    })
    passed = sum(item.get("status") == "pass" for item in results)
    report.update({
        "results": results,
        "passed": passed,
        "total": len(results),
        "runtime_data_restored": runtime_restored,
        "runtime_data_restore_error": restore_error,
    })
    report["status"] = "pass" if report.get("source_tree_unchanged") and passed == len(results) else "fail"
    report["ok"] = report["status"] == "pass"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic v1079.2 provider evidence and configuration-hardening fixtures.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_tests()
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"{report['status'].upper()}: {report['passed']}/{report['total']} v1079.2 checks")
        for item in report["results"]:
            print(f"- {item['status']}: {item['name']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
