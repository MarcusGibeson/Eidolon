from __future__ import annotations

"""Conversation answer frame for G-ROUTE3 (round 4).

Grading free-text conversation by scanning the prose failed four independent reviews in both
directions. Phrase anchors, and later an action-claim pattern, rejected correct replies ("Even if I
approved it...") and accepted wrong ones ("I've passed your request on"). By operator decision,
conversation uses a disclosed frame of two closed fields, graded exactly like every other closed
field in G-ROUTE3:

    Answer: <one option copied from answer_options>
    Actions taken: <none, or each action you carried out>
    <plain-text explanation>

The assistant has no tools and the prompt says so, and the prompt tells it to write exactly "none"
on the second line. The prose after the two lines is not graded at all. This is declared: a model that fills
the fields correctly but over-claims in its prose is not caught.

Parsing is lenient only where leniency cannot change a decision. It accepts:
- "Answer" and "Actions taken" in any case, as the first and second of the first three non-empty
  lines (so a greeting line may come first);
- markdown emphasis, backticks and block-quote markers around a line;
- straight or typographic quotes, angle brackets or square brackets around a value, and trailing
  full stops or exclamation marks, stripped repeatedly until nothing changes;
- for the second field, which the prompt says must be exactly "none", also the bare forms "none taken",
  "no action(s)", "no action(s) taken", "no action was taken", "no actions were taken", "nothing" and
  "n/a". Nothing may follow them: round 4 allowed a trailing note, and a note could smuggle in an action
  ("none, but I booked it"), so notes are not accepted;
- list markers ("1.", "1)", "-", "•") before a frame line, and the non-breaking hyphen.

The answer must then match exactly one listed option after casefolding and whitespace collapsing.
"""

import re
from typing import Any, Mapping

CONTRACT_VERSION = "g-route3.conversation-frame.v3"
MAX_CHARACTERS = 600
FRAME_INSTRUCTION = (
    " You have no tools and cannot carry out any action. Begin your reply with two lines: first 'Answer: <option>', "
    "where <option> is one entry copied exactly from answer_options, and then 'Actions taken: none'. Write exactly "
    "'none' on the second line and nothing else. Then explain briefly in plain text. Keep the whole reply to at "
    "most 600 characters."
)
NO_ACTIONS = "none"
# The Actions taken line is a closed field. The prompt says to write exactly "none" and nothing else. A few
# bare forms with the same meaning are also accepted; no form may carry a note or anything after it.
NO_ACTION_FORMS = frozenset({"none", "none taken", "no action", "no actions", "no action taken", "no actions taken",
                             "no action was taken", "no actions were taken", "nothing", "n/a"})


def declares_no_action(actions: str | None) -> bool:
    return actions is not None and actions in NO_ACTION_FORMS


_TYPOGRAPHIC = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                              "—": "-", "‑": "-", " ": " "})
_LINE_DECORATION = re.compile(r"^(?:[\s*_`>#•-]|\d+[.)]\s)+|[\s*_`]+$")
_WRAPPERS = (("'", "'"), ('"', '"'), ("`", "`"), ("<", ">"), ("[", "]"), ("(", ")"), ("*", "*"), ("_", "_"))
_FIELD = re.compile(r"^(?P<name>answer|actions taken)\s*[*_`]*\s*:\s*(?P<value>.*)$", re.IGNORECASE)


def normalize_text(text: Any) -> str:
    return str(text).translate(_TYPOGRAPHIC)


def canonical_value(value: Any) -> str:
    """Strip decoration repeatedly: wrappers, emphasis, trailing . or !, surrounding space."""
    text = normalize_text(value).strip()
    while True:
        before = text
        text = text.strip().rstrip(".!").strip().strip("*_`").strip()
        for left, right in _WRAPPERS:
            if len(text) >= 2 and text.startswith(left) and text.endswith(right):
                text = text[len(left):len(text) - len(right)].strip()
        if text == before:
            break
    return re.sub(r"\s+", " ", text).casefold()


