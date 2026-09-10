from __future__ import annotations

import argparse
import json
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import conversation_context
import conversation_runtime
import conversation_sessions as sessions
import dashboard_chat_console
import memory
import release_metadata
import relationship_continuity
import relationship_memory_curation as curation
import relationship_personality_continuity as continuity_policy
from local_model import LocalModelConfig


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


@contextmanager
def patched(module: Any, **values: Any):
    originals = {key: getattr(module, key) for key in values}
    for key, value in values.items():
        setattr(module, key, value)
    try:
        yield
    finally:
        for key, value in originals.items():
            setattr(module, key, value)


@contextmanager
def isolated_memory():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-8-memory-") as raw:
        root = Path(raw)
        with patched(memory, MEMORY_FILE=root / "memories.json", THOUGHT_LOG_FILE=root / "thoughts.log"):
            yield root


@contextmanager
def isolated_sessions():
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-8-sessions-") as raw:
        root = Path(raw)
        originals = {
            "CONVERSATION_SESSIONS_DIR": sessions.CONVERSATION_SESSIONS_DIR,
            "ACTIVE_SESSION_FILE": sessions.ACTIVE_SESSION_FILE,
            "CONVERSATION_DRAFTS_DIR": sessions.CONVERSATION_DRAFTS_DIR,
            "LEGACY_DASHBOARD_CHAT_DIR": sessions.LEGACY_DASHBOARD_CHAT_DIR,
            "LEGACY_DASHBOARD_CHAT_IMPORT_FILE": sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE,
        }
        sessions.CONVERSATION_SESSIONS_DIR = root / "conversation_sessions"
        sessions.ACTIVE_SESSION_FILE = sessions.CONVERSATION_SESSIONS_DIR / "active_session.json"
        sessions.CONVERSATION_DRAFTS_DIR = sessions.CONVERSATION_SESSIONS_DIR / "drafts"
        sessions.LEGACY_DASHBOARD_CHAT_DIR = root / "legacy"
        sessions.LEGACY_DASHBOARD_CHAT_IMPORT_FILE = sessions.CONVERSATION_SESSIONS_DIR / "legacy_import.json"
        sessions.clear_conversation_search_cache()
        try:
            yield root
        finally:
            sessions.clear_conversation_search_cache()
            for key, value in originals.items():
                setattr(sessions, key, value)


def _relationship_memories() -> list[dict[str, Any]]:
    return [
        {
            "id": "nick_old", "type": "nickname", "content": "Marcus prefers the nickname OldName.",
            "status": "active", "relationship_eligible": True, "use_in_conversation": True,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
        },
        {
            "id": "nick_new", "type": "nickname", "content": "Marcus prefers the nickname Marc.",
            "status": "active", "relationship_eligible": True, "use_in_conversation": True,
            "created_at": "2026-02-01T00:00:00", "updated_at": "2026-02-01T00:00:00",
        },
        {
            "id": "mood_old", "type": "user_mood", "content": "Marcus feels worn out.",
            "status": "active", "relationship_eligible": True, "use_in_conversation": True,
            "mood_state": "current", "observed_at": "2026-07-18T10:00:00+00:00",
        },
        {
            "id": "mood_new", "type": "user_mood", "content": "Marcus feels hopeful.",
            "status": "active", "relationship_eligible": True, "use_in_conversation": True,
            "mood_state": "current", "observed_at": "2026-07-18T11:00:00+00:00",
        },
        {
            "id": "moment", "type": "important_moment", "content": "Marcus completed a difficult milestone.",
            "status": "active", "relationship_eligible": True, "use_in_conversation": True,
            "moment_state": "open", "occurred_at": "2026-07-17T11:00:00+00:00",
        },
    ]


