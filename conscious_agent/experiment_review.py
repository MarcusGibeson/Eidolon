from __future__ import annotations

"""Supervised, read-only experiment self-review (spec 2.18; coverage repairs 2.19; omission handling and hierarchical synthesis 2.20).

Given one explicitly selected, completed experiment package, Eidolon inspects it and writes a structured research
review into a separate review area. The review is a non-authoritative research artifact: it cannot change gold labels,
registered verdicts, evidence, memories, beliefs, policies, configuration, patches, experiment authorization or release
state, and this module has no code path that writes anywhere except the review's own directory in the review area.

How the review is bounded:
- The package is a directory with ``package_manifest.json``. Only the documents listed there are read. Each must lie
  inside the package directory and match its recorded SHA-256; anything else fails closed before any model call. Every
  document is required unless the manifest marks it optional before the run, and a document with a required role
  (design, corpus, raw outputs) cannot be optional.
- The local model receives text only; it has no tools and no authority. Its reply is data.
- Observation passes: each bounded document part yields observations. Each observation carries one or more exact quotes,
  each located separately in that part with its own document, line and character provenance. One quote that is not
  found rejects the whole observation, and quotes stitched together with an ellipsis are never accepted. A single
  trailing ellipsis is read as an explicit omission marker, never as quoted text: the evidence is only the exact text
  before it, which must be found exactly once in the part, within one source record (one line), ending on a word
  boundary; and the observation's statement may not rely on words that occur only in the omitted rest of the record.
  The quote is stored as the exact prefix with an ``omission`` record naming the marker and the omitted suffix.
- A reply that reaches the output-token limit or the context limit is rejected as truncated, even when it parses.
- Hierarchical synthesis: grounded observations -> bounded intermediate syntheses, one per document or group of whole
  parts -> the final experiment synthesis. Every intermediate statement cites the observations it rests on, and every
  grounded observation must be cited by an accepted intermediate statement, so no observation (minority, contradictory
  or otherwise) can be dropped silently; a unit that leaves one uncited fails. Every final entry cites intermediate
  statements and carries its lineage back to the observations. Identifiers and numbers in a statement (for example
  item or form ids, field names, years) must occur in the evidence it cites, at both levels; entries that fail are
  rejected and reported, never repaired. Statement allocations are sized from explicit, finite bounds so the final input
  fits the context by construction; nothing is discarded to make it fit.
- Coverage is a first-class result at every level: package parts, observations, intermediate units and statements, and
  the final synthesis. If any required part, unit or final stage fails, the review is ``incomplete``, every point where
  coverage was lost is listed with its reason, and later stages are not requested.
- A deterministic mutation guard fingerprints the protected state before and after the review: the source tree, the
  package, the operator-named registered files, and every file of each protected runtime root except this review's own
  directory (earlier reviews stay protected). Any change marks the review ``mutation_guard_failed``; the guard does not
  rely on prompt instructions.
"""

from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable, Iterable, Mapping, Sequence
import uuid

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from json_storage import write_text_atomic

CONTRACT_VERSION = "v2731.7"
REVIEW_AREA = "research_reviews"
MANIFEST_NAME = "package_manifest.json"
DOCUMENT_ROLES = ("design", "prompts", "corpus", "raw_outputs", "scorer", "evidence", "notes", "prior_evidence")
REQUIRED_ROLES = ("design", "corpus", "raw_outputs")
TASK_KINDS = ("independent_review",)
CHUNK_CHARS = 6500
MAX_OBSERVATIONS_PER_CHUNK = 8
MAX_QUOTES_PER_OBSERVATION = 3
MAX_QUOTE_CHARS = 240
MIN_QUOTE_CHARS = 4
MAX_OBSERVATION_CHARS = 300
MAX_QUESTIONS_PER_CHUNK = 5
# An explicit, finite bound for one observation reply, derived from the reply schema, not from any review's answers. A
# maximal conforming reply (8 observations, each a 300-character statement with 3 quotes of 240 characters, plus 5
# questions of 300 characters) is about 10,100 characters of JSON: under 3,400 tokens even at 3 characters per token.
# The largest observation prompt (a 6,500-character part plus the frame) is under 3,600 tokens at 2.4 characters per
# token, so prompt and reply together stay inside the 8,192-token context.
OBSERVE_MAX_TOKENS = 4096
# Intermediate level. A unit holds whole parts of one document whose observation lines total at most 6,000 characters
# (a part holds at most 8 observations, about 2,500 characters, so every part fits). The prompt stays under 3,600 tokens
# at 2.4 characters per token; a maximal reply (16 statements of 200 characters, each with a kind and 12 ids) is under
# 2,000 tokens at 3 characters per token.
INTERMEDIATE_INPUT_BUDGET_CHARS = 6000
INTERMEDIATE_MAX_TOKENS = 2048
MAX_INTERMEDIATE_STATEMENT_CHARS = 200
MAX_IDS_PER_STATEMENT = 12
MIN_STATEMENTS_PER_UNIT = 2
MAX_STATEMENTS_PER_UNIT = 16
INTERMEDIATE_KINDS = ("finding", "disagreement", "uncertainty", "minority", "contradiction", "unknown", "unresolved_relationship")
# Final level. Each intermediate line is at most 200 characters of statement plus 40 of id, document and kind, so the
# statement slots (9,000 // 241 = 37) keep the final input within 9,000 characters by construction. The second-half
# prompt (input, a 3,500-character summary of the first half and the template) stays under 5,800 tokens at 2.64
# characters per token (the densest ratio measured), leaving 2,048 for its reply; the first-half prompt has no summary
# and leaves 3,072.
FINAL_INPUT_BUDGET_CHARS = 9000
FINAL_LINE_OVERHEAD_CHARS = 40
FIRST_HALF_SUMMARY_CHARS = 3500
FINAL_A_MAX_TOKENS = 3072
FINAL_B_MAX_TOKENS = 2048
CONTEXT_MARGIN_TOKENS = 16
REVIEW_READ_TIMEOUT_SECONDS = 1800.0
ELLIPSES = ("...", "…")
STOPWORDS = frozenset("the and for with that this from are was were has have its into also which while where when each both their there "
                      "these those than then".split())
REPAIR_PREFACE = "Your previous reply was not valid JSON in the requested shape. Return only the JSON requested below.\n"
REVIEW_AUTHORITY = {**DENIED_AUTHORITY, "review_authoritative": False, "gold_change_authorized": False, "verdict_change_authorized": False,
                    "evidence_change_authorized": False, "belief_change_authorized": False, "memory_change_authorized": False,
                    "policy_change_authorized": False, "configuration_change_authorized": False, "experiment_authorized": False}
SECTIONS_A = ("experiment_understanding", "observations", "passed", "failed", "failure_clusters", "possible_harness_or_measurement_failures",
              "possible_model_or_reasoning_failures", "ambiguous_cases")
SECTIONS_B = ("competing_hypotheses", "unknowns", "confidence", "discriminating_experiments", "not_established")
CONFIDENCE_LEVELS = ("low", "medium", "high")

