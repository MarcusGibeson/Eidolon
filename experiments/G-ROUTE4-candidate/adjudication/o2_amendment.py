"""G-ROUTE4 O2 post-seal amendment (operator decision 2026-09-29), recorded before any adjudicator contact.

The sealed O2 configuration (sealed/adjudicator_config.json, sha256 1658b9a2...) stays unchanged as the historical
frozen configuration. Anthropic's published API contract for claude-opus-5-5, checked 2026-09-29, makes two of its
request parameters invalid: thinking cannot be disabled, and a non-default temperature is rejected with HTTP 400. This
module derives the amended configuration from the sealed one deterministically: only the settings the operator
decided change; the model, channel, prompt template, input rendering, blindness, retry, binding-answer and
parse-failure rules are carried over unchanged. Every adjudication request and result is bound to the amended digest.

    python -B o2_amendment.py            # verify the committed amended configuration and print its digest
    python -B o2_amendment.py --write    # (re)write adjudicator_config_amended.json from the sealed configuration
"""

import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEALED_CONFIG = ROOT / "experiments/G-ROUTE4-candidate/sealed/adjudicator_config.json"
AMENDED_CONFIG = HERE / "adjudicator_config_amended.json"
SEALED_CONFIG_SHA256 = "1658b9a2a32fa176c8ca679d5407725b17379902610869fc3cdc91d03df88029"
SEAL_COMMIT = "50e6b46994299ffd71c97aa3f81f30637efaba1c"
AUDIT_SAMPLE_COMMIT = "29f5a477693d703699af62f9fc0e0945c9c66be2"
DECISION_DATE = "2026-09-29"
MODEL = "claude-opus-5-5"
ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
EFFORT = "high"
MAX_TOKENS = 32000


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(body):
    return hashlib.sha256(canonical({k: v for k, v in body.items() if k != "config_sha256"}).encode("utf-8")).hexdigest()


def sealed_config():
    cfg = json.loads(SEALED_CONFIG.read_text(encoding="utf-8"))
    if cfg.get("config_sha256") != SEALED_CONFIG_SHA256 or digest(cfg) != SEALED_CONFIG_SHA256:
        raise SystemExit("sealed O2 configuration does not match its frozen digest; refusing to amend")
    return cfg


EVIDENCE = [
    {"url": "https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5", "checked": DECISION_DATE,
     "finding": "Claude Opus 5.5: thinking is always on; a request that sets thinking {\"type\": \"disabled\"} "
                "returns a 400 invalid_request_error. Omitting thinking is equivalent to adaptive thinking."},
    {"url": "https://platform.claude.com/docs/en/models/opus-5-5/overview", "checked": DECISION_DATE,
     "finding": "Model id claude-opus-5-5 (pinned snapshot); adaptive thinking always on; default effort medium; "
                "max output 128K tokens."},
    {"url": "https://platform.claude.com/docs/en/build-with-claude/thinking", "checked": DECISION_DATE,
     "finding": "On Claude Opus 5.5 (and other current models) non-default temperature, top_p or top_k values return "
                "a 400 error on every request. max_tokens includes all thinking and is a strict limit."},
    {"url": "https://platform.claude.com/docs/en/build-with-claude/effort", "checked": DECISION_DATE,
     "finding": "Effort is set as top-level output_config.effort, no beta header; levels low, medium, high, xhigh, "
                "max; claude-opus-5-5 defaults to medium."},
    {"url": "https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback", "checked": DECISION_DATE,
     "finding": "Server-side fallback is opt-in: it runs only when a request sets `fallbacks` with the beta header "
                "server-side-fallback-2026-07-01. A classifier refusal is an HTTP 200 message with "
                "stop_reason \"refusal\"."},
]


