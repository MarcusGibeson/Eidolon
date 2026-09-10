"""Offline coverage for bounded attempts and truthful evidence diagnostics."""
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-synthesis-timing-")
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / "conscious_agent"), str(root)]
import governed_public_web_research_adapter as adapter_module
import local_model
from settings_manager import DEFAULT_SETTINGS
from dashboard_chat_console import _turn_timestamp, _render_session_transcript

checks = []
def check(value, name):
    assert value, name
    checks.append(name)

configs = []
class Client:
    def __init__(self, config): configs.append(config)
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def generate(self, prompt): return '{"findings":[]}'

with patch.object(local_model, "LocalModelClient", Client), patch("settings_manager.load_settings", return_value=DEFAULT_SETTINGS):
    adapter_module._single_synthesis_request("test", temperature=0, max_tokens=640, timeout_seconds=10)
check(configs[0].retry_limit == 0, "no_hidden_provider_retries")
check(configs[0].structured_json, "native_json_mode")
check(configs[0].connect_timeout_seconds + configs[0].read_timeout_seconds <= 10, "remaining_budget_caps_timeouts")
check(configs[0].generation.max_tokens == 640, "bounded_output")
check(not _turn_timestamp({}), "missing_history_time_not_invented")
check(not _turn_timestamp({"created_at": "<script>"}), "invalid_time_rejected")
check("[8:24am]" in _turn_timestamp({"created_at": "2026-09-07T08:24:25"}), "compact_history_time")
check("datetime='2026-09-07T08:24:25'" in _turn_timestamp({"created_at": "2026-09-07T08:24:25"}), "historical_timestamp_preserved")
from desktop_shell import _chat_timestamp
import time
for hour, expected in ((0, '12:19am'), (12, '12:19pm'), (14, '2:19pm')):
    check(_chat_timestamp(time.struct_time((2026,9,7,hour,19,35,0,250,-1))) == '[' + expected + ']', 'desktop_compact_hour_' + str(hour))
from chat_time_labels import day_label
for day, suffix in ((1,'st'),(2,'nd'),(3,'rd'),(7,'th'),(11,'th'),(12,'th'),(13,'th'),(21,'st'),(22,'nd'),(23,'rd'),(31,'st')):
    check(day_label(2026,7,day) == 'July ' + str(day) + suffix + ', 2026', 'ordinal_' + str(day))
turn = {'created_at':'2026-09-07T19:14:00','user_message':'Hi','success':True,'assistant_response':'Hello','completion_state':'completed'}
history = _render_session_transcript('', [turn, turn, {**turn, 'created_at':'2026-09-08T00:01:00'}])
check(history.count("class='chat-date-divider'") == 2, 'one_divider_per_day')
check('September 7th, 2026' in history and 'September 8th, 2026' in history, 'day_boundary_labels')
check('</time> Marcus:' in history and '</time> Eidolon:' in history, 'time_precedes_speaker')
html = _render_session_transcript("", [{"id":"a", "created_at":"2026-09-07T08:24:25", "user_message":"hello", "success":True, "assistant_response":"hi", "completion_state":"completed"}])
check(html.count("<time ") == 2, "both_speakers_have_timestamps")
check("data-session-turn-id='a'" in html, "turn_identity_rendered")

fixtures = runpy.run_path(str(root / "tools/v2730_9_4_research_trial_repair_tests.py"))
def prepared():
    adapter = fixtures["NativeAdapterProbe"]()
    observation = adapter.observe(fixtures["source_candidate"], plan={"plan_digest":"b"*64}, max_bytes=4096, timeout_seconds=1)
    return adapter, observation
adapter, observation = prepared()
calls = []
adapter.synthesizer = lambda prompt: calls.append(prompt) or {}
adapter.set_synthesis_time_budget(0)
result = adapter.synthesize(decomposition={"requested_result_count":0}, citations=[observation])
check(result["provider_request_count"] == 0 and not calls, "expired_budget_makes_no_provider_call")
adapter, observation = prepared()
calls = []
adapter.synthesizer = lambda prompt: calls.append(prompt) or {}
adapter.set_synthesis_time_budget(0)
for method in (adapter.discover_candidates, adapter.repair_candidate_discovery):
    result = method(decomposition={"requested_result_count":3}, citations=[observation])
    check(result["provider_request_count"] == 0 and not calls, method.__name__ + "_respects_expired_budget")
adapter, observation = prepared()
def fail(prompt): raise TimeoutError("test")
adapter.synthesizer = fail
result = adapter.synthesize(decomposition={"requested_result_count":0}, citations=[observation])
check(result["provider_request_count"] == 1, "failed_contact_counted_once")
check(not result["generation_retry_used"], "timeout_is_not_silently_replayed")
print(json.dumps({"ok":True, "passed":len(checks), "checks":checks}))