FRAME = (
    "You are Eidolon, reviewing a completed experiment. The model outputs recorded in this package were produced by the local "
    "model you run on (qwen3.8:27b), so this is evidence about your own behaviour. Your review is a research note only: it "
    "cannot change any label, verdict, evidence, belief, memory, policy, configuration or code, and nobody will act on it "
    "without an independent review. Report what the evidence shows, keep observation separate from interpretation, and say "
    "plainly when the evidence does not settle something. Do not propose code changes whose purpose is to make a benchmark pass.\n"
)
OBSERVE_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Below is one part of one document from the package: document {doc_id} ({role}: {description}), part {part} of {parts}.\n"
    "---\n{chunk}\n---\n"
    "List up to {max_obs} factual observations that this part itself shows. An observation states what the record contains, "
    "not what it means. For each, copy one or more short exact quotes from this part that show it (quotes: at most {max_quotes}, "
    "each at most {max_quote} characters). Copy each quote exactly as it appears; when an observation rests on more than one "
    "place in this part, give each place as its own quote instead of joining them. "
    "Also list questions this part raises but does not answer.\n"
    'Return only JSON: {{"observations": [{{"statement": "...", "quotes": ["..."]}}], "open_questions": ["..."]}}'
)
INTERMEDIATE_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Below are the grounded observations extracted from document {doc_id} ({role}: {description}), {parts_label}. Each has an id:\n"
    "{observations}\n"
    "Write a bounded synthesis of these observations for the later review of the whole experiment. Its purpose is to compress the "
    "evidence while keeping where it came from, not to reach conclusions. Keep each disagreement, uncertainty, minority observation, "
    "contradiction, explicit unknown and unresolved relationship as its own statement instead of merging it into a consensus. Use only "
    "what these observations state and add nothing from outside them. Each statement must cite the ids of the observations it rests on "
    "(obs_ids, at most {max_ids}), and every observation id listed above must be cited by at least one statement. Give at most "
    "{max_statements} statements, each at most {max_chars} characters, and label each with one kind: {kinds}.\n"
    'Return only JSON: {{"statements": [{{"statement": "...", "kind": "finding", "obs_ids": ["O1"]}}]}}'
)
FINAL_A_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "These are bounded syntheses of the grounded observations, made document by document. Each statement has an id, its document "
    "and its kind, and rests on observations cited in the record (no interpretation of the whole experiment yet):\n"
    "{statements}\n"
    "Write the first half of your review. Every entry must cite the ids of the statements it rests on (int_ids). Keep entries short. "
    "Record uncertainty instead of manufacturing a conclusion.\n"
    'Return only JSON: {{"experiment_understanding": {{"statement": "...", "int_ids": ["I1"]}}, "observations": [{{"statement": "...", "int_ids": ["I1"]}}], '
    '"passed": [{{"statement": "...", "int_ids": []}}], "failed": [{{"statement": "...", "int_ids": []}}], '
    '"failure_clusters": [{{"statement": "...", "int_ids": []}}], "possible_harness_or_measurement_failures": [{{"statement": "...", "int_ids": []}}], '
    '"possible_model_or_reasoning_failures": [{{"statement": "...", "int_ids": []}}], "ambiguous_cases": [{{"statement": "...", "int_ids": []}}]}}'
)
FINAL_B_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Statements synthesized from the package's grounded observations (id [document, kind]: statement):\n{statements}\n"
    "Your first-half review found:\n{first_half}\n"
    "Write the second half. Give competing hypotheses that could explain what was observed, each with the statement ids for and "
    "against it. List unknowns. Rate your confidence (low, medium or high) with a reason. Propose the smallest experiments that would "
    "discriminate between the hypotheses, naming which hypotheses each distinguishes (by number, starting at 1). List what the "
    "evidence does not establish. Every entry must cite the ids of the statements it rests on (int_ids).\n"
    'Return only JSON: {{"competing_hypotheses": [{{"hypothesis": "...", "evidence_for": ["I1"], "evidence_against": ["I2"]}}], '
    '"unknowns": [{{"statement": "...", "int_ids": ["I1"]}}], "confidence": {{"level": "low|medium|high", "reason": "...", "int_ids": ["I1"]}}, '
    '"discriminating_experiments": [{{"experiment": "...", "distinguishes": [1, 2], "int_ids": ["I1"]}}], '
    '"not_established": [{{"statement": "...", "int_ids": ["I1"]}}]}}'
)


