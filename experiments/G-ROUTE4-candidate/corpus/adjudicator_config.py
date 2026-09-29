"""The G-ROUTE4 adjudicator configuration (O2), PREPARED for the seal commit. Nothing here contacts any model.

O2 freezes, in the seal commit and before the first session: the adjudicator model id and version, the prompt
template and its digest, and the tool settings and input rendering, identical for A′, B′ and reserve sessions.
This module builds that configuration deterministically and digests it. It is not frozen until the seal commit,
and the two fields listed under operator_confirmation_required must be confirmed by the operator first.

The adjudicator sees exactly what the local models see: the frozen G-ROUTE3 rendering (tools/g_route3_contract.py
render_prompt) of the model-facing fixture, with the frozen G-ROUTE1 prompt profile as the system text. It never
sees gold, reference outputs, rationales or the authoring ledger: render_request takes a model-facing fixture only.

    python -B adjudicator_config.py            # print the configuration and its digest
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
PROFILES_PATH = ROOT / "experiments/G-ROUTE1-candidate/prompt_profiles.json"
RENDER_TOOL = ROOT / "tools/g_route3_contract.py"
USER_TEMPLATE = "{FIXTURE_PROMPT}\n\nINPUT:\n{CANONICAL_INPUT_JSON}"
SYSTEM_TEMPLATE = "{PROMPT_PROFILE_TEXT}"
MODEL_FACING_KEYS = {"consequence_risk", "fixture_id", "input", "prompt", "task_class", "title", "validator_profile"}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_sha256(path):
    """sha256 of a text file with line endings normalized to LF (independent of a checkout's core.autocrlf)."""
    return sha256_bytes(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render_request(fixture):
    """The adjudicator request for one model-facing fixture: {'system', 'user'}. Refuses anything else."""
    if set(fixture) != MODEL_FACING_KEYS:
        raise ValueError("adjudicator input must be a model-facing fixture only (no gold or ledger keys)")
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    return {"system": SYSTEM_TEMPLATE.replace("{PROMPT_PROFILE_TEXT}", str(profiles[fixture["validator_profile"]])),
            "user": USER_TEMPLATE.replace("{FIXTURE_PROMPT}", str(fixture["prompt"]))
                                 .replace("{CANONICAL_INPUT_JSON}", canonical(fixture["input"]))}


def config():
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    body = {
        "schema_version": "g-route4.adjudicator-config.v1",
        "status": "prepared for the seal commit; NOT frozen; no adjudicator or model has been contacted",
        "operator_confirmation_required": ["adjudicator.model_id", "adjudicator.channel"],
        "adjudicator": {
            "provider": "Anthropic",
            "model_id": "claude-opus-5-5",
            "model_version_rule": "the exact model id string above, never an alias or a 'latest' pointer; any "
                                  "change is a recorded operator decision and every fixture is re-adjudicated "
                                  "from scratch",
            "channel": "Anthropic Messages API: one request per invocation, with no prior turns, no memory, no "
                       "project context and no files",
        },
        "sessions": {
            "one_fixture_per_session": True, "fresh_session_per_invocation": True,
            "tools": [], "attachments": [],
            "blind_to": ["gold", "reference outputs", "rationales", "the authoring ledger", "G-ROUTE3 outputs",
                         "the research diagnosis"],
            "identical_for": ["A′ main", "B′ main", "reserve"],
        },
        "settings": {
            "temperature": 0, "thinking": "disabled", "max_output_tokens": 2048, "stop_sequences": [],
            "max_output_tokens_note": "larger than the local models' 350-token cap on purpose: adjudication tests "
                                      "derivability of gold, and a truncated adjudicator answer would be read as "
                                      "a disagreement for the wrong reason",
            "retry": "only a no-answer (a session error with no final message) is retried, once; a second "
                     "no-answer counts as a disagreement",
            "binding_answer": "the first logged invocation that produced a final message",
            "parse_failure": "an output that fails operational parsing counts as a disagreement",
        },
        "input_rendering": {
            "rule": "identical to the models' rendering: tools/g_route3_contract.py render_prompt",
            "system": "the G-ROUTE1 prompt profile text for the fixture's validator_profile",
            "user": "the fixture prompt, then a blank line, 'INPUT:', a newline, and the fixture input as JSON with "
                    "sorted keys, separators (',', ':') and ensure_ascii false",
            "render_tool_sha256": file_sha256(RENDER_TOOL),
            "prompt_profiles_sha256": file_sha256(PROFILES_PATH),
            "file_digest_rule": "sha256 of the file with line endings normalized to LF",
        },
        "prompt_template": {
            "system": SYSTEM_TEMPLATE, "user": USER_TEMPLATE,
            "template_sha256": sha256_bytes(canonical({"system": SYSTEM_TEMPLATE, "user": USER_TEMPLATE}).encode()),
            "profile_sha256": {name: sha256_bytes(text.encode("utf-8")) for name, text in sorted(profiles.items())
                               if name != "coding.v1"},
        },
        "judgement": "disagreement means the answer fails the frozen semantic validator "
                     "(tools/g_route3_semantics.py validate_fixture_output) against the sealed gold",
    }
    body["config_sha256"] = sha256_bytes(canonical(body).encode("utf-8"))
    return body


if __name__ == "__main__":
    print(json.dumps(config(), indent=1, ensure_ascii=False))