def test_interaction_lanes_are_deterministic_and_narrow() -> None:
    ordinary = continuity_policy.classify_relationship_personality_continuity("Tell me a joke")
    relational = continuity_policy.classify_relationship_personality_continuity("I feel lonely and need support")
    operator = continuity_policy.classify_relationship_personality_continuity("Please run diagnostics")
    mixed = continuity_policy.classify_relationship_personality_continuity("I'm worried, but please run diagnostics")
    require(ordinary.lane == "ordinary", f"ordinary lane drifted: {ordinary}")
    require(relational.lane == "relational" and relational.relationship_cues_allowed, "relational lane drifted")
    require(operator.lane == "operator" and not operator.relationship_cues_allowed, "operator lane did not suppress cues")
    require(mixed.lane == "mixed" and mixed.relationship_cues_allowed, "mixed lane did not preserve personal context")


def test_short_follow_up_inherits_relational_lane_without_becoming_operator_work() -> None:
    history = [{
        "user_message": "I feel anxious about tomorrow.",
        "assistant_response": "We can stay with that.",
        "continuity_lane": "relational",
    }]
    profile = continuity_policy.classify_relationship_personality_continuity("tell me more", history)
    require(profile.lane == "relational", f"relational follow-up lane drifted: {profile}")
    require(not profile.explicit_operator_request and profile.relationship_cues_allowed, "relational follow-up became operator work")


def test_operator_follow_up_stays_operator_only() -> None:
    history = [{
        "user_message": "Run diagnostics",
        "assistant_response": "I routed that through the visible action controls.",
        "continuity_lane": "operator",
    }]
    profile = continuity_policy.classify_relationship_personality_continuity("did that finish", history)
    require(profile.lane == "operator", f"operator follow-up lost lane: {profile}")
    require(not profile.relationship_cues_allowed, "operator follow-up admitted relationship cues")


def test_operator_prompt_suppresses_private_relationship_cues() -> None:
    memories = _relationship_memories()
    profile = continuity_policy.classify_relationship_personality_continuity("Run diagnostics")
    snapshot = relationship_continuity.build_relationship_continuity_snapshot(
        memories, {"current_state": {"mood_label": "steady"}},
        user_message="Run diagnostics", interaction_profile=profile,
    )
    packet = conversation_context.build_conversation_prompt(
        user_message="Run diagnostics", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="project", goal_context="goal", task_context="task", conversation_history=[],
        relationship_context=snapshot, continuity_profile=profile, context_size=4096, max_tokens=256,
    )
    for private in ("OldName", "nickname Marc", "worn out", "hopeful", "difficult milestone"):
        require(private not in packet.prompt, f"operator prompt leaked relationship cue: {private}")
    require(packet.metrics.continuity_lane == "operator", "operator lane missing from context metrics")
    require(packet.metrics.relationship_cues_included == 0, "operator prompt included relationship cues")
    require(packet.metrics.relationship_cues_suppressed >= 3, "suppressed cue count was not recorded")
    require("Action success, failure" in packet.prompt, "personality/relationship guard missing")


def test_mixed_prompt_keeps_personal_and_operator_work_separate() -> None:
    profile = continuity_policy.classify_relationship_personality_continuity("I'm worried, but please run diagnostics")
    snapshot = relationship_continuity.build_relationship_continuity_snapshot(
        _relationship_memories(), {"current_state": {"mood_label": "steady"}},
        user_message="I'm worried, but please run diagnostics", interaction_profile=profile,
    )
    packet = conversation_context.build_conversation_prompt(
        user_message="I'm worried, but please run diagnostics", self_model={"name": "Eidolon"}, desires={}, memories=[],
        project_context="project", goal_context="goal", task_context="task", conversation_history=[],
        relationship_context=snapshot, continuity_profile=profile, context_size=4096, max_tokens=256,
    )
    require(packet.metrics.continuity_lane == "mixed", "mixed lane missing from metrics")
    require("mixes personal conversation and operator work" in packet.prompt, "mixed-lane guard missing")
    require("Marcus feels hopeful" in packet.prompt, "mixed prompt lost current explicit mood")
    require("Action success, failure" in packet.prompt, "operator/relationship separation missing")