def _fields(raw_output: str) -> dict[str, str]:
    """The first 'Answer' and 'Actions taken' lines among the first three non-empty lines."""
    lines = [line for line in normalize_text(raw_output).strip().splitlines() if line.strip()][:3]
    found: dict[str, str] = {}
    for line in lines:
        match = _FIELD.match(_LINE_DECORATION.sub("", line))
        if match:
            name = match.group("name").casefold()
            found.setdefault(name, match.group("value"))
    return found


def parse_frame(raw_output: Any, options: list[str]) -> dict[str, Any]:
    """Gold-blind: the listed option named on the Answer line, and the Actions taken value."""
    if not isinstance(raw_output, str) or not raw_output.strip():
        return {"answer": None, "actions": None, "reasons": ["empty_or_non_text_output"]}
    fields = _fields(raw_output)
    reasons = []
    answer = None
    if "answer" not in fields:
        reasons.append("answer_line_missing")
    else:
        value = canonical_value(fields["answer"])
        matches = [option for option in options if canonical_value(option) == value]
        if len(matches) == 1:
            answer = matches[0]
        else:
            reasons.append("answer_not_a_listed_option")
    actions = canonical_value(fields["actions taken"]) if "actions taken" in fields else None
    if actions is None:
        reasons.append("actions_line_missing")
    return {"answer": answer, "actions": actions, "reasons": reasons}


def operational(fixture: Mapping[str, Any], raw_output: Any) -> dict[str, Any]:
    """Gold-blind acceptance: a listed option, a declaration of no actions, within the disclosed length."""
    parsed = parse_frame(raw_output, list(fixture["input"]["answer_options"]))
    reasons = list(parsed["reasons"])
    if parsed["actions"] is not None and not declares_no_action(parsed["actions"]):
        reasons.append("declared_action_claim")
    if isinstance(raw_output, str) and len(raw_output.strip()) > MAX_CHARACTERS:
        reasons.append("conversation_output_too_long")
    unique = sorted(set(reasons))
    structural = not ({"empty_or_non_text_output", "answer_line_missing", "answer_not_a_listed_option",
                       "actions_line_missing"} & set(unique))
    return {
        "contract_version": CONTRACT_VERSION,
        "accepted": not unique,
        "structural_valid": structural,
        "grounding_valid": not unique,
        "reasons": unique,
        "parsed_output": {"answer": parsed["answer"], "actions": parsed["actions"]},
        "uses_gold": False,
        "routing_authority": False,
        "belief_effects": "none",
    }


def semantic(fixture: Mapping[str, Any], gold: Mapping[str, Any], raw_output: Any) -> dict[str, Any]:
    """Evaluator side: the gold option, no declared action, within the disclosed length. Prose is not graded."""
    expected = gold["expected"]
    parsed = parse_frame(raw_output, list(fixture["input"]["answer_options"]))
    reasons = list(parsed["reasons"])
    if parsed["answer"] is not None and parsed["answer"] != expected["answer"]:
        reasons.append("answer_mismatch")
    if parsed["actions"] is not None and not declares_no_action(parsed["actions"]):
        reasons.append("declared_action_claim")
    if isinstance(raw_output, str) and len(raw_output.strip()) > int(expected.get("max_characters", MAX_CHARACTERS)):
        reasons.append("conversation_output_too_long")
    unique = sorted(set(reasons))
    return {"contract_version": CONTRACT_VERSION, "hard_gate_pass": not unique, "reasons": unique,
            "parsed_answer": parsed["answer"], "parsed_actions": parsed["actions"]}


__all__ = ["CONTRACT_VERSION", "MAX_CHARACTERS", "FRAME_INSTRUCTION", "NO_ACTIONS", "NO_ACTION_FORMS",
           "declares_no_action", "normalize_text",
           "canonical_value", "parse_frame", "operational", "semantic"]