class ReviewPackageError(ValueError):
    """The selected package cannot be reviewed: fail closed before any model call."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _norm(text: Any) -> str:
    return " ".join(str(text).split())


def _ids(value: Any) -> list[str]:
    return list(dict.fromkeys(str(x) for x in (value if isinstance(value, list) else []) if isinstance(x, (str, int)) and not isinstance(x, bool)))


def _identifiers(text: Any) -> set[str]:
    """Identifier-like tokens (letters with digits, underscores, 4+ digit or dotted numbers); review ids O1/I1 excluded."""
    found = set()
    for token in re.findall(r"[A-Za-z0-9_]+(?:[.:][A-Za-z0-9_]+)*", str(text)):
        t = token.lower()
        if re.fullmatch(r"[oi][0-9]+", t):
            continue
        alpha, digits = any(c.isalpha() for c in t), sum(c.isdigit() for c in t)
        if (alpha and digits) or "_" in t or (digits and not alpha and (digits >= 4 or "." in t)):
            found.add(t)
    return found


def _words(text: Any) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_]+", str(text).lower()) if len(w) >= 3 and w not in STOPWORDS}


def runtime_root(value: str | Path | None = None) -> Path:
    if value is not None:
        return Path(value).expanduser().resolve()
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()


# --- the package ---------------------------------------------------------------------------------------------------------
def load_package(package_dir: str | Path) -> dict[str, Any]:
    """Read and verify an explicitly selected package. Only listed documents are opened."""
    base = Path(package_dir).expanduser().resolve()
    manifest_path = base / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ReviewPackageError("package_manifest_missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("task") or "") not in TASK_KINDS:
        raise ReviewPackageError("package_task_not_supported")
    documents = []
    for entry in manifest.get("documents") or []:
        rel = str(entry.get("path") or "")
        target = (base / rel).resolve()
        if not rel or target == base or base not in target.parents or target.is_symlink():
            raise ReviewPackageError("package_document_outside_package")
        if str(entry.get("role") or "") not in DOCUMENT_ROLES:
            raise ReviewPackageError("package_document_role_invalid")
        optional = entry.get("optional", False)
        if not isinstance(optional, bool):
            raise ReviewPackageError("package_document_optional_flag_invalid")
        if optional and entry["role"] in REQUIRED_ROLES:
            raise ReviewPackageError("required_role_marked_optional")
        if not target.is_file() or _sha256_file(target) != str(entry.get("sha256") or ""):
            raise ReviewPackageError("package_document_digest_mismatch")
        documents.append({"doc_id": str(entry["doc_id"]), "role": entry["role"], "description": str(entry.get("description") or "")[:200],
                          "path": rel, "sha256": entry["sha256"], "required": not optional, "text": target.read_text(encoding="utf-8")})
    if not documents:
        raise ReviewPackageError("package_has_no_documents")
    if len({d["doc_id"] for d in documents}) != len(documents):
        raise ReviewPackageError("package_document_ids_not_unique")
    return {"dir": base, "manifest": manifest, "manifest_sha256": _sha256_file(manifest_path), "documents": documents,
            "experiment_id": str(manifest.get("experiment_id") or ""), "title": str(manifest.get("title") or ""),
            "brief": str(manifest.get("brief") or "")}


def chunks(text: str, size: int = CHUNK_CHARS) -> list[str]:
    """Deterministic, lossless split on line boundaries into pieces of at most ``size`` characters (a longer line is cut)."""
    out, current = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > size:
            if current:
                out.append(current)
                current = ""
            out.append(line[:size])
            line = line[size:]
        if len(current) + len(line) > size and current:
            out.append(current)
            current = ""
        current += line
    if current:
        out.append(current)
    assert "".join(out) == text
    return out or [""]


# --- the mutation guard -----------------------------------------------------------------------------------------------------
def _tree_digest(root: Path, exclude: Sequence[Path] = ()) -> dict[str, str]:
    files = {}
    if root.is_file():
        return {str(root): _sha256_file(root)}
    if not root.exists():
        return {}
    excluded = [e.resolve() for e in exclude]
    for path in sorted(root.rglob("*")):
        rp = path.resolve()
        if any(rp == e or e in rp.parents for e in excluded) or not path.is_file():
            continue
        try:
            files[str(path.relative_to(root))] = _sha256_file(path)
        except OSError as exc:  # a locked file is recorded, not skipped
            files[str(path.relative_to(root))] = f"unreadable:{type(exc).__name__}"
    return files


def _git_state(source_root: Path) -> dict[str, str]:
    def run(*args: str) -> bytes:
        return subprocess.run(["git", "-C", str(source_root), *args], capture_output=True, check=True).stdout
    return {"head": run("rev-parse", "HEAD").decode().strip(), "status_sha256": hashlib.sha256(run("status", "--porcelain=v1", "-z")).hexdigest(),
            "diff_sha256": hashlib.sha256(run("diff", "HEAD", "--binary")).hexdigest()}


def snapshot_protected(*, source_root: Path | None, package_dir: Path, protected_paths: Iterable[Path], protected_roots: Iterable[Path],
                       review_area: Path) -> dict[str, Any]:
    """Fingerprint everything the review must leave unchanged. ``review_area`` (this review's own directory) is the only exclusion."""
    snap: dict[str, Any] = {"package": _tree_digest(package_dir)}
    if source_root is not None:
        snap["source_tree"] = _git_state(source_root)
    snap["protected_paths"] = {str(p): _tree_digest(Path(p)) for p in protected_paths}
    snap["protected_roots"] = {str(r): _tree_digest(Path(r), exclude=[review_area]) for r in protected_roots}
    return snap


def compare_snapshots(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
    changes = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        if a == b:
            continue
        if isinstance(a, dict) and isinstance(b, dict):
            for sub in sorted(set(a) | set(b)):
                if a.get(sub) != b.get(sub):
                    inner_a, inner_b = a.get(sub), b.get(sub)
                    if isinstance(inner_a, dict) and isinstance(inner_b, dict):
                        changes += [f"{key}:{sub}:{f}" for f in sorted(set(inner_a) | set(inner_b)) if inner_a.get(f) != inner_b.get(f)][:20]
                    else:
                        changes.append(f"{key}:{sub}")
        else:
            changes.append(key)
    return changes


# --- model calls ------------------------------------------------------------------------------------------------------------
def production_call_model(*, temperature: float = 0.0) -> Callable[[str, int], tuple[str, dict[str, Any]]]:
    """One counted attempt per call through the configured local model, with no hidden transport retries."""
    from local_model import LocalModelClient, LocalModelConfig
    from settings_manager import load_settings

    def call(prompt: str, max_tokens: int) -> tuple[str, dict[str, Any]]:
        config = LocalModelConfig.from_settings(load_settings()).with_generation(temperature=temperature, max_tokens=max_tokens)
        config = replace(config, retry_limit=0, structured_json=True, read_timeout_seconds=max(config.read_timeout_seconds, REVIEW_READ_TIMEOUT_SECONDS))
        started = time.perf_counter()
        meta: dict[str, Any] = {}
        try:
            with LocalModelClient(config) as client:
                text = client.generate(prompt)
                meta["metrics"] = dict(client.last_metrics or {})
        except Exception as exc:  # a failed attempt is recorded and counted, never hidden
            text, meta["error"] = "", f"{type(exc).__name__}: {exc}"[:300]
        meta["seconds"] = round(time.perf_counter() - started, 3)
        return text, meta
    return call


def model_identity() -> dict[str, Any]:
    from local_model import LocalModelConfig
    from settings_manager import load_settings
    import dataclasses
    config = json.loads(json.dumps(dataclasses.asdict(LocalModelConfig.from_settings(load_settings())), default=str, sort_keys=True))
    return {"model": config.get("model"), "provider": config.get("provider"), "context_size": config.get("context_size"),
            "resolved_config_sha256": digest(config)}


def _parse(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        try:
            value = json.loads(text[start:end + 1]) if 0 <= start < end else None
        except Exception:
            value = None
    return value if isinstance(value, dict) else None


def _rejection(meta: Mapping[str, Any], parsed: Mapping[str, Any] | None, accept: Callable[[dict[str, Any]], bool], max_tokens: int,
               context_size: int | None) -> str | None:
    """Why an attempt is not accepted, or None. A reply at the output or context limit is truncated even if it parses."""
    if meta.get("error"):
        return "timeout" if "Timeout" in str(meta["error"]) else "provider_error"
    metrics = meta.get("metrics") or {}
    produced, prompt_tokens = metrics.get("eval_count"), metrics.get("prompt_eval_count")
    if isinstance(produced, int) and produced >= max_tokens:
        return "truncated_at_output_limit"
    if isinstance(produced, int) and isinstance(prompt_tokens, int) and context_size and \
            prompt_tokens + produced >= context_size - CONTEXT_MARGIN_TOKENS:
        return "context_limit_reached"
    if parsed is None:
        return "unparseable_json"
    if not accept(dict(parsed)):
        return "schema_rejected"
    return None


def _ask(call_model, prompt: str, max_tokens: int, accept: Callable[[dict[str, Any]], bool], ledger: list[dict[str, Any]], stage: str,
         *, context_size: int | None = None, check: Callable[[dict[str, Any]], str | None] | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """At most one repair retry over the identical input; every attempt is recorded with its rejection reason.

    ``check`` is a registered mechanical conformance test applied after the schema (for example, that an intermediate
    synthesis cites every observation); its failure is a rejection like any other, with the same single retry.
    """
    reason = None
    for attempt, text in enumerate((prompt, REPAIR_PREFACE + prompt), 1):
        raw, meta = call_model(text, max_tokens)
        parsed = _parse(raw or "")
        reason = _rejection(meta, parsed, accept, max_tokens, context_size)
        if reason is None and check is not None:
            reason = check(dict(parsed))
        ledger.append({"stage": stage, "attempt": attempt, "prompt_sha256": hashlib.sha256(text.encode()).hexdigest()[:16], "max_tokens": max_tokens,
                       "reply": raw, "accepted": reason is None, "rejection": reason, **meta})
        if reason is None:
            return parsed, None
    return None, reason


# --- observation grounding ----------------------------------------------------------------------------------------------------
def _pattern(text: str) -> str:
    return r"\s+".join(re.escape(t) for t in text.split())


def _locate(quote: str, text: str) -> re.Match | None:
    """Find a whitespace-normalized quote in the raw text, so its exact span is known."""
    return re.search(_pattern(quote), text) if quote.split() else None


def _without_trailing_marker(text: str) -> tuple[str, str] | None:
    for marker in ELLIPSES:
        if text.endswith(marker):
            return text[:-len(marker)].rstrip(), marker
    return None


def _ground_quote(value: Any, chunk_text: str, doc_text: str, doc_id: str, part: int, chunk_offset: int) -> dict[str, Any]:
    """Locate one quote. An exact match wins; otherwise a single trailing ellipsis may mark an omitted record suffix."""
    as_returned = _norm(value if isinstance(value, str) else "")
    text = as_returned[:MAX_QUOTE_CHARS]
    if len(text) < MIN_QUOTE_CHARS:
        return {"text": text, "found": False, "reason": "quote_too_short"}
    matches = list(re.finditer(_pattern(text), chunk_text))
    omission, suffix = None, ""
    if not matches:
        stripped = _without_trailing_marker(text)
        if stripped is None:
            return {"text": text, "found": False, "reason": "stitched_quote" if any(e in text for e in ELLIPSES) else "quote_not_found_in_document"}
        body, marker = stripped
        if any(e in body for e in ELLIPSES):
            return {"text": text, "found": False, "reason": "stitched_quote"}
        if len(body) < MIN_QUOTE_CHARS:
            return {"text": text, "found": False, "reason": "quote_too_short"}
        matches = list(re.finditer(_pattern(body), chunk_text))
        if not matches:
            return {"text": text, "found": False, "reason": "omission_prefix_not_found"}
        if len(matches) > 1:
            return {"text": text, "found": False, "reason": "omission_prefix_ambiguous"}
        start, end = chunk_offset + matches[0].start(), chunk_offset + matches[0].end()
        if "\n" in doc_text[start:end]:
            return {"text": text, "found": False, "reason": "omission_spans_records"}
        if body[-1].isalnum() and doc_text[end:end + 1].isalnum():
            return {"text": text, "found": False, "reason": "omission_splits_a_word"}
        stop = doc_text.find("\n", end)
        suffix = doc_text[end:len(doc_text) if stop < 0 else stop].rstrip("\r")
        text = body
        omission = {"marker": marker, "as_returned": as_returned, "omitted_suffix_chars": len(suffix), "omitted_suffix": suffix[:1000]}
    match = matches[0]
    start, end = chunk_offset + match.start(), chunk_offset + match.end()
    line_begin = doc_text.rfind("\n", 0, start) + 1
    line_stop = doc_text.find("\n", start)
    return {"text": text, "found": True, "doc_id": doc_id, "part": part, "char_start": start, "char_end": end,
            "line_start": doc_text.count("\n", 0, start) + 1, "line_end": doc_text.count("\n", 0, max(start, end - 1)) + 1,
            "record_head": doc_text[line_begin:len(doc_text) if line_stop < 0 else line_stop].rstrip("\r")[:120],
            "occurrences_in_part": len(matches), "omission": omission, "_suffix": suffix}


def ground_observations(parsed: Mapping[str, Any], chunk_text: str, doc_id: str, part: int, start_index: int, *,
                        doc_text: str | None = None, chunk_offset: int = 0, rejected_start: int = 1):
    """Each observation needs 1 to MAX_QUOTES_PER_OBSERVATION quotes, each located separately in this part.

    One quote that is not found rejects the whole observation. A quote using a trailing omission marker is grounded only
    by its exact prefix, and the observation is rejected if its statement relies on words found only in the omitted text.
    """
    doc_text = chunk_text if doc_text is None else doc_text
    grounded, rejected = [], []
    items = [x for x in parsed.get("observations") or [] if isinstance(x, dict)][:MAX_OBSERVATIONS_PER_CHUNK]
    for item in items:
        statement = _norm(item.get("statement") or "")[:MAX_OBSERVATION_CHARS]
        raw_quotes = item.get("quotes") if "quotes" in item else [item.get("quote")] if "quote" in item else None
        reason, extra = None, {}
        if not statement:
            reason = "empty_statement"
        elif not isinstance(raw_quotes, list) or not raw_quotes:
            reason = "no_quotes"
        elif len(raw_quotes) > MAX_QUOTES_PER_OBSERVATION:
            reason = "too_many_quotes"
        quotes = [_ground_quote(v, chunk_text, doc_text, doc_id, part, chunk_offset) for v in (raw_quotes if isinstance(raw_quotes, list) else [])]
        if reason is None:
            failed = next((q for q in quotes if not q["found"]), None)
            reason = failed["reason"] if failed else None
        if reason is None and any(q["omission"] for q in quotes):
            quoted = _words(" ".join(q["text"] for q in quotes))
            omitted = _words(" ".join(q["_suffix"] for q in quotes if q["omission"]))
            hidden = sorted((_words(statement) & omitted) - quoted)
            if hidden:
                reason, extra = "omission_hides_attributed_content", {"hidden_terms": hidden}
        for q in quotes:
            q.pop("_suffix", None)
        row = {"doc_id": doc_id, "part": part, "statement": statement, "quotes": quotes}
        if reason is None:
            grounded.append({"obs_id": f"O{start_index + len(grounded)}", **row})
        else:
            rejected.append({"rej_id": f"R{rejected_start + len(rejected)}", **row, "reason": reason, **extra})
    questions = [_norm(q)[:300] for q in (parsed.get("open_questions") or []) if isinstance(q, str) and q.strip()][:MAX_QUESTIONS_PER_CHUNK]
    return grounded, rejected, questions


# --- the intermediate level ---------------------------------------------------------------------------------------------------
def _intermediate_line(o: Mapping[str, Any]) -> str:
    return f"{o['obs_id']} (part {o['part']}): {o['statement']}"


def plan_units(package: Mapping[str, Any], grounded: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Group each document's grounded observations into units of whole parts within the intermediate input budget."""
    units: list[dict[str, Any]] = []
    for doc in package["documents"]:
        observations = [o for o in grounded if o["doc_id"] == doc["doc_id"]]
        groups, current, size = [], [], 0
        for part in sorted({o["part"] for o in observations}):
            part_obs = [o for o in observations if o["part"] == part]
            part_size = sum(len(_intermediate_line(o)) + 1 for o in part_obs)
            if current and size + part_size > INTERMEDIATE_INPUT_BUDGET_CHARS:
                groups.append(current)
                current, size = [], 0
            current += part_obs
            size += part_size
        if current:
            groups.append(current)
        for group in groups:
            unit_id = f"U{len(units) + 1}"
            units.append({"unit_id": unit_id, "stage": f"intermediate:{unit_id}", "doc_id": doc["doc_id"], "role": doc["role"],
                          "description": doc["description"], "required": doc["required"], "parts": sorted({o["part"] for o in group}),
                          "total_parts": len(chunks(doc["text"])), "obs_ids": [o["obs_id"] for o in group]})
    return units


def final_slots() -> int:
    return FINAL_INPUT_BUDGET_CHARS // (MAX_INTERMEDIATE_STATEMENT_CHARS + FINAL_LINE_OVERHEAD_CHARS + 1)


def statement_allocation(counts: Sequence[int], slots: int) -> list[int]:
    """Deterministic statement caps per unit, proportional to its observations (largest remainder), within the slots."""
    if not counts:
        return []
    total = sum(counts) or 1
    raw = [slots * c / total for c in counts]
    alloc = [min(MAX_STATEMENTS_PER_UNIT, max(MIN_STATEMENTS_PER_UNIT, int(r))) for r in raw]
    spare = slots - sum(alloc)
    for k in sorted(range(len(counts)), key=lambda i: (-(raw[i] - int(raw[i])), i)):
        if spare <= 0:
            break
        if alloc[k] < MAX_STATEMENTS_PER_UNIT:
            alloc[k] += 1
            spare -= 1
    while sum(alloc) > slots:  # minimums pushed the total over: take back from the largest, never below the minimum
        k = max(range(len(alloc)), key=lambda i: (alloc[i], -i))
        if alloc[k] <= MIN_STATEMENTS_PER_UNIT:
            break
        alloc[k] -= 1
    return alloc


def intermediate_prompt(package: Mapping[str, Any], unit: Mapping[str, Any], observations_by_id: Mapping[str, Mapping[str, Any]]) -> str:
    parts = unit["parts"]
    label = f"part {parts[0]} of {unit['total_parts']}" if len(parts) == 1 else f"parts {', '.join(map(str, parts))} of {unit['total_parts']}"
    return INTERMEDIATE_PROMPT.format(title=package["title"], brief=package["brief"], doc_id=unit["doc_id"], role=unit["role"],
                                      description=unit["description"], parts_label=label,
                                      observations="\n".join(_intermediate_line(observations_by_id[i]) for i in unit["obs_ids"]),
                                      max_ids=MAX_IDS_PER_STATEMENT, max_statements=unit["max_statements"],
                                      max_chars=MAX_INTERMEDIATE_STATEMENT_CHARS, kinds=", ".join(INTERMEDIATE_KINDS))


def _observation_support(obs_ids: Iterable[str], observations_by_id: Mapping[str, Mapping[str, Any]]) -> set[str]:
    texts = []
    for i in obs_ids:
        o = observations_by_id[i]
        texts.append(o["statement"])
        texts += [q["text"] for q in o["quotes"]]
    return _identifiers(" ".join(texts))


def validate_intermediate(parsed: Mapping[str, Any], unit: Mapping[str, Any],
                          observations_by_id: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep statements that cite this unit's observations and are supported by them; reject the rest, never repair them."""
    kept, dropped = [], []
    in_unit = set(unit["obs_ids"])
    for n, item in enumerate(x for x in parsed.get("statements") or [] if isinstance(x, dict)):
        text = _norm(item.get("statement") or "")
        kind = item.get("kind")
        cited = _ids(item.get("obs_ids"))
        good = [i for i in cited if i in in_unit]
        row = {"statement": text[:600], "kind": kind, "obs_ids": good, "dropped_obs_ids": [i for i in cited if i not in in_unit]}
        reason, extra = None, {}
        if n >= unit["max_statements"]:
            reason = "over_statement_limit"
        elif not text:
            reason = "empty_statement"
        elif len(text) > MAX_INTERMEDIATE_STATEMENT_CHARS:
            reason = "statement_too_long"
        elif kind not in INTERMEDIATE_KINDS:
            reason = "invalid_kind"
        elif not good:
            reason = "no_valid_obs_ids"
        elif len(good) > MAX_IDS_PER_STATEMENT:
            reason = "too_many_obs_ids"
        else:
            unsupported = sorted(_identifiers(text) - _observation_support(good, observations_by_id))
            if unsupported:
                reason, extra = "unsupported_identifiers", {"identifiers": unsupported}
        if reason is None:
            kept.append(row)
        else:
            dropped.append({**row, "reason": reason, **extra})
    return kept, dropped


def final_block(statements: Sequence[Mapping[str, Any]]) -> str:
    return "\n".join(f"{s['int_id']} [{s['doc_id']}, {s['kind']}]: {s['statement']}" for s in statements)


# --- the final level --------------------------------------------------------------------------------------------------------
def _lineage(int_ids: Iterable[str], int_by_id: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return list(dict.fromkeys(o for i in int_ids for o in int_by_id[i]["obs_ids"]))


def _final_support(int_ids: Iterable[str], int_by_id, observations_by_id) -> set[str]:
    ids = list(int_ids)
    return _identifiers(" ".join(int_by_id[i]["statement"] for i in ids)) | _observation_support(_lineage(ids, int_by_id), observations_by_id)


def _final_entry(where: str, text: Any, cited: list[str], int_by_id, observations_by_id):
    text = _norm(text or "")[:600]
    good, bad = [i for i in cited if i in int_by_id], [i for i in cited if i not in int_by_id]
    if not text:
        return None, None, bad
    if not good:
        return None, {"where": where, "statement": text, "reason": "untraceable_no_valid_int_ids", "cited": cited}, bad
    unsupported = sorted(_identifiers(text) - _final_support(good, int_by_id, observations_by_id))
    if unsupported:
        return None, {"where": where, "statement": text, "reason": "unsupported_identifiers", "identifiers": unsupported, "int_ids": good}, bad
    return {"statement": text, "int_ids": good, "obs_ids": _lineage(good, int_by_id), "unknown_int_ids": bad}, None, bad


def _entry_parts(item: Any, key: str = "statement") -> tuple[Any, list[str]]:
    return (item.get(key), _ids(item.get("int_ids"))) if isinstance(item, dict) else (item, [])


def validate_final_first(parsed: Mapping[str, Any], int_by_id, observations_by_id) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    rejected: list[dict[str, Any]] = []
    unknown: list[str] = []
    text, cited = _entry_parts(parsed.get("experiment_understanding"))
    entry, rej, bad = _final_entry("experiment_understanding", text, cited, int_by_id, observations_by_id)
    section: dict[str, Any] = {"experiment_understanding": entry}
    rejected += [rej] if rej else []
    unknown += bad
    for key in SECTIONS_A[1:]:
        rows = []
        for n, item in enumerate(parsed.get(key) if isinstance(parsed.get(key), list) else []):
            entry, rej, bad = _final_entry(f"{key}[{n}]", *_entry_parts(item), int_by_id, observations_by_id)
            rows += [entry] if entry else []
            rejected += [rej] if rej else []
            unknown += bad
        section[key] = rows
    return section, rejected, unknown


def validate_final_second(parsed: Mapping[str, Any], int_by_id, observations_by_id) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    rejected: list[dict[str, Any]] = []
    unknown: list[str] = []
    hypotheses, renumber = [], {}
    given = [x for x in parsed.get("competing_hypotheses") or [] if isinstance(x, dict)]
    for n, item in enumerate(given, 1):
        text = _norm(item.get("hypothesis") or "")[:600]
        if not text:
            continue
        cited_for, cited_against = _ids(item.get("evidence_for")), _ids(item.get("evidence_against"))
        good_for, good_against = [i for i in cited_for if i in int_by_id], [i for i in cited_against if i in int_by_id]
        unknown += [i for i in cited_for + cited_against if i not in int_by_id]
        if not good_for and not good_against:
            rejected.append({"where": f"competing_hypotheses[{n}]", "statement": text, "reason": "untraceable_no_valid_int_ids"})
            continue
        unsupported = sorted(_identifiers(text) - _final_support(good_for + good_against, int_by_id, observations_by_id))
        if unsupported:
            rejected.append({"where": f"competing_hypotheses[{n}]", "statement": text, "reason": "unsupported_identifiers", "identifiers": unsupported})
            continue
        hypotheses.append({"hypothesis": text, "evidence_for": good_for, "evidence_against": good_against,
                           "obs_ids": _lineage(good_for + good_against, int_by_id), "original_number": n})
        renumber[n] = len(hypotheses)
    listed = {}
    for key in ("unknowns", "not_established"):
        rows = []
        for n, item in enumerate(parsed.get(key) if isinstance(parsed.get(key), list) else []):
            entry, rej, bad = _final_entry(f"{key}[{n}]", *_entry_parts(item), int_by_id, observations_by_id)
            rows += [entry] if entry else []
            rejected += [rej] if rej else []
            unknown += bad
        listed[key] = rows
    conf = parsed.get("confidence") if isinstance(parsed.get("confidence"), dict) else {}
    entry, rej, bad = _final_entry("confidence", conf.get("reason"), _ids(conf.get("int_ids")), int_by_id, observations_by_id)
    unknown += bad
    if entry:
        confidence = {"level": conf.get("level") if conf.get("level") in CONFIDENCE_LEVELS else None, "reason": entry["statement"],
                      "int_ids": entry["int_ids"], "obs_ids": entry["obs_ids"]}
    else:
        confidence = {"level": None, "reason": "", "int_ids": [], "obs_ids": []}
        rejected += [rej] if rej else [{"where": "confidence", "statement": "", "reason": "untraceable_no_valid_int_ids"}]
    experiments = []
    for n, item in enumerate(x for x in parsed.get("discriminating_experiments") or [] if isinstance(x, dict)):
        text = _norm(item.get("experiment") or "")[:600]
        if not text:
            continue
        cited = _ids(item.get("int_ids"))
        good = [i for i in cited if i in int_by_id]
        unknown += [i for i in cited if i not in int_by_id]
        numbers = [int(x) for x in item.get("distinguishes") or [] if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
        mapped = [renumber[i] for i in numbers if i in renumber]
        via = [i for h in (hypotheses[m - 1] for m in mapped) for i in h["evidence_for"] + h["evidence_against"]]
        if not good and not mapped:
            rejected.append({"where": f"discriminating_experiments[{n}]", "statement": text, "reason": "untraceable_no_valid_int_ids"})
            continue
        unsupported = sorted(_identifiers(text) - _final_support(list(dict.fromkeys(good + via)), int_by_id, observations_by_id)
                             - {t for m in mapped for t in _identifiers(hypotheses[m - 1]["hypothesis"])})
        if unsupported:
            rejected.append({"where": f"discriminating_experiments[{n}]", "statement": text, "reason": "unsupported_identifiers", "identifiers": unsupported})
            continue
        experiments.append({"experiment": text, "distinguishes": mapped,
                            "distinguishes_dropped": [i for i in numbers if i not in renumber and 1 <= i <= len(given)],
                            "distinguishes_unknown": [i for i in numbers if not 1 <= i <= len(given)],
                            "int_ids": good, "obs_ids": _lineage(list(dict.fromkeys(good + via)), int_by_id)})
    return ({"competing_hypotheses": hypotheses, "unknowns": listed["unknowns"], "confidence": confidence,
             "discriminating_experiments": experiments, "not_established": listed["not_established"]}, rejected, unknown)


def _accept_final_first(parsed: Mapping[str, Any]) -> bool:
    return isinstance(parsed.get("experiment_understanding"), (dict, str)) and all(isinstance(parsed.get(k), list) for k in SECTIONS_A[1:])


def _accept_final_second(parsed: Mapping[str, Any]) -> bool:
    return isinstance(parsed.get("competing_hypotheses"), list) and isinstance(parsed.get("confidence"), dict) and \
        all(isinstance(parsed.get(k), list) for k in ("unknowns", "discriminating_experiments", "not_established"))


def first_half_summary(first_half: Mapping[str, Any]) -> str:
    return json.dumps({k: [e["statement"] for e in first_half.get(k, [])][:6] for k in SECTIONS_A[2:]}, ensure_ascii=False)[:FIRST_HALF_SUMMARY_CHARS]


def final_int_ids(review: Mapping[str, Any]) -> list[str]:
    """Every intermediate id a final entry cites."""
    ids: list[str] = []
    entries = [review.get("experiment_understanding")] + [e for k in SECTIONS_A[1:] for e in review.get(k, [])]
    entries += list(review.get("unknowns", [])) + list(review.get("not_established", [])) + list(review.get("discriminating_experiments", []))
    entries += [review.get("confidence")] if review.get("confidence") else []
    for e in entries:
        ids += (e or {}).get("int_ids", [])
    for h in review.get("competing_hypotheses", []):
        ids += h["evidence_for"] + h["evidence_against"]
    return list(dict.fromkeys(ids))


# --- the operation ----------------------------------------------------------------------------------------------------------
def review_experiment(package_dir: str | Path, *, call_model: Callable[[str, int], tuple[str, dict[str, Any]]] | None = None,
                      runtime_root_path: str | Path | None = None, source_root: str | Path | None = None,
                      protected_paths: Iterable[str | Path] = (), protected_roots: Iterable[str | Path] = (),
                      identity: Mapping[str, Any] | None = None, clock: Callable[[], str] = _now) -> dict[str, Any]:
    """Review one explicitly selected package and write the artifact into ``<runtime root>/research_reviews/<review_id>/``."""
    package = load_package(package_dir)
    root = runtime_root(runtime_root_path)
    area = root / REVIEW_AREA
    started = clock()
    review_id = hashlib.sha256(f"{package['manifest_sha256']}|{started}|{uuid.uuid4().hex}".encode()).hexdigest()[:16]
    out_dir = area / review_id
    if out_dir.exists():  # a review never overwrites another
        raise FileExistsError(f"review directory already exists: {out_dir}")
    guarded_roots = [root, *[Path(r).expanduser().resolve() for r in protected_roots]]
    guarded_paths = [Path(p).expanduser().resolve() for p in protected_paths]
    src = Path(source_root).expanduser().resolve() if source_root is not None else None
    before = snapshot_protected(source_root=src, package_dir=package["dir"], protected_paths=guarded_paths, protected_roots=guarded_roots,
                                review_area=out_dir)
    call_model = call_model or production_call_model()
    ident = dict(identity) if identity is not None else model_identity()
    context_size = ident.get("context_size") if isinstance(ident.get("context_size"), int) else None
    ledger: list[dict[str, Any]] = []
    grounded: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    parts_coverage: list[dict[str, Any]] = []

    # level 0: package parts -> grounded observations
    absent_roles = [r for r in REQUIRED_ROLES if r not in {d["role"] for d in package["documents"]}]
    if not absent_roles:  # a package missing a required role is incomplete before any model call
        for doc in package["documents"]:
            parts, offset = chunks(doc["text"]), 0
            for part, chunk_text in enumerate(parts, 1):
                stage = f"observe:{doc['doc_id']}:{part}"
                prompt = OBSERVE_PROMPT.format(title=package["title"], brief=package["brief"], doc_id=doc["doc_id"], role=doc["role"],
                                               description=doc["description"], part=part, parts=len(parts), chunk=chunk_text,
                                               max_obs=MAX_OBSERVATIONS_PER_CHUNK, max_quotes=MAX_QUOTES_PER_OBSERVATION, max_quote=MAX_QUOTE_CHARS)
                parsed, reason = _ask(call_model, prompt, OBSERVE_MAX_TOKENS, lambda p: isinstance(p.get("observations"), list), ledger, stage,
                                      context_size=context_size)
                g: list[dict[str, Any]] = []
                r: list[dict[str, Any]] = []
                if parsed is not None:
                    g, r, q = ground_observations(parsed, chunk_text, doc["doc_id"], part, len(grounded) + 1, doc_text=doc["text"],
                                                  chunk_offset=offset, rejected_start=len(rejected) + 1)
                    grounded += g
                    rejected += r
                    questions += [{"doc_id": doc["doc_id"], "part": part, "question": x} for x in q]
                    reason = None if g else "no_grounded_observations"
                parts_coverage.append({"stage": stage, "doc_id": doc["doc_id"], "role": doc["role"], "part": part, "parts": len(parts),
                                       "required": doc["required"], "reviewed": reason is None, "reason": reason,
                                       "attempts": sum(x["stage"] == stage for x in ledger), "grounded_observations": len(g),
                                       "rejected_observations": len(r)})
                offset += len(chunk_text)
    required = [p for p in parts_coverage if p["required"]]
    optional = [p for p in parts_coverage if not p["required"]]
    missing: list[dict[str, Any]] = [{"kind": "required_role_absent", "role": role, "reason": "the package lists no document with this required role"}
                                     for role in absent_roles]
    missing += [{"kind": "required_part_not_reviewed", "stage": p["stage"], "doc_id": p["doc_id"], "part": p["part"], "reason": p["reason"]}
                for p in required if not p["reviewed"]]
    obs_by_id = {o["obs_id"]: o for o in grounded}
    rejected_ids = {o["rej_id"] for o in rejected}

    # level 1: grounded observations -> bounded intermediate syntheses
    units: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    rejected_statements: list[dict[str, Any]] = []
    slots = final_slots()
    if not missing:
        units = plan_units(package, grounded)
        if len(units) * MIN_STATEMENTS_PER_UNIT > slots:
            missing.append({"kind": "final_capacity_insufficient", "units": len(units), "slots": slots,
                            "reason": "the final input budget cannot hold the minimum statements for every unit"})
        else:
            for unit, cap in zip(units, statement_allocation([len(u["obs_ids"]) for u in units], slots)):
                unit["max_statements"] = cap
            for unit in units:
                holder: dict[str, Any] = {}

                def check(parsed: dict[str, Any], unit: Mapping[str, Any] = unit, holder: dict[str, Any] = holder) -> str | None:
                    kept, dropped = validate_intermediate(parsed, unit, obs_by_id)
                    cited = {i for s in kept for i in s["obs_ids"]}
                    holder.clear()
                    holder.update(kept=kept, dropped=dropped, uncited=[i for i in unit["obs_ids"] if i not in cited])
                    return "no_valid_statements" if not kept else "uncited_observations" if holder["uncited"] else None
                parsed, reason = _ask(call_model, intermediate_prompt(package, unit, obs_by_id), INTERMEDIATE_MAX_TOKENS,
                                      lambda p: isinstance(p.get("statements"), list), ledger, unit["stage"], context_size=context_size, check=check)
                unit["attempts"] = sum(x["stage"] == unit["stage"] for x in ledger)
                if parsed is not None:
                    unit.update(status="accepted", uncited_obs_ids=[])
                    for s in holder["kept"]:
                        statements.append({"int_id": f"I{len(statements) + 1}", "unit_id": unit["unit_id"], "doc_id": unit["doc_id"], **s})
                    rejected_statements += [{"unit_id": unit["unit_id"], **s} for s in holder["dropped"]]
                else:
                    unit.update(status=f"failed:{reason}", uncited_obs_ids=holder.get("uncited", []),
                                rejected_statements_last_attempt=holder.get("dropped", []))
                    if unit["required"]:
                        missing.append({"kind": "intermediate_unit_failed", "unit_id": unit["unit_id"], "stage": unit["stage"], "doc_id": unit["doc_id"],
                                        "parts": unit["parts"], "reason": reason, "uncited_obs_ids": unit["uncited_obs_ids"], "lost_obs_ids": unit["obs_ids"]})
    int_by_id = {s["int_id"]: s for s in statements}
    intermediate_refs = [i for s in statements + rejected_statements for i in s.get("dropped_obs_ids", [])]

    # level 2: intermediate syntheses -> final experiment synthesis
    block = final_block(statements)
    first = second = None
    first_half: dict[str, Any] = {}
    second_half: dict[str, Any] = {}
    final_rejected: list[dict[str, Any]] = []
    final_unknown: list[str] = []
    final_state = {"first_half": "skipped:earlier_coverage_incomplete", "second_half": "skipped:earlier_coverage_incomplete"}
    if not missing and len(block) > FINAL_INPUT_BUDGET_CHARS:
        missing.append({"kind": "final_input_exceeds_budget", "chars": len(block), "budget": FINAL_INPUT_BUDGET_CHARS,
                        "reason": "the intermediate statements exceed the final input budget"})
    if not missing:
        first, reason_a = _ask(call_model, FINAL_A_PROMPT.format(title=package["title"], brief=package["brief"], statements=block),
                               FINAL_A_MAX_TOKENS, _accept_final_first, ledger, "final:first_half", context_size=context_size)
        if first is None:
            final_state = {"first_half": f"failed:{reason_a}", "second_half": "skipped:first_half_failed"}
            missing.append({"kind": "final_synthesis_failed", "stage": "final:first_half", "reason": reason_a})
        else:
            first_half, rej, unk = validate_final_first(first, int_by_id, obs_by_id)
            final_rejected += rej
            final_unknown += unk
            second, reason_b = _ask(call_model, FINAL_B_PROMPT.format(title=package["title"], brief=package["brief"], statements=block,
                                                                      first_half=first_half_summary(first_half)),
                                    FINAL_B_MAX_TOKENS, _accept_final_second, ledger, "final:second_half", context_size=context_size)
            final_state = {"first_half": "accepted", "second_half": "accepted" if second else f"failed:{reason_b}"}
            if second is None:
                missing.append({"kind": "final_synthesis_failed", "stage": "final:second_half", "reason": reason_b})
            else:
                second_half, rej, unk = validate_final_second(second, int_by_id, obs_by_id)
                final_rejected += rej
                final_unknown += unk
    review = {**first_half, **second_half}

    after = snapshot_protected(source_root=src, package_dir=package["dir"], protected_paths=guarded_paths, protected_roots=guarded_roots,
                               review_area=out_dir)
    changes = compare_snapshots(before, after)
    complete = not missing and first is not None and second is not None
    status = "mutation_guard_failed" if changes else "complete" if complete else "incomplete"
    reviewed_required = sum(p["reviewed"] for p in required)
    cited_by_intermediate = {i for s in statements for i in s["obs_ids"]}
    required_units = [u for u in units if u["required"]]
    cited_finally = final_int_ids(review)
    reached = set(_lineage(cited_finally, int_by_id))
    ratio = lambda a, b: round(a / b, 4) if b else 0.0  # noqa: E731
    coverage = {
        "complete": complete, "required_parts": len(required), "reviewed_required_parts": reviewed_required,
        "required_coverage": ratio(reviewed_required, len(required)), "optional_parts": len(optional),
        "reviewed_optional_parts": sum(p["reviewed"] for p in optional), "required_roles": list(REQUIRED_ROLES), "absent_required_roles": absent_roles,
        "grounded_observations": len(grounded),
        "levels": {
            "package_parts": {"required": len(required), "reviewed": reviewed_required, "coverage": ratio(reviewed_required, len(required))},
            "observations": {"grounded": len(grounded), "cited_by_accepted_intermediate": len(cited_by_intermediate),
                             "coverage": ratio(len(cited_by_intermediate), len(grounded))},
            "intermediate": {"units": len(units), "required_units": len(required_units),
                             "accepted_required_units": sum(u.get("status") == "accepted" for u in required_units),
                             "coverage": ratio(sum(u.get("status") == "accepted" for u in required_units), len(required_units)),
                             "statements": len(statements), "rejected_statements": len(rejected_statements),
                             "delivered_to_final": len(statements) if first is not None else 0,
                             "final_input_chars": len(block), "final_input_budget": FINAL_INPUT_BUDGET_CHARS, "final_statement_slots": slots},
            "final": {**final_state, "rejected_entries": len(final_rejected), "intermediate_statements_cited": len(cited_finally),
                      "intermediate_citation_coverage": ratio(len(cited_finally), len(statements)),
                      "units_cited": len({int_by_id[i]["unit_id"] for i in cited_finally}), "observations_reached": len(reached),
                      "observation_reach": ratio(len(reached), len(grounded))},
        },
        "missing": missing, "parts": parts_coverage,
    }
    rejections = Counter(x["rejection"] for x in ledger if x["rejection"])
    stage_order = list(dict.fromkeys(x["stage"] for x in ledger))
    accepted_stages = {x["stage"] for x in ledger if x["accepted"]}
    all_refs = intermediate_refs + final_unknown
    artifact = {
        "object": "experiment_review", "contract_version": CONTRACT_VERSION, "review_id": review_id, "status": status,
        "non_authoritative": True, "authority": dict(REVIEW_AUTHORITY), "coverage": coverage,
        "review": review if (first or second) else {},
        "intermediate": {"units": units, "statements": statements, "rejected_statements": rejected_statements},
        "final_rejected_entries": final_rejected,
        "grounded_observations": grounded, "rejected_observations": rejected, "open_questions": questions,
        "unknown_references": sorted(set(final_unknown) - rejected_ids),
        "intermediate_dropped_references": sorted(set(intermediate_refs) - rejected_ids),
        "rejected_observation_references": sorted(set(all_refs) & rejected_ids),
        "integrity_metrics": {"multi_quote_observations": sum(len(o["quotes"]) > 1 for o in grounded),
                              "omission_quotes": sum(bool(q.get("omission")) for o in grounded for q in o["quotes"]),
                              "observations_with_identifiers_not_in_their_quotes":
                                  sum(bool(_identifiers(o["statement"]) - _identifiers(" ".join(q["text"] for q in o["quotes"]))) for o in grounded)},
        "provenance": {"experiment_id": package["experiment_id"], "title": package["title"], "package_dir": str(package["dir"]),
                       "manifest_sha256": package["manifest_sha256"],
                       "documents": [{k: d[k] for k in ("doc_id", "role", "path", "sha256", "required")} for d in package["documents"]],
                       "model": ident, "started": started, "finished": clock(), "task": package["manifest"].get("task"),
                       "capability": {"contract_version": CONTRACT_VERSION, "module_sha256": _sha256_file(Path(__file__).resolve()),
                                      "source_tree": before.get("source_tree")},
                       "limits": {"observe_max_tokens": OBSERVE_MAX_TOKENS, "intermediate_max_tokens": INTERMEDIATE_MAX_TOKENS,
                                  "final_a_max_tokens": FINAL_A_MAX_TOKENS, "final_b_max_tokens": FINAL_B_MAX_TOKENS, "chunk_chars": CHUNK_CHARS,
                                  "max_observations_per_chunk": MAX_OBSERVATIONS_PER_CHUNK, "max_quotes_per_observation": MAX_QUOTES_PER_OBSERVATION,
                                  "max_quote_chars": MAX_QUOTE_CHARS, "intermediate_input_budget_chars": INTERMEDIATE_INPUT_BUDGET_CHARS,
                                  "max_intermediate_statement_chars": MAX_INTERMEDIATE_STATEMENT_CHARS, "max_ids_per_statement": MAX_IDS_PER_STATEMENT,
                                  "final_input_budget_chars": FINAL_INPUT_BUDGET_CHARS, "first_half_summary_chars": FIRST_HALF_SUMMARY_CHARS,
                                  "context_size": context_size},
                       "prompt_templates_sha256": {"observe": digest(OBSERVE_PROMPT), "intermediate": digest(INTERMEDIATE_PROMPT),
                                                   "final_a": digest(FINAL_A_PROMPT), "final_b": digest(FINAL_B_PROMPT)},
                       "mutation_authority": "none"},
        "runtime_accounting": {"provider_attempts": len(ledger), "failed_attempts": sum(bool(x.get("error")) for x in ledger),
                               "timeout_attempts": sum("Timeout" in str(x.get("error", "")) for x in ledger),
                               "unparseable_or_rejected_replies": sum(not x["accepted"] and not x.get("error") for x in ledger),
                               "truncated_attempts": rejections["truncated_at_output_limit"] + rejections["context_limit_reached"],
                               "retries": sum(x["attempt"] > 1 for x in ledger),
                               "recovered_stages": sorted(s for s in accepted_stages if any(x["stage"] == s and not x["accepted"] for x in ledger)),
                               "rejections_by_reason": dict(sorted(rejections.items())),
                               "stages_without_accepted_reply": sorted(set(stage_order) - accepted_stages),
                               "terminal_stage_failures": [{"stage": s, "reason": [x for x in ledger if x["stage"] == s][-1]["rejection"]}
                                                           for s in stage_order if s not in accepted_stages],
                               "accepted_replies_without_token_metrics": sum(x["accepted"] and not isinstance((x.get("metrics") or {}).get("eval_count"), int)
                                                                             for x in ledger)},
        "mutation_guard": {"passed": not changes, "changes": changes[:50],
                           "protected": {"source_tree": src is not None, "package": True, "paths": [str(p) for p in guarded_paths],
                                         "roots": [str(r) for r in guarded_roots], "excluded": str(out_dir)}},
        "ledger": ledger,
    }
    write_text_atomic(out_dir / "review.json", json.dumps(artifact, indent=1, ensure_ascii=False))
    write_text_atomic(out_dir / "review.md", render_markdown(artifact))
    return artifact


def _missing_text(item: Mapping[str, Any]) -> str:
    kind = item["kind"]
    if kind == "required_role_absent":
        return f"required role absent: {item['role']}"
    if kind == "required_part_not_reviewed":
        return f"{item['stage']} not reviewed: {item['reason']}"
    if kind == "intermediate_unit_failed":
        uncited = f"; uncited observations {', '.join(item['uncited_obs_ids'])}" if item["uncited_obs_ids"] else ""
        return f"{item['stage']} ({item['doc_id']}, parts {', '.join(map(str, item['parts']))}) failed: {item['reason']}{uncited}"
    if kind == "final_input_exceeds_budget":
        return f"final input {item['chars']} characters exceeds the budget of {item['budget']}"
    if kind == "final_capacity_insufficient":
        return f"final capacity insufficient: {item['units']} units for {item['slots']} statement slots"
    if kind == "final_synthesis_failed":
        return f"{item['stage']} failed: {item['reason']}"
    return json.dumps(item, ensure_ascii=False)


def _cites(entry: Mapping[str, Any] | None) -> str:
    return f" ({', '.join(entry['int_ids'])})" if entry and entry.get("int_ids") else ""


def render_markdown(artifact: Mapping[str, Any]) -> str:
    r, p, c = artifact.get("review") or {}, artifact["provenance"], artifact["coverage"]
    lv = c["levels"]
    lines = [f"# Eidolon research review: {p['title']}", "",
             f"Non-authoritative research artifact. Status: {artifact['status']}. Review {artifact['review_id']}, "
             f"model {p['model'].get('model')}, {p['started']} to {p['finished']}. Mutation guard passed: {artifact['mutation_guard']['passed']}.", "",
             f"Required coverage: {c['reviewed_required_parts']} of {c['required_parts']} package parts reviewed ({c['required_coverage']:.0%}); "
             f"{lv['observations']['cited_by_accepted_intermediate']} of {lv['observations']['grounded']} grounded observations cited by intermediate "
             f"syntheses ({lv['observations']['coverage']:.0%}); {lv['intermediate']['accepted_required_units']} of {lv['intermediate']['required_units']} "
             f"required intermediate units accepted; final synthesis: first half {lv['final']['first_half']}, second half {lv['final']['second_half']}; "
             f"final citations reach {lv['final']['observations_reached']} of {lv['observations']['grounded']} observations.", ""]
    if artifact["status"] != "complete":
        lines += ["**INCOMPLETE: this review must not be interpreted as a finished analysis.**", ""]
    if c["missing"]:
        lines += ["## Missing coverage", ""] + [f"- {_missing_text(m)}" for m in c["missing"]] + [""]
    if r.get("experiment_understanding"):
        lines += ["## Experiment understanding", "", r["experiment_understanding"]["statement"] + _cites(r["experiment_understanding"]), ""]
    titles = {"observations": "Observations", "passed": "Behaviours that passed", "failed": "Behaviours that failed",
              "failure_clusters": "Failure clusters", "possible_harness_or_measurement_failures": "Possible harness or measurement failures",
              "possible_model_or_reasoning_failures": "Possible model or reasoning failures", "ambiguous_cases": "Ambiguous cases"}
    for key, title in titles.items():
        if r.get(key):
            lines += [f"## {title}", ""] + [f"- {e['statement']}{_cites(e)}" for e in r[key]] + [""]
    if r.get("competing_hypotheses"):
        lines += ["## Competing hypotheses", ""]
        for n, h in enumerate(r["competing_hypotheses"], 1):
            lines.append(f"{n}. {h['hypothesis']} For: {', '.join(h['evidence_for']) or 'none'}. Against: {', '.join(h['evidence_against']) or 'none'}.")
        lines.append("")
    for key, title in (("unknowns", "Unknowns"), ("not_established", "Not established by the evidence")):
        if r.get(key):
            lines += [f"## {title}", ""] + [f"- {e['statement']}{_cites(e)}" for e in r[key]] + [""]
    if r.get("confidence") and r["confidence"].get("level"):
        lines += ["## Confidence", "", f"{r['confidence']['level']}: {r['confidence']['reason']}{_cites(r['confidence'])}", ""]
    if r.get("discriminating_experiments"):
        lines += ["## Smallest discriminating experiments", ""] + \
                 [f"- {e['experiment']} (distinguishes hypotheses {', '.join(map(str, e['distinguishes'])) or 'none named'}){_cites(e)}"
                  for e in r["discriminating_experiments"]] + [""]
    inter = artifact.get("intermediate") or {}
    if inter.get("statements"):
        lines += ["## Lineage: intermediate syntheses", ""]
        for u in inter["units"]:
            lines.append(f"### {u['unit_id']}: {u['doc_id']}, parts {', '.join(map(str, u['parts']))} ({u.get('status')})")
            lines += [f"- {s['int_id']} [{s['kind']}]: {s['statement']} ({', '.join(s['obs_ids'])})" for s in inter["statements"] if s["unit_id"] == u["unit_id"]]
            lines.append("")
    lines += ["## Grounded observations", ""]
    for o in artifact["grounded_observations"]:
        marks = "".join(" [omitted suffix]" for q in o["quotes"] if q.get("omission"))
        lines.append(f"- {o['obs_id']} [{o['doc_id']}, lines {', '.join(str(q['line_start']) for q in o['quotes'])}]: {o['statement']}{marks}")
    return "\n".join(lines) + "\n"


__all__ = ["CONTRACT_VERSION", "REVIEW_AREA", "REVIEW_AUTHORITY", "REQUIRED_ROLES", "ReviewPackageError", "load_package", "chunks",
           "snapshot_protected", "compare_snapshots", "ground_observations", "plan_units", "statement_allocation", "final_slots",
           "intermediate_prompt", "validate_intermediate", "final_block", "validate_final_first", "validate_final_second",
           "first_half_summary", "final_int_ids", "review_experiment", "render_markdown", "production_call_model", "model_identity", "runtime_root"]
