from __future__ import annotations

"""G-EVID1: the run procedure.

DRAFT, NOT FROZEN, AND NOT RUN. Executing the experiment requires an explicit operator confirmation; without it this
module builds prompts, estimates cost and validates the corpus, and calls no model.

One model call per (proposition, evidence) pair per repeat. The model produces a provisional assessment only: the
prompt never contains the words that name a disposition, so the model is never invited to choose one. Stages 2 and 3
live in ``g_evid1_policy`` and run after the call, deterministically.
"""

import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "G-EVID1"
CONTRACT_VERSION = "g-evid1.0"

# Measured on this host from the two completed local reviews (qwen3.8:27b, ollama): generation is output-token bound
# at a median 4.0-5.1 tokens/second with no significant fixed overhead per call.
MEASURED_TOKENS_PER_SECOND = 4.5
ESTIMATED_OUTPUT_TOKENS = 200

PROMPT_TEMPLATE = (
    "You are assessing whether one passage of evidence bears on one proposition. Report only what the passage "
    "itself establishes. Do not decide what should be done about it, and do not draw on anything you know beyond "
    "the passage.\n\n"
    "Proposition {proposition_id}: {proposition}\n"
    "Purpose: {purpose}\n\n"
    "Evidence {evidence_id}:\n---\n{evidence}\n---\n\n"
    "Reply with one JSON object and nothing else:\n"
    "{{\n"
    '  "proposition_id": "{proposition_id}",\n'
    '  "evidence_id": "{evidence_id}",\n'
    '  "relation": one of supports, contradicts, partial, irrelevant, unclear,\n'
    '  "scope": one of match, evidence_narrower, evidence_broader, mismatch, unclear,\n'
    '  "temporal": one of compatible, evidence_superseded, evidence_predates, unclear,\n'
    '  "quotes": up to 2 exact spans copied from the evidence, each 8 to 200 characters,\n'
    '  "confidence": one of low, medium, high\n'
    "}}\n\n"
    "relation describes what the passage does to the proposition. scope describes whether the passage covers the "
    "same subject and range as the proposition. temporal describes whether the passage still applies. Every quote "
    "must appear in the evidence above, character for character."
)


def load_corpus(path: Path | None = None) -> list[dict[str, Any]]:
    payload = json.loads((path or DATA / "corpus.json").read_text(encoding="utf-8"))
    return list(payload["items"])


def build_prompt(item: Mapping[str, Any]) -> str:
    return PROMPT_TEMPLATE.format(proposition_id=item["proposition_id"], proposition=item["proposition"],
                                  purpose=item["intended_use"], evidence_id=item["evidence_id"],
                                  evidence=item["evidence"])


def estimate(items: list[dict[str, Any]], repeats: int) -> dict[str, Any]:
    """Cost estimate from the measured generation rate. No model is contacted."""
    prompts = [build_prompt(i) for i in items]
    chars = sum(len(p) for p in prompts)
    calls = len(items) * repeats
    seconds = calls * (ESTIMATED_OUTPUT_TOKENS / MEASURED_TOKENS_PER_SECOND)
    return {"items": len(items), "repeats": repeats, "model_calls": calls,
            "prompt_chars_total": chars, "prompt_chars_median": sorted(len(p) for p in prompts)[len(prompts) // 2],
            "estimated_prompt_tokens_each": round(sorted(len(p) for p in prompts)[len(prompts) // 2] / 3.62),
            "assumed_output_tokens_each": ESTIMATED_OUTPUT_TOKENS,
            "assumed_tokens_per_second": MEASURED_TOKENS_PER_SECOND,
            "estimated_seconds": round(seconds), "estimated_minutes": round(seconds / 60, 1)}


def _parse(reply: str) -> Any:
    """The model's reply as an object, or None. A reply that is not one JSON object is structurally invalid."""
    text = str(reply or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def run(*, confirmed: bool, repeats: int = 1, call_model: Callable[[str], tuple[str, dict]] | None = None,
        out_dir: Path | None = None, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run the experiment once. Refuses without an explicit operator confirmation.

    ``call_model`` is injected by the contract tests; production passes None and the configured local model is
    resolved here, unchanged.
    """
    if not confirmed:
        raise PermissionError("g_evid1_run_requires_explicit_operator_confirmation")

    import g_evid1_policy as policy

    items = items if items is not None else load_corpus()
    out = out_dir or (DATA / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(parents=True, exist_ok=True)

    if call_model is None:
        import sys

        sys.path.insert(0, str(ROOT / "conscious_agent"))
        import experiment_review as er

        identity = er.model_identity()
        raw_call = er.production_call_model()

        def call_model(prompt: str) -> tuple[str, dict]:  # noqa: F811 - production path
            reply, meta = raw_call(prompt, 350)
            return reply, meta
    else:
        identity = {"model": "injected", "provider": "injected", "context_size": 0, "resolved_config_sha256": "0" * 64}

    started = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    observations: list[dict[str, Any]] = []
    for repeat in range(1, repeats + 1):
        for item in items:
            prompt = build_prompt(item)
            began = time.monotonic()
            reply, meta = call_model(prompt)
            seconds = time.monotonic() - began
            assessment = _parse(reply)
            decision = policy.assess_to_disposition(assessment, proposition_id=item["proposition_id"],
                                                    evidence_id=item["evidence_id"], evidence_text=item["evidence"])
            metrics = (meta or {}).get("metrics") or {}
            observations.append({
                "item_id": item["item_id"], "repeat": repeat, "model_call": True,
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "raw_reply": str(reply)[:4000], "assessment": assessment if isinstance(assessment, dict) else None,
                "validation": decision["validation"], "disposition": decision["disposition"],
                "rule": decision["rule"], "reason": decision["reason"], "belief_effects": policy.BELIEF_EFFECTS,
                "seconds": round(seconds, 2), "prompt_tokens": int(metrics.get("prompt_eval_count") or 0),
                "output_tokens": int(metrics.get("eval_count") or 0),
            })

    finished = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    conditions = {
        "contract_version": CONTRACT_VERSION, "experiment_id": "G-EVID1", "started": started, "finished": finished,
        "repeats": repeats, "items": len(items), "model_identity": identity,
        "prompt_template_sha256": hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest(),
        "corpus_sha256": hashlib.sha256((DATA / "corpus.json").read_bytes()).hexdigest(),
        "host": platform.node(), "python": platform.python_version(), "belief_effects": policy.BELIEF_EFFECTS,
    }
    payload = {"conditions": conditions, "observations": observations}
    (out / "observations.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="G-EVID1 run procedure (estimate by default; running needs confirmation).")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--confirm-run", action="store_true", help="actually call the local model")
    args = parser.parse_args()
    items = load_corpus()
    if not args.confirm_run:
        print(json.dumps({"ran": False, "reason": "no --confirm-run given", **estimate(items, args.repeats)}, indent=1))
        return 0
    payload = run(confirmed=True, repeats=args.repeats)
    print(json.dumps({"ran": True, "observations": len(payload["observations"])}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
