from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import dashboard_chat_console
import release_metadata


class Failure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def dashboard_source() -> str:
    return (AGENT / "dashboard_chat_console.py").read_text(encoding="utf-8")


def rendered_panel() -> str:
    return dashboard_chat_console.render_realtime_chat_panel(None, compact=True)


def rendered_script() -> str:
    html = rendered_panel()
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
    return "\n".join(scripts)


def test_composer_latches_before_async_coordination() -> None:
    source = dashboard_source()
    latch = source.find("composerSubmissionPending = true;")
    confirmation = source.find("if (!await confirmConversationControl())", latch)
    bubble = source.find("bubble('user', message)", latch)
    require(latch >= 0 and confirmation > latch and bubble > confirmation, "composer latch does not precede async ownership confirmation and visible insertion")
    require("composerSubmissionPending || activeController || activeOperationId" in source, "duplicate-submit guard is incomplete")
    require("Nothing was submitted twice." in source, "duplicate-submit presentation is missing")


def test_enter_and_beforeinput_share_submission_latch() -> None:
    source = dashboard_source()
    require("requestComposerSubmitOnce(event);" in source, "keydown and beforeinput do not share the submit-once resolver")
    require(source.count("requestComposerSubmitOnce(event);") == 2, "keydown and beforeinput are not both protected by the same latch")
    require("compositionActive || event.isComposing || event.keyCode === 229" in source, "IME composition protection regressed")
    require("allowNextLineBreak || compositionActive || event.isComposing" in source, "Shift+Enter or composition handling regressed")


def test_send_control_reflects_acceptance_and_stream_state() -> None:
    source = dashboard_source()
    require("!!activeOperationId || !!activeController || composerSubmissionPending" in source, "Send is not disabled across acceptance, streaming, and persisted operation states")
    require("composerSubmissionPending = false;" in source, "submission latch is never released")


def test_attention_refresh_is_single_flight() -> None:
    source = dashboard_source()
    require("if (attentionRefreshPromise) return attentionRefreshPromise;" in source, "attention refresh can overlap")
    require("attentionList.setAttribute('aria-busy', 'true')" in source, "attention busy state is missing")
    require("attentionList.removeAttribute('aria-busy')" in source, "attention busy state is not cleared")


def test_catalog_refresh_is_latest_request_wins() -> None:
    source = dashboard_source()
    for token in (
        "const sequence = ++catalogRefreshSequence;",
        "catalogRefreshController.abort();",
        "signal:controller.signal",
        "if (sequence !== catalogRefreshSequence) return false;",
        "Existing results were preserved",
    ):
        require(token in source, f"catalog latest-request-wins behavior omitted {token}")


def test_catalog_clear_is_in_place_and_non_navigating() -> None:
    html = rendered_panel()
    require("id='conversation-catalog-clear'" in html, "catalog clear control is missing")
    require("href='/chat-console'>Clear" not in html, "catalog clear still causes a full navigation")
    script = rendered_script()
    for token in ("catalogQuery.value = ''", "catalogArchived.checked = false", "refreshConversationOrganizer(0)"):
        require(token in script, f"in-place catalog clear omitted {token}")


def test_tab_scoped_usability_state_is_bounded() -> None:
    source = dashboard_source()
    require("window.sessionStorage.setItem(usabilityStorageKey" in source, "usability state is not tab scoped")
    require("window.localStorage.setItem(usabilityStorageKey" not in source, "usability state was made long-lived in localStorage")
    require("catalog_query: String(state.catalog_query || '').slice(0, 160)" in source, "catalog query is not bounded")
    require("Math.min(1000000" in source, "catalog offset is not bounded")


def test_usability_state_contains_no_results_or_transcripts() -> None:
    source = dashboard_source()
    capture_start = source.index("function captureUsabilityState()")
    capture_end = source.index("function persistUsabilityState()", capture_start)
    block = source[capture_start:capture_end]
    for forbidden in ("transcript", "snippet", "items", "assistant", "user_message", "action_output", "credential"):
        require(forbidden not in block, f"usability state captures private/result field {forbidden}")
    for required in ("open_surfaces", "catalog_query", "include_archived", "catalog_offset"):
        require(required in block, f"usability state omitted {required}")


def test_escape_closes_all_temporary_drawers() -> None:
    source = dashboard_source()
    selector_match = re.search(r"document\.querySelectorAll\('([^']+)'\)\.forEach", source)
    require(selector_match is not None, "temporary-surface selector is missing")
    selector = selector_match.group(1)
    for token in (".chat-attention-center[open]", ".chat-continuity-curation[open]", ".chat-session-organizer[open]", ".chat-diagnostics-drawer[open]"):
        require(token in selector, f"Escape does not close {token}")
    require("if (closed) persistUsabilityState();" in source, "Escape closure is not persisted")


