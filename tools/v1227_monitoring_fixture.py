from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import execution_session_authorization_bounded_launch as launch_module
from v1226_launch_fixture import build_launch_fixture


def build_monitoring_fixture(seed: str = "v1227"):
    fixture = build_launch_fixture(seed)
    runtime = fixture["runtime"]
    session = fixture["prepared_session"]
    authorization = launch_module.prepare_bounded_launch_authorization(
        session["session_id"],
        expected_session_digest=session["session_digest"],
        runtime_root=runtime,
    )
    assert authorization.get("ok"), authorization
    launch = launch_module.launch_bounded_development_execution_session(
        authorization["authorization_id"],
        expected_authorization_digest=authorization["authorization_digest"],
        expected_session_id=session["session_id"],
        expected_session_digest=session["session_digest"],
        runtime_root=runtime,
    )
    assert launch.get("ok"), launch
    return {
        **fixture,
        "launch_authorization": authorization,
        "launch": launch,
    }
