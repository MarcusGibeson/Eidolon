from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2300-windows-data-")

from fine_grained_authority_v2200 import build_permission_policy, evaluate_policy_ceiling, read_policy_state, revoke_policy
from local_tool_interaction_v2100 import build_tool_preview, prepare_existing_execution_handoff

checks: list[str] = []


def require(value: object, name: str) -> None:
    checks.append(name)
    assert value, name


require(os.name == "nt", "native_windows_host")
digest = "a" * 64
policy = build_permission_policy(
    policy_id="windows-native",
    capability="file_read",
    target_digest=digest,
    scope=["workspace"],
    mode="read_only",
    duration_seconds=300,
    issued_epoch=100,
)
base_request = {
    "capability": "file_read",
    "target_digest": digest,
    "scope": ["workspace"],
    "environment": "isolated_workspace",
    "effect": "read",
}
require(evaluate_policy_ceiling(policy, base_request, now_epoch=101)["allowed_by_policy_ceiling"], "bounded_native_request_within_ceiling")
deputy = evaluate_policy_ceiling(policy, {**base_request, "target_digest": "b" * 64}, now_epoch=101)
require(not deputy["allowed_by_policy_ceiling"] and "target_mismatch" in deputy["reason_codes"], "confused_deputy_target_rejected")
traversal = evaluate_policy_ceiling(policy, {**base_request, "scope": ["workspace/../outside"]}, now_epoch=101)
require(not traversal["allowed_by_policy_ceiling"] and "scope_expansion" in traversal["reason_codes"], "traversal_shaped_scope_rejected")

runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2300-windows-revoke-"))


def revoke(event_id: str, target: Path) -> dict[str, object]:
    return revoke_policy(
        policy_digest=policy["policy_digest"],
        reason_code="race",
        event_id=event_id,
        runtime_root=target,
    )


with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(lambda index: revoke(f"event-{index}", runtime), range(4)))
require(all(result.get("ok") for result in results), "concurrent_revocations_complete")
state = read_policy_state(runtime_root=runtime)
require(int(state.get("revision") or 0) == 4 and len(state.get("history") or []) == 4, "concurrent_revocations_converge_without_loss")
revoked = evaluate_policy_ceiling(policy, base_request, runtime_root=runtime, now_epoch=101)
require(not revoked["allowed_by_policy_ceiling"] and revoked["status"] == "authority_policy_revoked", "revocation_visible_after_runtime_reload")

replay_runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2300-windows-replay-"))
with ThreadPoolExecutor(max_workers=4) as executor:
    replay_results = list(executor.map(lambda _: revoke("same-event", replay_runtime), range(4)))
require(all(result.get("ok") for result in replay_results), "concurrent_exact_replays_complete")
replay_state = read_policy_state(runtime_root=replay_runtime)
require(int(replay_state.get("revision") or 0) == 1 and len(replay_state.get("history") or []) == 1, "concurrent_exact_replay_is_once")

preview = build_tool_preview(
    tool_class="read",
    operation="file_read",
    argument_metadata={"target": "workspace_file"},
    target_scope="workspace",
    request_id="windows-native",
)["preview"]
deny_policy = build_permission_policy(
    policy_id="deny",
    capability="tool:read:file_read",
    target_digest=digest,
    scope=["workspace"],
    mode="deny",
    environment="isolated_workspace",
)
handoff = prepare_existing_execution_handoff(
    preview,
    authority_policy=deny_policy,
    authority_request={**base_request, "capability": "tool:read:file_read"},
)
effect_target = Path(tempfile.mkdtemp(prefix="eidolon-v2300-no-effect-")) / "should-not-exist.txt"
if handoff.get("ok"):
    effect_target.write_text("unexpected", encoding="utf-8")
require(not handoff.get("ok") and not effect_target.exists(), "denied_handoff_has_no_filesystem_effect")

print(json.dumps({"suite": "v2300.9-era8-windows-native", "ok": True, "passed": len(checks), "failed": 0, "checks": checks}, sort_keys=True))