def amended_config():
    sealed = sealed_config()
    body = {k: v for k, v in copy.deepcopy(sealed).items() if k != "config_sha256"}
    body["schema_version"] = "g-route4.adjudicator-config.amended.v1"
    body["status"] = ("AMENDED after the seal and before any adjudicator contact, by recorded operator decision "
                      f"({DECISION_DATE}); binding for every G-ROUTE4 adjudication session")
    body["amends"] = {
        "sealed_config_path": "experiments/G-ROUTE4-candidate/sealed/adjudicator_config.json",
        "sealed_config_sha256": SEALED_CONFIG_SHA256,
        "sealed_config_status": "unchanged; preserved as the historical frozen configuration",
        "seal_commit": SEAL_COMMIT, "audit_sample_commit": AUDIT_SAMPLE_COMMIT,
        "reason": "Anthropic's published API contract for claude-opus-5-5 makes two sealed request parameters "
                  "invalid: thinking \"disabled\" and temperature 0 each return HTTP 400 on every request.",
        "re_adjudication": "none required: no adjudication session had taken place when this amendment was made",
    }
    body["provider_documentation_evidence"] = EVIDENCE
    body["operator_decisions"] = list(sealed["operator_decisions"]) + [
        {"field": "settings (O2 amendment)", "value": "omit temperature and thinking; effort high; max output tokens "
         "32000; server-side fallback disabled; binding answer = concatenated text of the first final message",
         "decided_by": "operator", "date": DECISION_DATE}]
    settings = body["settings"]
    for key in ("temperature", "thinking", "max_output_tokens", "max_output_tokens_note"):
        settings.pop(key, None)
    settings.update({
        "temperature": "omitted (provider default); a non-default value returns HTTP 400 on claude-opus-5-5",
        "thinking": "omitted; adaptive thinking is always on and provider-required on claude-opus-5-5",
        "effort": EFFORT,
        "max_output_tokens": MAX_TOKENS,
        "max_output_tokens_note": "max_tokens counts thinking as well as the reply on claude-opus-5-5; 32000 leaves "
                                  "room for thinking so a reply is not cut off for the wrong reason",
        "tools": "none (no tools field is sent)",
        "server_side_fallback": "disabled: no `fallbacks` field and no anthropic-beta header are sent; a response "
                                "naming another model or reporting a fallback is an integrity stop",
        "binding_answer": "the concatenated text content (text blocks only, in order, no separator) of the first "
                          "final assistant message returned for the adjudicator slot; a refusal, malformed or "
                          "truncated final message still binds and is scored under the frozen procedure",
        "retry": "only a no-answer (a session error with no final message) is retried, once; a second no-answer "
                 "counts as a disagreement. An answer is never retried because it is unusable, surprising or "
                 "disagrees with gold",
    })
    body["request"] = {
        "channel": "Anthropic Messages API, one HTTP request per invocation, no conversation history",
        "endpoint": ENDPOINT, "method": "POST", "stream": False,
        "headers": {"anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json",
                    "x-api-key": "<operator key, loaded from a local file, never logged or committed>"},
        "body_template": {"model": MODEL, "max_tokens": MAX_TOKENS, "system": "{SYSTEM}",
                          "messages": [{"role": "user", "content": "{USER}"}], "output_config": {"effort": EFFORT}},
        "absent_fields": ["temperature", "top_p", "top_k", "thinking", "tools", "tool_choice", "fallbacks",
                          "stop_sequences", "metadata"],
        "serialization": "UTF-8 JSON, sorted keys, separators (',', ':'), ensure_ascii false; its sha256 is the "
                         "request digest recorded before the request is sent",
    }
    body["error_classification"] = {
        "final_message": "HTTP 200 whose body is a message object: binds (whatever its stop_reason)",
        "no_answer": "HTTP 408, 429, 500, 502, 503, 504 or 529 (a session error with no final message): the "
                     "slot's single permitted retry follows after the provider's retry-after (or 60 s)",
        "request_rejected": "any other HTTP status (for example 400, 401, 403, 404, 413): the batch stops; not retried",
        "not_sent": "a connection error before any request byte was sent: the batch stops; the slot is not consumed",
        "in_doubt": "any other transport failure after sending, or a crash between the write-ahead record and the "
                    "durable raw record: the batch stops and the slot is never re-sent without an operator decision",
    }
    body["config_sha256"] = digest(body)
    return body


def render_file(cfg):
    return json.dumps(cfg, indent=1, ensure_ascii=False) + "\n"


def verify():
    cfg = amended_config()
    committed = AMENDED_CONFIG.read_text(encoding="utf-8")
    if committed != render_file(cfg):
        raise SystemExit("committed amended configuration differs from the derivation")
    return cfg


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        cfg = amended_config()
        AMENDED_CONFIG.write_text(render_file(cfg), encoding="utf-8", newline="\n")
    cfg = verify()
    print(json.dumps({"amended_config_sha256": cfg["config_sha256"], "sealed_config_sha256": SEALED_CONFIG_SHA256},
                     indent=1))