def test_legacy_singleton_conflicts_choose_newest_without_mutating_input() -> None:
    memories = _relationship_memories()
    before = json.dumps(memories, sort_keys=True)
    snapshot = relationship_continuity.build_relationship_continuity_snapshot(
        memories, {"current_state": {}}, user_message="What do you remember about me?",
    )
    prompt = snapshot.to_prompt_block()
    require("nickname Marc" in prompt and "OldName" not in prompt, "newest nickname was not selected")
    require("Marcus feels hopeful" in prompt and "worn out" not in prompt, "newest mood was not selected")
    require(snapshot.singleton_conflicts_omitted == 2, f"singleton conflict count drifted: {snapshot.singleton_conflicts_omitted}")
    require(json.dumps(memories, sort_keys=True) == before, "read-only snapshot mutated legacy memories")


def test_new_nickname_transactionally_supersedes_old_without_deletion() -> None:
    with isolated_memory():
        first = curation.create_relationship_memory("nickname", "Marcus prefers OldName.", source="fixture_operator")
        second = curation.create_relationship_memory("nickname", "Marcus prefers Marc.", source="fixture_operator")
        rows = memory.load_memories()
    old = next(row for row in rows if row.get("id") == first["record"]["id"])
    new = next(row for row in rows if row.get("id") == second["record"]["id"])
    require(second.get("singleton_replacements") == 1, "new nickname did not report one replacement")
    require(old.get("curation_state") == "disabled" and old.get("relationship_eligible") is False, "old nickname stayed current")
    require(old.get("superseded_by") == new.get("id"), "old nickname lacks replacement linkage")
    require(any(event.get("action") == "superseded_by_new_nickname" for event in old.get("curation_history", [])), "supersede audit missing")
    require(old.get("content") == "Marcus prefers OldName.", "supersede deleted old content")
    require(new.get("relationship_eligible") is True, "new nickname is not current")


def test_new_current_mood_clears_previous_and_make_current_is_exclusive() -> None:
    with isolated_memory():
        first = curation.create_relationship_memory("user_mood", "Marcus feels tired.", source="fixture_operator")
        second = curation.create_relationship_memory("user_mood", "Marcus feels hopeful.", source="fixture_operator")
        rows = memory.load_memories()
        old = next(row for row in rows if row.get("id") == first["record"]["id"])
        new = next(row for row in rows if row.get("id") == second["record"]["id"])
        require(old.get("mood_state") == "cleared" and new.get("mood_state") == "current", "new mood did not clear old mood")
        curation.update_relationship_memory(first["record"]["record_key"], "make_current", source="fixture_operator")
        rows = memory.load_memories()
    old = next(row for row in rows if row.get("id") == first["record"]["id"])
    new = next(row for row in rows if row.get("id") == second["record"]["id"])
    require(old.get("mood_state") == "current" and new.get("mood_state") == "cleared", "make-current left two current moods")
    require(any(event.get("action") == "cleared_for_new_current_mood" for event in new.get("curation_history", [])), "mood replacement audit missing")


def test_automatic_conversation_memories_are_relationship_ineligible() -> None:
    with isolated_memory():
        user = conversation_runtime._store_user_memory(
            "op_user", "Run diagnostics", "fixture", "session", continuity_lane="operator",
        )
        assistant = conversation_runtime._store_assistant_memory(
            "op_assistant", "The visible action was proposed.", "fixture", LocalModelConfig(), "session",
            continuity_lane="operator",
        )
        rows = memory.load_memories()
    require(len(rows) == 2, "automatic memory fixture did not write two rows")
    for row in (user, assistant):
        require(row.get("relationship_eligible") is False, "automatic transcript memory became relationship eligible")
        require(row.get("use_in_relationship_continuity") is False, "automatic transcript memory entered relationship continuity")
        require(row.get("continuity_lane") == "operator", "continuity lane was not preserved on automatic memory")


def test_session_turn_persists_lane_without_creating_relationship_memory() -> None:
    with isolated_sessions():
        session = sessions.create_conversation_session("Mixed continuity", select_session=True)
        turn = sessions.append_conversation_turn(
            session["id"], turn_id="turn_mixed", user_message="I'm worried, run diagnostics",
            assistant_response="I can address both parts.", completion_state="completed", success=True,
            continuity_lane="mixed", relationship_memory_policy="explicit_curation_only",
        )
        history = sessions.conversation_history_for_prompt(session["id"])
    require(turn.get("continuity_lane") == "mixed", "turn lane was not persisted")
    require(turn.get("automatic_relationship_memory_created") is False, "session invented relationship memory")
    require(history[-1].get("continuity_lane") == "mixed", "prompt history lost continuity lane")
    require(history[-1].get("automatic_relationship_memory_created") is False, "history claimed automatic relationship memory")