def test_surface_ids_and_restore_contract_render() -> None:
    html = rendered_panel()
    for token in (
        "id='chat-tools-drawer'",
        "id='chat-session-organizer'",
        "id='chat-continuity-panel'",
        "id='chat-continuity-curation'",
        "id='chat-diagnostics-drawer'",
    ):
        require(token in html, f"stable surface ID omitted {token}")
    require("restoreUsabilityState()" in html, "tab UI restoration is not rendered")


def test_scroll_restore_reconciles_jump_latest_control() -> None:
    source = dashboard_source()
    start = source.index("function restorePresentation")
    end = source.index("async function persistDraft", start)
    block = source[start:end]
    require("updateJumpLatestButton();" in block, "scroll restoration does not reconcile jump-to-latest visibility")
    require("scroll_from_bottom_px" in block and "follow_latest" in block, "scroll restoration contract regressed")


def test_accepted_draft_generation_advances_once() -> None:
    source = dashboard_source()
    start = source.index("function clearAcceptedDraft")
    end = source.index("function applySessionSnapshot", start)
    block = source[start:end]
    require(block.count("draftSaveSequence += 1;") == 1, "accepted-draft clear advances the generation more than once")
    require("newer draft preserved" in block, "rapid post-send typing preservation regressed")


def test_rendered_javascript_syntax() -> None:
    script = rendered_script()
    with tempfile.TemporaryDirectory(prefix="eidolon-v1080-9-js-") as raw:
        path = Path(raw) / "rendered.js"
        path.write_text(script, encoding="utf-8")
        try:
            result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            return
        require(result.returncode == 0, f"rendered JavaScript syntax failed: {result.stderr.strip()}")


def test_narrow_layout_and_accessibility_contract() -> None:
    source = (AGENT / "dashboard_chat_styles.py").read_text(encoding="utf-8")
    html = rendered_panel()
    require("@media (max-width:620px)" in source, "narrow layout contract is missing")
    require("aria-live='polite'" in html, "polite live status region is missing")
    script = rendered_script()
    require("setAttribute('aria-busy', 'true')" in script, "async read-only surfaces do not expose busy state")


def test_current_metadata_docs_and_release_registration_are_aligned() -> None:
    current_parts = tuple(int(part) for part in release_metadata.RUNTIME_VERSION.split("."))
    require(current_parts >= (1080, 9), "runtime metadata predates the v1080.9 usability foundation")
    current = f"v{release_metadata.RUNTIME_VERSION}"
    require(release_metadata.RUNTIME_VERSION_TAG == current, "runtime version tag drifted from the current version")
    require("v1080.9" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"), "v1080.9 historical milestone disappeared")
    settings = json.loads((ROOT / "data/settings.json").read_text(encoding="utf-8"))
    require(bool(settings.get("settings_version")), "source settings template has no schema version")
    for relative in ("data/workspaces/active_project.json", "data/workspaces/projects.json"):
        require(not (ROOT / relative).exists(), f"source-only package contains private runtime workspace file: {relative}")
    for relative in ("README.md", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"):
        require(current in (ROOT / relative).read_text(encoding="utf-8"), f"{relative} omits {current}")
    verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    require(verify.count('"desktop-alpha-usability-consolidation-fixtures"') == 1, "v1080.9 stage is not registered exactly once")
    require(verify.count('"tools/v1080_9_desktop_alpha_usability_consolidation_tests.py"') == 1, "v1080.9 suite path is not registered exactly once")


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
    ("composer_latches_before_async_coordination", test_composer_latches_before_async_coordination),
    ("enter_and_beforeinput_share_submission_latch", test_enter_and_beforeinput_share_submission_latch),
    ("send_control_reflects_acceptance_and_stream_state", test_send_control_reflects_acceptance_and_stream_state),
    ("attention_refresh_is_single_flight", test_attention_refresh_is_single_flight),
    ("catalog_refresh_is_latest_request_wins", test_catalog_refresh_is_latest_request_wins),
    ("catalog_clear_is_in_place_and_non_navigating", test_catalog_clear_is_in_place_and_non_navigating),
    ("tab_scoped_usability_state_is_bounded", test_tab_scoped_usability_state_is_bounded),
    ("usability_state_contains_no_results_or_transcripts", test_usability_state_contains_no_results_or_transcripts),
    ("escape_closes_all_temporary_drawers", test_escape_closes_all_temporary_drawers),
    ("surface_ids_and_restore_contract_render", test_surface_ids_and_restore_contract_render),
    ("scroll_restore_reconciles_jump_latest_control", test_scroll_restore_reconciles_jump_latest_control),
    ("accepted_draft_generation_advances_once", test_accepted_draft_generation_advances_once),
    ("rendered_javascript_syntax", test_rendered_javascript_syntax),
    ("narrow_layout_and_accessibility_contract", test_narrow_layout_and_accessibility_contract),
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
        "suite": "v1080.9-desktop-alpha-usability-consolidation",
        "passed": passed,
        "total": len(TESTS),
        "status": "pass" if passed == len(TESTS) else "fail",
        "checks": checks,
        "native_provider_contacted": False,
        "model_management_performed": False,
        "runtime_state_mutated": False,
        "release_authorized": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