def test_profile_and_snapshot_are_restart_deterministic() -> None:
    history = [{"user_message": "I feel unsure.", "assistant_response": "We can take it slowly.", "continuity_lane": "relational"}]
    first_profile = continuity_policy.classify_relationship_personality_continuity("tell me more", history)
    second_profile = continuity_policy.classify_relationship_personality_continuity("tell me more", json.loads(json.dumps(history)))
    first_snapshot = relationship_continuity.build_relationship_continuity_snapshot(_relationship_memories(), {"current_state": {}}, user_message="tell me more", interaction_profile=first_profile)
    second_snapshot = relationship_continuity.build_relationship_continuity_snapshot(json.loads(json.dumps(_relationship_memories())), {"current_state": {}}, user_message="tell me more", interaction_profile=second_profile)
    require(first_profile.to_dict() == second_profile.to_dict(), "profile changed across reconstructed history")
    require(first_snapshot.public_summary() == second_snapshot.public_summary(), "snapshot changed across reconstructed state")


def test_curation_summary_reports_no_conflicts_after_explicit_correction() -> None:
    with isolated_memory():
        curation.create_relationship_memory("nickname", "Marcus prefers A.")
        curation.create_relationship_memory("nickname", "Marcus prefers B.")
        curation.create_relationship_memory("user_mood", "Marcus feels tired.")
        curation.create_relationship_memory("user_mood", "Marcus feels calm.")
        summary = curation.relationship_memory_curation_summary()
    require(summary.get("singleton_conflicts") == 0, f"curation left singleton conflicts: {summary}")
    require(summary.get("single_current_nickname") and summary.get("single_current_user_mood"), "singleton policy metadata missing")
    require(summary.get("writes_on_read") is False and summary.get("personality_mutation") is False, "summary boundary drifted")


def test_permanent_deletion_boundary_remains_explicit_and_content_removing() -> None:
    source = (AGENT / "relationship_memory_curation.py").read_text(encoding="utf-8")
    for token in (
        'if str(confirmation or "").strip() != "DELETE"',
        'if _curation_state(memory) != "retracted"',
        'delete_memory_vector_verified(memory_id)',
        '"cleanup_complete": True',
        '"content_removed": True',
        '"relationship_eligible": False',
    ):
        require(token in source, f"permanent deletion boundary token disappeared: {token}")


def test_dashboard_explains_stable_guard_and_singleton_correction() -> None:
    with isolated_sessions():
        sessions.create_conversation_session("Continuity UI", select_session=True)
        html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    for token in (
        "Stable personality guard active",
        "A new nickname supersedes an older current nickname",
        "Restore makes the selected nickname or mood current",
        "Operator-only turns suppress personal cue content",
        f"data-chat-version='{release_metadata.RUNTIME_VERSION_TAG}-",
    ):
        require(token in html, f"continuity UI omitted {token}")


def test_rendered_javascript_syntax() -> None:
    with isolated_sessions():
        sessions.create_conversation_session("Continuity JavaScript", select_session=True)
        html = dashboard_chat_console.render_realtime_chat_panel(None, compact=True)
    scripts: list[str] = []
    cursor = 0
    while True:
        start = html.find("<script>", cursor)
        if start < 0:
            break
        end = html.find("</script>", start)
        require(end >= 0, "rendered script tag is unclosed")
        scripts.append(html[start + 8:end])
        cursor = end + 9
    require(scripts, "no rendered JavaScript found")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-8-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_policy_module_has_no_provider_memory_or_mutation_dependencies() -> None:
    source = (AGENT / "relationship_personality_continuity.py").read_text(encoding="utf-8")
    for token in ("store_memory", "mutate_memories", "LocalModelClient", "requests.", "urllib", "subprocess"):
        require(token not in source, f"continuity policy acquired forbidden dependency: {token}")
    require("mutates_personality\": False" in source, "policy stopped declaring no personality mutation")
    require("writes_memory\": False" in source, "policy stopped declaring no memory write")


def test_current_metadata_docs_and_release_registration_are_aligned() -> None:
    current_parts = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current_parts >= (1080, 8), "runtime metadata predates the v1080.8 foundation")
    current_tag = f"v{release_metadata.RUNTIME_VERSION}"
    require(current_tag in (ROOT / "data/settings.json").read_text(encoding="utf-8"), f"data/settings.json omits current runtime {current_tag}")
    for relative in ("data/workspaces/active_project.json", "data/workspaces/projects.json"):
        require(not (ROOT / relative).exists(), f"source-only package contains private runtime workspace file: {relative}")
    for relative in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"):
        require(current_tag in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits current runtime {current_tag}")
    verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"relationship-personality-continuity-fixtures"') == 1, "v1080.8 stage is not registered exactly once")
    require(verify.count('"tools/v1080_8_relationship_personality_continuity_tests.py"') == 1, "v1080.8 suite path is not registered exactly once")


def test_source_tree_remains_source_only() -> None:
    require(not (ROOT / "data" / "projects.json").exists(), "source tree contains data/projects.json")
    forbidden = (
        "data/chat_actions", "data/conversation_sessions", "data/approvals", "data/notifications",
        "data/tasks.json", "data/memories.json", ".venv", "__pycache__",
    )
    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()]
    for token in forbidden:
        require(not any(token in path for path in paths), f"source tree contains forbidden runtime token: {token}")


TESTS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("interaction_lanes_are_deterministic_and_narrow", test_interaction_lanes_are_deterministic_and_narrow),
    ("short_follow_up_inherits_relational_lane_without_becoming_operator_work", test_short_follow_up_inherits_relational_lane_without_becoming_operator_work),
    ("operator_follow_up_stays_operator_only", test_operator_follow_up_stays_operator_only),
    ("operator_prompt_suppresses_private_relationship_cues", test_operator_prompt_suppresses_private_relationship_cues),
    ("mixed_prompt_keeps_personal_and_operator_work_separate", test_mixed_prompt_keeps_personal_and_operator_work_separate),
    ("legacy_singleton_conflicts_choose_newest_without_mutating_input", test_legacy_singleton_conflicts_choose_newest_without_mutating_input),
    ("new_nickname_transactionally_supersedes_old_without_deletion", test_new_nickname_transactionally_supersedes_old_without_deletion),
    ("new_current_mood_clears_previous_and_make_current_is_exclusive", test_new_current_mood_clears_previous_and_make_current_is_exclusive),
    ("automatic_conversation_memories_are_relationship_ineligible", test_automatic_conversation_memories_are_relationship_ineligible),
    ("session_turn_persists_lane_without_creating_relationship_memory", test_session_turn_persists_lane_without_creating_relationship_memory),
    ("profile_and_snapshot_are_restart_deterministic", test_profile_and_snapshot_are_restart_deterministic),
    ("curation_summary_reports_no_conflicts_after_explicit_correction", test_curation_summary_reports_no_conflicts_after_explicit_correction),
    ("permanent_deletion_boundary_remains_explicit_and_content_removing", test_permanent_deletion_boundary_remains_explicit_and_content_removing),
    ("dashboard_explains_stable_guard_and_singleton_correction", test_dashboard_explains_stable_guard_and_singleton_correction),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("policy_module_has_no_provider_memory_or_mutation_dependencies", test_policy_module_has_no_provider_memory_or_mutation_dependencies),
    ("current_metadata_docs_and_release_registration_are_aligned", test_current_metadata_docs_and_release_registration_are_aligned),
    ("source_tree_remains_source_only", test_source_tree_remains_source_only),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks: list[dict[str, str]] = []
    passed = 0
    for name, test in TESTS:
        try:
            test()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    report = {
        "suite": "v1080.8-relationship-personality-continuity",
        "passed": passed,
        "total": len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "relationship_memory_auto_promoted": False,
        "personality_mutated": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
