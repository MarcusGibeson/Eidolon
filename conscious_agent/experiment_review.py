from __future__ import annotations

"""Supervised, read-only experiment self-review (spec 2.18; coverage 2.19; omission 2.20; provenance and three-level synthesis 2.21).

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
- Observations: each bounded document part yields observations, each carrying one or more exact quotes located
  separately in that part. One unfound quote rejects the observation; stitched quotes are never accepted; a single
  trailing ellipsis is an omission marker whose evidence is only the exact prefix (unique in the part, within one
  record, on a word boundary), and the statement may not rely on words found only in the omitted text.
- Provenance: the system reads the record (line) each quote sits in and attaches its metadata (experiment, form, run,
  item, and similar keys) and the document id to the observation. An observation may name an identifier only if its
  quotes or that deterministic provenance establish it; the model need not quote metadata the system supplies.
  Identifier comparison is exact, except that a number with a recognized unit suffix (7.3s) matches the identical
  number (7.3), and never a different value, unit family or unrelated suffix.
- Three-level synthesis: grounded observations -> per-part synthesis -> per-document synthesis over small groups of
  whole parts -> final experiment synthesis. Each statement cites its immediate inputs, and its lineage back to the
  observations and their exact quotes is computed by code. Deterministic code, not the model, owns coverage: after each
  stage it records which inputs were cited, and every uncited input is carried forward explicitly to the next level.
  No model is asked again merely to cite more inputs. At the end, every observation is either in the lineage of a final
  entry or listed as evidence the final synthesis did not cite; nothing disappears silently.
- Every limit is explicit and finite. A reply that reaches the output-token or context limit is rejected as truncated.
  A failed required stage, or a final input over its budget, makes the review ``incomplete`` with the point of loss
  named, and later stages are not requested.
- A deterministic mutation guard fingerprints the protected state before and after the review: the source tree, the
  package, the operator-named registered files, and every file of each protected runtime root except this review's own
  directory (earlier reviews stay protected). Any change marks the review ``mutation_guard_failed``.
"""

from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable, Iterable, Mapping, Sequence
import uuid

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from json_storage import write_text_atomic

CONTRACT_VERSION = "v2731.8"
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
# Observation replies: a maximal conforming reply is about 10,100 characters (under 3,400 tokens at 3 characters per
# token); the largest observation prompt is under 3,600 tokens at 2.4, so both fit the 8,192-token context.
OBSERVE_MAX_TOKENS = 4096
# Synthesis statements, at the part and document levels.
MAX_STATEMENT_CHARS = 200
MAX_IDS_PER_STATEMENT = 12
SYNTHESIS_KINDS = ("finding", "disagreement", "uncertainty", "minority", "contradiction", "unknown", "unresolved_relationship")
# Part level: one unit per part (at most 8 observations); a unit may give ceil(n / 2) statements, a 2:1 compression, the
# size at which Review 3's summaries cited completely. A maximal reply is under 500 tokens.
PART_MAX_TOKENS = 1024
# Document level: whole parts of one document grouped while the unit holds at most 12 inputs and 6,000 characters (one
# part never exceeds this: at most 4 statements and 8 carried observations). Caps are ceil(n / 2), scaled down if their
# total would exceed the final statement slots. A maximal reply is under 2,000 tokens at 3 characters per token.
DOCUMENT_UNIT_MAX_INPUTS = 12
DOCUMENT_UNIT_INPUT_BUDGET_CHARS = 6000
DOCUMENT_MAX_TOKENS = 2048
# Final level. Budgets come from the context: synthesis prompts measured 3.62 to 4.53 characters per token on this
# model (Review 3); with a 15% margin on the minimum, 3.08. The second-half prompt (input, a 3,500-character summary of
# the first half and a template under 3,000 characters) then stays under 6,128 tokens, leaving 2,048 for its reply.
# Document statements are allocated within 9,000 characters; carried inputs use the rest, and a final input over
# 12,000 characters fails closed without discarding anything.
CALIBRATED_CHARS_PER_TOKEN = 3.08
FINAL_INPUT_BUDGET_CHARS = 12000
FINAL_DOCUMENT_STATEMENT_BUDGET_CHARS = 9000
FINAL_LINE_OVERHEAD_CHARS = 40
FIRST_HALF_SUMMARY_CHARS = 3500
FINAL_A_MAX_TOKENS = 3072
FINAL_B_MAX_TOKENS = 2048
CONTEXT_MARGIN_TOKENS = 16
REVIEW_READ_TIMEOUT_SECONDS = 1800.0
ELLIPSES = ("...", "…")
STOPWORDS = frozenset("the and for with that this from are was were has have its into also which while where when each both their there "
                      "these those than then".split())
METADATA_KEYS = ("experiment", "prompt_form_equivalent", "form", "variant", "condition", "run", "item", "case", "record")
UNIT_FAMILIES = {"s": "s", "sec": "s", "secs": "s", "second": "s", "seconds": "s", "ms": "ms", "millisecond": "ms", "milliseconds": "ms",
                 "min": "min", "mins": "min", "minute": "min", "minutes": "min", "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
                 "kb": "kb", "mb": "mb", "gb": "gb", "tb": "tb", "kib": "kib", "mib": "mib", "gib": "gib"}
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
_PRESERVE = ("Its purpose is to compress the evidence while keeping where it came from, not to reach conclusions. Keep each "
             "disagreement, uncertainty, minority observation, contradiction, explicit unknown and unresolved relationship as its own "
             "statement instead of merging it into a consensus. Use only what these inputs state and add nothing from outside them. ")
PART_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Below are the grounded observations extracted from document {doc_id} ({role}: {description}), part {part} of {parts}. Each has an "
    "id and, in brackets, record details the system attached:\n"
    "{inputs}\n"
    "Write a part-level synthesis of these observations for the later review of the whole experiment. " + _PRESERVE +
    "Each statement must cite the ids of the observations it rests on (obs_ids, at most {max_ids}). Observations you leave out are "
    "carried forward unchanged, so cite only what a statement actually rests on. Give at most {max_statements} statements, each at "
    "most {max_chars} characters, and label each with one kind: {kinds}.\n"
    'Return only JSON: {{"statements": [{{"statement": "...", "kind": "finding", "obs_ids": ["O1"]}}]}}'
)
DOCUMENT_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Below are the inputs from document {doc_id} ({role}: {description}), {parts_label}: part-level statements (PS ids) and "
    "observations that no part-level statement captured (O ids). Each has an id and, in brackets, its details:\n"
    "{inputs}\n"
    "Write a document-level synthesis of these inputs for the later review of the whole experiment. " + _PRESERVE +
    "Each statement must cite the ids of the inputs it rests on (input_ids, at most {max_ids}). Inputs you leave out are carried "
    "forward unchanged, so cite only what a statement actually rests on. Give at most {max_statements} statements, each at most "
    "{max_chars} characters, and label each with one kind: {kinds}.\n"
    'Return only JSON: {{"statements": [{{"statement": "...", "kind": "finding", "input_ids": ["PS1"]}}]}}'
)
FINAL_A_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "These are syntheses of the package's grounded observations: document-level statements (DS ids) and, marked as uncaptured, "
    "part-level statements (PS ids) and observations (O ids) that no higher-level statement captured. Each has an id and, in "
    "brackets, its document and kind (no interpretation of the whole experiment yet):\n"
    "{inputs}\n"
    "Write the first half of your review. Every entry must cite the ids of the inputs it rests on (input_ids). Keep entries short. "
    "Record uncertainty instead of manufacturing a conclusion.\n"
    'Return only JSON: {{"experiment_understanding": {{"statement": "...", "input_ids": ["DS1"]}}, "observations": [{{"statement": "...", "input_ids": ["DS1"]}}], '
    '"passed": [{{"statement": "...", "input_ids": []}}], "failed": [{{"statement": "...", "input_ids": []}}], '
    '"failure_clusters": [{{"statement": "...", "input_ids": []}}], "possible_harness_or_measurement_failures": [{{"statement": "...", "input_ids": []}}], '
    '"possible_model_or_reasoning_failures": [{{"statement": "...", "input_ids": []}}], "ambiguous_cases": [{{"statement": "...", "input_ids": []}}]}}'
)
FINAL_B_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Syntheses of the package's grounded observations (id [document, kind]: statement; uncaptured inputs are marked):\n{inputs}\n"
    "Your first-half review found:\n{first_half}\n"
    "Write the second half. Give competing hypotheses that could explain what was observed, each with the input ids for and "
    "against it. List unknowns. Rate your confidence (low, medium or high) with a reason. Propose the smallest experiments that would "
    "discriminate between the hypotheses, naming which hypotheses each distinguishes (by number, starting at 1). List what the "
    "evidence does not establish. Every entry must cite the ids of the inputs it rests on (input_ids).\n"
    'Return only JSON: {{"competing_hypotheses": [{{"hypothesis": "...", "evidence_for": ["DS1"], "evidence_against": ["DS2"]}}], '
    '"unknowns": [{{"statement": "...", "input_ids": ["DS1"]}}], "confidence": {{"level": "low|medium|high", "reason": "...", "input_ids": ["DS1"]}}, '
    '"discriminating_experiments": [{{"experiment": "...", "distinguishes": [1, 2], "input_ids": ["DS1"]}}], '
    '"not_established": [{{"statement": "...", "input_ids": ["DS1"]}}]}}'
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


# --- identifiers -------------------------------------------------------------------------------------------------------------
_NUMBER_IN_TEXT = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?!\.?\d)(\s*)([A-Za-z]*)")


def _identifiers(text: Any) -> set[str]:
    """Identifier-like tokens (letters with digits, underscores, 4+ digit or dotted numbers); review ids O1/PS1/DS1 excluded."""
    found = set()
    for token in re.findall(r"[A-Za-z0-9_]+(?:[.:][A-Za-z0-9_]+)*", str(text)):
        t = token.lower()
        if re.fullmatch(r"(?:o|ps|ds)[0-9]+", t):
            continue
        alpha, digits = any(c.isalpha() for c in t), sum(c.isdigit() for c in t)
        if (alpha and digits) or "_" in t or (digits and not alpha and (digits >= 4 or "." in t)):
            found.add(t)
    return found


def _number_supported(value: str, unit_family: str | None, text: str) -> bool:
    """True when ``text`` holds the identical number, bare, spaced, or with a unit of the same family (never an unrelated suffix)."""
    target = Decimal(value)
    for m in _NUMBER_IN_TEXT.finditer(text):
        if Decimal(m.group(1)) != target:
            continue
        letters, spaced = m.group(3).lower(), bool(m.group(2))
        family = UNIT_FAMILIES.get(letters) if letters else None
        if letters and not spaced and family is None:
            continue  # 7.3q, 7.3st: a different token, not a unit
        if unit_family is None or not letters or (spaced and family is None) or family == unit_family:
            return True
    return False


def _identifier_supported(token: str, support_ids: set[str], support_text: str) -> bool:
    if token in support_ids:
        return True
    unit = re.fullmatch(r"(\d+(?:\.\d+)?)([a-z]+)", token)
    if unit and unit.group(2) in UNIT_FAMILIES:
        return _number_supported(unit.group(1), UNIT_FAMILIES[unit.group(2)], support_text)
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return _number_supported(token, None, support_text)
    return False


def unsupported_identifiers(text: str, evidence: str) -> list[str]:
    """The identifiers in ``text`` that ``evidence`` does not establish (exact, or the narrow unit rule)."""
    support = _identifiers(evidence)
    return sorted(t for t in _identifiers(text) if not _identifier_supported(t, support, evidence))


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
         *, context_size: int | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """At most one repair retry over the identical input, only for provider, truncation, parse or schema failures."""
    reason = None
    for attempt, text in enumerate((prompt, REPAIR_PREFACE + prompt), 1):
        raw, meta = call_model(text, max_tokens)
        parsed = _parse(raw or "")
        reason = _rejection(meta, parsed, accept, max_tokens, context_size)
        ledger.append({"stage": stage, "attempt": attempt, "prompt_sha256": hashlib.sha256(text.encode()).hexdigest()[:16], "max_tokens": max_tokens,
                       "reply": raw, "accepted": reason is None, "rejection": reason, **meta})
        if reason is None:
            return parsed, None
    return None, reason


# --- observation grounding and provenance --------------------------------------------------------------------------------------
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


_METADATA = re.compile(r'(?<![A-Za-z0-9_])"?(' + "|".join(METADATA_KEYS) + r')"?\s*[=:]\s*"?([A-Za-z0-9][A-Za-z0-9_.:\-]*)')


def record_metadata(doc_text: str, line_start: int, line_end: int) -> dict[str, list[str]]:
    """Metadata the system reads from the source records (lines) a quote sits in: key=value and "key": "value" pairs."""
    found: dict[str, list[str]] = {}
    for line in doc_text.split("\n")[line_start - 1:line_end]:
        for key, value in _METADATA.findall(line):
            value = value.rstrip(".:-")
            if value and value not in found.setdefault(key, []):
                found[key].append(value)
    return found


def _merge_metadata(records: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for r in records:
        for key, values in r["metadata"].items():
            for v in values:
                if v not in merged.setdefault(key, []):
                    merged[key].append(v)
    return merged


def _metadata_label(metadata: Mapping[str, Sequence[str]]) -> str:
    return " ".join(f"{k}={'/'.join(v)}" for k, v in metadata.items())


def observation_evidence(o: Mapping[str, Any]) -> str:
    """Everything that establishes an observation: its exact quotes and the provenance the system attached."""
    meta = o["provenance"]["metadata"]
    return " ".join([q["text"] for q in o["quotes"]] + [f"{k} {v}" for k, vs in meta.items() for v in vs] + [o["provenance"]["doc_id"]])


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
    """Ground each observation in 1 to MAX_QUOTES_PER_OBSERVATION separately located quotes, then attach record provenance.

    Rejected when a quote is not found, when a suffix omission hides words the statement relies on, or when the statement
    names an identifier that neither its quotes nor the attached record metadata establish.
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
        provenance = None
        if reason is None:
            records = [{"line_start": q["line_start"], "line_end": q["line_end"], "metadata": record_metadata(doc_text, q["line_start"], q["line_end"])}
                       for q in quotes]
            provenance = {"doc_id": doc_id, "part": part, "records": records, "metadata": _merge_metadata(records)}
            meta_words = _words(" ".join(v for vs in provenance["metadata"].values() for v in vs))
            if any(q["omission"] for q in quotes):
                quoted = _words(" ".join(q["text"] for q in quotes))
                omitted = _words(" ".join(q["_suffix"] for q in quotes if q["omission"]))
                hidden = sorted((_words(statement) & omitted) - quoted - meta_words)
                if hidden:
                    reason, extra = "omission_hides_attributed_content", {"hidden_terms": hidden}
            if reason is None:
                unsupported = unsupported_identifiers(statement, observation_evidence({"quotes": quotes, "provenance": provenance}))
                if unsupported:
                    reason, extra = "unsupported_identifiers", {"identifiers": unsupported}
        for q in quotes:
            q.pop("_suffix", None)
        row = {"doc_id": doc_id, "part": part, "statement": statement, "quotes": quotes, "provenance": provenance}
        if reason is None:
            grounded.append({"obs_id": f"O{start_index + len(grounded)}", **row})
        else:
            rejected.append({"rej_id": f"R{rejected_start + len(rejected)}", **row, "reason": reason, **extra})
    questions = [_norm(q)[:300] for q in (parsed.get("open_questions") or []) if isinstance(q, str) and q.strip()][:MAX_QUESTIONS_PER_CHUNK]
    return grounded, rejected, questions


# --- the synthesis hierarchy: shared bookkeeping --------------------------------------------------------------------------------
def lineage_of(ids: Iterable[str], items: Mapping[str, Mapping[str, Any]]) -> list[str]:
    return list(dict.fromkeys(o for i in ids for o in items[i]["lineage"]))


def support_evidence(ids: Iterable[str], items: Mapping[str, Mapping[str, Any]], evidence: Mapping[str, str]) -> str:
    """The ground truth behind a set of inputs: the quotes and provenance of every observation in their lineage."""
    return " ".join(evidence[o] for o in lineage_of(ids, items))


def input_line(item: Mapping[str, Any], level: str) -> str:
    """How an input is shown to the next level; carried inputs are marked as uncaptured."""
    if item["type"] == "observation":
        where = f"part {item['part']}" if level != "final" else f"{item['doc_id']} part {item['part']}"
        label = "" if level == "part" else ", uncaptured observation"
        meta = f"; {item['meta']}" if item["meta"] else ""
        details = f"{where}{label}{meta}" if level != "part" else item["meta"]
        return f"{item['id']}{f' [{details}]' if details else ''}: {item['statement']}"
    if item["type"] == "part_statement":
        if level == "document":
            return f"{item['id']} [part {item['part']}, {item['kind']}]: {item['statement']}"
        return f"{item['id']} [{item['doc_id']} part {item['part']}, uncaptured part statement, {item['kind']}]: {item['statement']}"
    return f"{item['id']} [{item['doc_id']}, {item['kind']}]: {item['statement']}"


def validate_statements(parsed: Mapping[str, Any], unit: Mapping[str, Any], items: Mapping[str, Mapping[str, Any]],
                        evidence: Mapping[str, str], *, ids_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep statements that cite this unit's inputs and are supported by their lineage; reject the rest, never repair them."""
    kept, dropped = [], []
    allowed = set(unit["inputs"])
    for n, item in enumerate(x for x in parsed.get("statements") or [] if isinstance(x, dict)):
        text = _norm(item.get("statement") or "")
        kind = item.get("kind")
        cited = _ids(item.get(ids_key))
        good = [i for i in cited if i in allowed]
        row = {"statement": text[:600], "kind": kind, "cites": good, "dropped_cites": [i for i in cited if i not in allowed]}
        reason, extra = None, {}
        if n >= unit["max_statements"]:
            reason = "over_statement_limit"
        elif not text:
            reason = "empty_statement"
        elif len(text) > MAX_STATEMENT_CHARS:
            reason = "statement_too_long"
        elif kind not in SYNTHESIS_KINDS:
            reason = "invalid_kind"
        elif not good:
            reason = "no_valid_citations"
        elif len(good) > MAX_IDS_PER_STATEMENT:
            reason = "too_many_citations"
        else:
            unsupported = unsupported_identifiers(text, support_evidence(good, items, evidence))
            if unsupported:
                reason, extra = "unsupported_identifiers", {"identifiers": unsupported}
        if reason is None:
            kept.append(row)
        else:
            dropped.append({**row, "reason": reason, **extra})
    return kept, dropped


def allocate(wants: Sequence[int], slots: int) -> list[int]:
    """Statement caps: each unit's want (ceil(inputs / 2)) if they fit the slots, else scaled by largest remainder, at least 1."""
    if sum(wants) <= slots:
        return list(wants)
    raw = [slots * w / sum(wants) for w in wants]
    alloc = [min(w, max(1, int(r))) for w, r in zip(wants, raw)]
    for k in sorted(range(len(wants)), key=lambda i: (-(raw[i] - int(raw[i])), i)):
        if sum(alloc) >= slots:
            break
        if alloc[k] < wants[k]:
            alloc[k] += 1
    while sum(alloc) > slots:
        k = max(range(len(alloc)), key=lambda i: (alloc[i], -i))
        if alloc[k] <= 1:
            break
        alloc[k] -= 1
    return alloc


def document_statement_slots() -> int:
    return FINAL_DOCUMENT_STATEMENT_BUDGET_CHARS // (MAX_STATEMENT_CHARS + FINAL_LINE_OVERHEAD_CHARS + 1)


def plan_part_units(package: Mapping[str, Any], grounded: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    units = []
    for doc in package["documents"]:
        total = len(chunks(doc["text"]))
        for part in sorted({o["part"] for o in grounded if o["doc_id"] == doc["doc_id"]}):
            ids = [o["obs_id"] for o in grounded if o["doc_id"] == doc["doc_id"] and o["part"] == part]
            unit_id = f"PU{len(units) + 1}"
            units.append({"unit_id": unit_id, "stage": f"part:{unit_id}", "doc_id": doc["doc_id"], "role": doc["role"], "description": doc["description"],
                          "required": doc["required"], "part": part, "total_parts": total, "inputs": ids, "max_statements": max(1, math.ceil(len(ids) / 2))})
    return units


def part_prompt(package: Mapping[str, Any], unit: Mapping[str, Any], items: Mapping[str, Mapping[str, Any]]) -> str:
    return PART_PROMPT.format(title=package["title"], brief=package["brief"], doc_id=unit["doc_id"], role=unit["role"], description=unit["description"],
                              part=unit["part"], parts=unit["total_parts"], inputs="\n".join(input_line(items[i], "part") for i in unit["inputs"]),
                              max_ids=MAX_IDS_PER_STATEMENT, max_statements=unit["max_statements"], max_chars=MAX_STATEMENT_CHARS,
                              kinds=", ".join(SYNTHESIS_KINDS))


def plan_document_units(package: Mapping[str, Any], part_units: Sequence[Mapping[str, Any]], items: Mapping[str, Mapping[str, Any]],
                        part_inputs: Mapping[tuple[str, int], Sequence[str]]) -> list[dict[str, Any]]:
    """Group each document's parts, in order and whole, while a unit holds at most 12 inputs and 6,000 characters."""
    units: list[dict[str, Any]] = []
    for doc in package["documents"]:
        parts = [u["part"] for u in part_units if u["doc_id"] == doc["doc_id"]]
        groups, current, count, size = [], [], 0, 0
        for part in parts:
            ids = list(part_inputs.get((doc["doc_id"], part), []))
            chars = sum(len(input_line(items[i], "document")) + 1 for i in ids)
            if current and (count + len(ids) > DOCUMENT_UNIT_MAX_INPUTS or size + chars > DOCUMENT_UNIT_INPUT_BUDGET_CHARS):
                groups.append(current)
                current, count, size = [], 0, 0
            current.append((part, ids))
            count += len(ids)
            size += chars
        if current:
            groups.append(current)
        for group in groups:
            ids = [i for _, g in group for i in g]
            if not ids:
                continue
            unit_id = f"DU{len(units) + 1}"
            units.append({"unit_id": unit_id, "stage": f"document:{unit_id}", "doc_id": doc["doc_id"], "role": doc["role"],
                          "description": doc["description"], "required": doc["required"], "parts": [p for p, _ in group],
                          "total_parts": len(chunks(doc["text"])), "inputs": ids})
    return units


def document_prompt(package: Mapping[str, Any], unit: Mapping[str, Any], items: Mapping[str, Mapping[str, Any]]) -> str:
    parts = unit["parts"]
    label = f"part {parts[0]} of {unit['total_parts']}" if len(parts) == 1 else f"parts {', '.join(map(str, parts))} of {unit['total_parts']}"
    return DOCUMENT_PROMPT.format(title=package["title"], brief=package["brief"], doc_id=unit["doc_id"], role=unit["role"],
                                  description=unit["description"], parts_label=label,
                                  inputs="\n".join(input_line(items[i], "document") for i in unit["inputs"]), max_ids=MAX_IDS_PER_STATEMENT,
                                  max_statements=unit["max_statements"], max_chars=MAX_STATEMENT_CHARS, kinds=", ".join(SYNTHESIS_KINDS))


def final_block(final_inputs: Sequence[str], items: Mapping[str, Mapping[str, Any]]) -> str:
    return "\n".join(input_line(items[i], "final") for i in final_inputs)


# --- the final level --------------------------------------------------------------------------------------------------------
def _final_entry(where: str, text: Any, cited: list[str], known: set[str], items, evidence):
    text = _norm(text or "")[:600]
    good, bad = [i for i in cited if i in known], [i for i in cited if i not in known]
    if not text:
        return None, None, bad
    if not good:
        return None, {"where": where, "statement": text, "reason": "untraceable_no_valid_input_ids", "cited": cited}, bad
    unsupported = unsupported_identifiers(text, support_evidence(good, items, evidence))
    if unsupported:
        return None, {"where": where, "statement": text, "reason": "unsupported_identifiers", "identifiers": unsupported, "input_ids": good}, bad
    return {"statement": text, "input_ids": good, "obs_ids": lineage_of(good, items), "unknown_input_ids": bad}, None, bad


def _entry_parts(item: Any, key: str = "statement") -> tuple[Any, list[str]]:
    return (item.get(key), _ids(item.get("input_ids"))) if isinstance(item, dict) else (item, [])


def validate_final_first(parsed: Mapping[str, Any], known: set[str], items, evidence) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    rejected: list[dict[str, Any]] = []
    unknown: list[str] = []
    entry, rej, bad = _final_entry("experiment_understanding", *_entry_parts(parsed.get("experiment_understanding")), known, items, evidence)
    section: dict[str, Any] = {"experiment_understanding": entry}
    rejected += [rej] if rej else []
    unknown += bad
    for key in SECTIONS_A[1:]:
        rows = []
        for n, item in enumerate(parsed.get(key) if isinstance(parsed.get(key), list) else []):
            entry, rej, bad = _final_entry(f"{key}[{n}]", *_entry_parts(item), known, items, evidence)
            rows += [entry] if entry else []
            rejected += [rej] if rej else []
            unknown += bad
        section[key] = rows
    return section, rejected, unknown


def validate_final_second(parsed: Mapping[str, Any], known: set[str], items, evidence) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    rejected: list[dict[str, Any]] = []
    unknown: list[str] = []
    hypotheses, renumber = [], {}
    given = [x for x in parsed.get("competing_hypotheses") or [] if isinstance(x, dict)]
    for n, item in enumerate(given, 1):
        text = _norm(item.get("hypothesis") or "")[:600]
        if not text:
            continue
        cited_for, cited_against = _ids(item.get("evidence_for")), _ids(item.get("evidence_against"))
        good_for, good_against = [i for i in cited_for if i in known], [i for i in cited_against if i in known]
        unknown += [i for i in cited_for + cited_against if i not in known]
        if not good_for and not good_against:
            rejected.append({"where": f"competing_hypotheses[{n}]", "statement": text, "reason": "untraceable_no_valid_input_ids"})
            continue
        unsupported = unsupported_identifiers(text, support_evidence(good_for + good_against, items, evidence))
        if unsupported:
            rejected.append({"where": f"competing_hypotheses[{n}]", "statement": text, "reason": "unsupported_identifiers", "identifiers": unsupported})
            continue
        hypotheses.append({"hypothesis": text, "evidence_for": good_for, "evidence_against": good_against,
                           "obs_ids": lineage_of(good_for + good_against, items), "original_number": n})
        renumber[n] = len(hypotheses)
    listed = {}
    for key in ("unknowns", "not_established"):
        rows = []
        for n, item in enumerate(parsed.get(key) if isinstance(parsed.get(key), list) else []):
            entry, rej, bad = _final_entry(f"{key}[{n}]", *_entry_parts(item), known, items, evidence)
            rows += [entry] if entry else []
            rejected += [rej] if rej else []
            unknown += bad
        listed[key] = rows
    conf = parsed.get("confidence") if isinstance(parsed.get("confidence"), dict) else {}
    entry, rej, bad = _final_entry("confidence", conf.get("reason"), _ids(conf.get("input_ids")), known, items, evidence)
    unknown += bad
    if entry:
        confidence = {"level": conf.get("level") if conf.get("level") in CONFIDENCE_LEVELS else None, "reason": entry["statement"],
                      "input_ids": entry["input_ids"], "obs_ids": entry["obs_ids"]}
    else:
        confidence = {"level": None, "reason": "", "input_ids": [], "obs_ids": []}
        rejected += [rej] if rej else [{"where": "confidence", "statement": "", "reason": "untraceable_no_valid_input_ids"}]
    experiments = []
    for n, item in enumerate(x for x in parsed.get("discriminating_experiments") or [] if isinstance(x, dict)):
        text = _norm(item.get("experiment") or "")[:600]
        if not text:
            continue
        cited = _ids(item.get("input_ids"))
        good = [i for i in cited if i in known]
        unknown += [i for i in cited if i not in known]
        numbers = [int(x) for x in item.get("distinguishes") or [] if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
        mapped = [renumber[i] for i in numbers if i in renumber]
        via = [i for h in (hypotheses[m - 1] for m in mapped) for i in h["evidence_for"] + h["evidence_against"]]
        if not good and not mapped:
            rejected.append({"where": f"discriminating_experiments[{n}]", "statement": text, "reason": "untraceable_no_valid_input_ids"})
            continue
        all_ids = list(dict.fromkeys(good + via))
        unsupported = unsupported_identifiers(text, support_evidence(all_ids, items, evidence) + " " +
                                              " ".join(hypotheses[m - 1]["hypothesis"] for m in mapped))
        if unsupported:
            rejected.append({"where": f"discriminating_experiments[{n}]", "statement": text, "reason": "unsupported_identifiers", "identifiers": unsupported})
            continue
        experiments.append({"experiment": text, "distinguishes": mapped,
                            "distinguishes_dropped": [i for i in numbers if i not in renumber and 1 <= i <= len(given)],
                            "distinguishes_unknown": [i for i in numbers if not 1 <= i <= len(given)],
                            "input_ids": good, "obs_ids": lineage_of(all_ids, items)})
    return ({"competing_hypotheses": hypotheses, "unknowns": listed["unknowns"], "confidence": confidence,
             "discriminating_experiments": experiments, "not_established": listed["not_established"]}, rejected, unknown)


def _accept_statements(parsed: Mapping[str, Any]) -> bool:
    return isinstance(parsed.get("statements"), list)


def _accept_final_first(parsed: Mapping[str, Any]) -> bool:
    return isinstance(parsed.get("experiment_understanding"), (dict, str)) and all(isinstance(parsed.get(k), list) for k in SECTIONS_A[1:])


def _accept_final_second(parsed: Mapping[str, Any]) -> bool:
    return isinstance(parsed.get("competing_hypotheses"), list) and isinstance(parsed.get("confidence"), dict) and \
        all(isinstance(parsed.get(k), list) for k in ("unknowns", "discriminating_experiments", "not_established"))


def first_half_summary(first_half: Mapping[str, Any]) -> str:
    return json.dumps({k: [e["statement"] for e in first_half.get(k, [])][:6] for k in SECTIONS_A[2:]}, ensure_ascii=False)[:FIRST_HALF_SUMMARY_CHARS]


def final_input_ids(review: Mapping[str, Any]) -> list[str]:
    """Every final input a final entry cites."""
    ids: list[str] = []
    entries = [review.get("experiment_understanding")] + [e for k in SECTIONS_A[1:] for e in review.get(k, [])]
    entries += list(review.get("unknowns", [])) + list(review.get("not_established", [])) + list(review.get("discriminating_experiments", []))
    entries += [review.get("confidence")] if review.get("confidence") else []
    for e in entries:
        ids += (e or {}).get("input_ids", [])
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

    # level 0: package parts -> grounded observations with provenance
    absent_roles = [r for r in REQUIRED_ROLES if r not in {d["role"] for d in package["documents"]}]
    if not absent_roles:
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
    rejected_ids = {o["rej_id"] for o in rejected}
    items: dict[str, dict[str, Any]] = {o["obs_id"]: {"id": o["obs_id"], "type": "observation", "doc_id": o["doc_id"], "part": o["part"],
                                                      "statement": o["statement"], "lineage": [o["obs_id"]],
                                                      "meta": _metadata_label(o["provenance"]["metadata"])} for o in grounded}
    evidence = {o["obs_id"]: observation_evidence(o) for o in grounded}
    part_units: list[dict[str, Any]] = []
    doc_units: list[dict[str, Any]] = []
    part_statements: list[str] = []
    doc_statements: list[str] = []
    rejected_statements: list[dict[str, Any]] = []
    carried_to_document: list[str] = []
    carried_to_final: list[str] = []
    final_inputs: list[str] = []
    dropped_refs: list[str] = []

    def run_unit(unit: dict[str, Any], prompt: str, max_tokens: int, ids_key: str, prefix: str, kind: str, extra: Callable[[dict], dict]):
        parsed, reason = _ask(call_model, prompt, max_tokens, _accept_statements, ledger, unit["stage"], context_size=context_size)
        unit["attempts"] = sum(x["stage"] == unit["stage"] for x in ledger)
        if parsed is None:
            unit.update(status=f"failed:{reason}", cited=[], uncited=list(unit["inputs"]), statements=[])
            return reason
        kept, dropped = validate_statements(parsed, unit, items, evidence, ids_key=ids_key)
        cited = {i for s in kept for i in s["cites"]}
        unit.update(status="accepted", cited=[i for i in unit["inputs"] if i in cited], uncited=[i for i in unit["inputs"] if i not in cited],
                    statements=[], rejected_statements=len(dropped))
        for s in kept:
            sid = f"{prefix}{sum(1 for x in items.values() if x['type'] == kind) + 1}"
            items[sid] = {"id": sid, "type": kind, "unit_id": unit["unit_id"], "doc_id": unit["doc_id"], "kind": s["kind"],
                          "statement": s["statement"], "cites": s["cites"], "dropped_cites": s["dropped_cites"],
                          "lineage": lineage_of(s["cites"], items), **extra(s)}
            unit["statements"].append(sid)
        rejected_statements.extend({"level": unit["stage"].split(":")[0], "unit_id": unit["unit_id"], **d} for d in dropped)
        dropped_refs.extend(i for s in kept + dropped for i in s["dropped_cites"])
        return None

    # level 1: grounded observations -> per-part synthesis
    if not missing:
        part_units = plan_part_units(package, grounded)
        for unit in part_units:
            reason = run_unit(unit, part_prompt(package, unit, items), PART_MAX_TOKENS, "obs_ids", "PS", "part_statement",
                              lambda s, unit=unit: {"part": unit["part"]})
            if reason and unit["required"]:
                missing.append({"kind": "synthesis_stage_failed", "level": "part", "unit_id": unit["unit_id"], "stage": unit["stage"],
                                "doc_id": unit["doc_id"], "parts": [unit["part"]], "reason": reason, "inputs_lost_at_stage": unit["inputs"]})
        part_statements = [i for u in part_units for i in u.get("statements", [])]
        carried_to_document = [i for u in part_units if u.get("status") == "accepted" or not u["required"] for i in u["uncited"]]

    # level 2: part statements and uncaptured observations -> per-document synthesis
    slots = document_statement_slots()
    if not missing:
        part_inputs = {(u["doc_id"], u["part"]): u["statements"] + u["uncited"] for u in part_units}
        doc_units = plan_document_units(package, part_units, items, part_inputs)
        if len(doc_units) > slots:
            missing.append({"kind": "final_capacity_insufficient", "units": len(doc_units), "slots": slots,
                            "reason": "the document-statement budget cannot give every document unit one statement"})
        else:
            for unit, cap in zip(doc_units, allocate([max(1, math.ceil(len(u["inputs"]) / 2)) for u in doc_units], slots)):
                unit["max_statements"] = cap
            for unit in doc_units:
                reason = run_unit(unit, document_prompt(package, unit, items), DOCUMENT_MAX_TOKENS, "input_ids", "DS", "document_statement",
                                  lambda s, unit=unit: {"parts": unit["parts"]})
                if reason and unit["required"]:
                    missing.append({"kind": "synthesis_stage_failed", "level": "document", "unit_id": unit["unit_id"], "stage": unit["stage"],
                                    "doc_id": unit["doc_id"], "parts": unit["parts"], "reason": reason, "inputs_lost_at_stage": unit["inputs"]})
            doc_statements = [i for u in doc_units for i in u.get("statements", [])]
            carried_to_final = [i for u in doc_units if u.get("status") == "accepted" or not u["required"] for i in u["uncited"]]

    # level 3: document statements and uncaptured inputs -> final experiment synthesis
    first = second = None
    first_half: dict[str, Any] = {}
    second_half: dict[str, Any] = {}
    final_rejected: list[dict[str, Any]] = []
    final_unknown: list[str] = []
    final_state = {"first_half": "skipped:earlier_coverage_incomplete", "second_half": "skipped:earlier_coverage_incomplete"}
    block = ""
    if not missing:
        order = {u["unit_id"]: n for n, u in enumerate(doc_units)}
        final_inputs = doc_statements + sorted(carried_to_final, key=lambda i: (next(order[u["unit_id"]] for u in doc_units if i in u["inputs"]), i))
        block = final_block(final_inputs, items)
        if len(block) > FINAL_INPUT_BUDGET_CHARS:
            missing.append({"kind": "final_input_exceeds_budget", "chars": len(block), "budget": FINAL_INPUT_BUDGET_CHARS,
                            "carried_inputs": len(carried_to_final), "reason": "document statements and carried inputs exceed the final input budget"})
    if not missing:
        known = set(final_inputs)
        first, reason_a = _ask(call_model, FINAL_A_PROMPT.format(title=package["title"], brief=package["brief"], inputs=block),
                               FINAL_A_MAX_TOKENS, _accept_final_first, ledger, "final:first_half", context_size=context_size)
        if first is None:
            final_state = {"first_half": f"failed:{reason_a}", "second_half": "skipped:first_half_failed"}
            missing.append({"kind": "final_synthesis_failed", "stage": "final:first_half", "reason": reason_a})
        else:
            first_half, rej, unk = validate_final_first(first, known, items, evidence)
            final_rejected += rej
            final_unknown += unk
            second, reason_b = _ask(call_model, FINAL_B_PROMPT.format(title=package["title"], brief=package["brief"], inputs=block,
                                                                      first_half=first_half_summary(first_half)),
                                    FINAL_B_MAX_TOKENS, _accept_final_second, ledger, "final:second_half", context_size=context_size)
            final_state = {"first_half": "accepted", "second_half": "accepted" if second else f"failed:{reason_b}"}
            if second is None:
                missing.append({"kind": "final_synthesis_failed", "stage": "final:second_half", "reason": reason_b})
            else:
                second_half, rej, unk = validate_final_second(second, known, items, evidence)
                final_rejected += rej
                final_unknown += unk
    review = {**first_half, **second_half}

    # deterministic accounting: nothing may disappear
    represented = set(lineage_of(final_inputs, items))
    cited_finally = final_input_ids(review)
    reached = lineage_of(cited_finally, items)
    silently_dropped = [o["obs_id"] for o in grounded if o["obs_id"] not in represented] if final_inputs else []
    after = snapshot_protected(source_root=src, package_dir=package["dir"], protected_paths=guarded_paths, protected_roots=guarded_roots,
                               review_area=out_dir)
    changes = compare_snapshots(before, after)
    complete = not missing and first is not None and second is not None and not silently_dropped
    status = "mutation_guard_failed" if changes else "complete" if complete else "incomplete"
    ratio = lambda a, b: round(a / b, 4) if b else 0.0  # noqa: E731
    reviewed_required = sum(p["reviewed"] for p in required)
    captured_by_part = {o for i in part_statements for o in items[i]["cites"]}
    doc_cited = {i for u in doc_units for i in u.get("cited", [])}
    coverage = {
        "complete": complete, "required_parts": len(required), "reviewed_required_parts": reviewed_required,
        "required_coverage": ratio(reviewed_required, len(required)), "optional_parts": len(optional),
        "reviewed_optional_parts": sum(p["reviewed"] for p in optional), "required_roles": list(REQUIRED_ROLES), "absent_required_roles": absent_roles,
        "grounded_observations": len(grounded),
        "levels": {
            "package_parts": {"required": len(required), "reviewed": reviewed_required, "coverage": ratio(reviewed_required, len(required))},
            "part_synthesis": {"units": len(part_units), "accepted": sum(u.get("status") == "accepted" for u in part_units),
                               "statements": len(part_statements), "observations": len(grounded), "observations_cited": len(captured_by_part),
                               "observations_carried_forward": len(carried_to_document)},
            "document_synthesis": {"units": len(doc_units), "accepted": sum(u.get("status") == "accepted" for u in doc_units),
                                   "statement_slots": slots, "statements": len(doc_statements),
                                   "inputs": sum(len(u["inputs"]) for u in doc_units), "inputs_cited": len(doc_cited),
                                   "inputs_carried_forward": len(carried_to_final)},
            "final": {**final_state, "inputs": len(final_inputs), "input_chars": len(block), "input_budget": FINAL_INPUT_BUDGET_CHARS,
                      "inputs_cited": len(cited_finally), "inputs_not_cited": len([i for i in final_inputs if i not in set(cited_finally)]),
                      "observations_reached": len(reached), "observation_reach": ratio(len(reached), len(grounded)),
                      "rejected_entries": len(final_rejected)},
            "architecture": {"observations": len(grounded), "represented_in_final_inputs": len(represented & set(items)),
                             "coverage": ratio(len(represented), len(grounded)), "silently_dropped": silently_dropped},
        },
        "rejected_statements": dict(Counter(r["reason"] for r in rejected_statements)),
        "missing": missing, "parts": parts_coverage,
    }
    rejections = Counter(x["rejection"] for x in ledger if x["rejection"])
    stage_order = list(dict.fromkeys(x["stage"] for x in ledger))
    accepted_stages = {x["stage"] for x in ledger if x["accepted"]}
    all_refs = dropped_refs + final_unknown
    statement_record = lambda i: {k: v for k, v in items[i].items()}  # noqa: E731
    artifact = {
        "object": "experiment_review", "contract_version": CONTRACT_VERSION, "review_id": review_id, "status": status,
        "non_authoritative": True, "authority": dict(REVIEW_AUTHORITY), "coverage": coverage,
        "review": review if (first or second) else {},
        "hierarchy": {"part_units": part_units, "part_statements": [statement_record(i) for i in part_statements],
                      "carried_to_document_level": carried_to_document, "document_units": doc_units,
                      "document_statements": [statement_record(i) for i in doc_statements], "carried_to_final": carried_to_final,
                      "final_inputs": final_inputs, "final_inputs_not_cited": [i for i in final_inputs if i not in set(cited_finally)],
                      "rejected_statements": rejected_statements},
        "final_rejected_entries": final_rejected,
        "grounded_observations": grounded, "rejected_observations": rejected, "open_questions": questions,
        "unknown_references": sorted(set(final_unknown) - rejected_ids),
        "dropped_references": sorted(set(dropped_refs) - rejected_ids),
        "rejected_observation_references": sorted(set(all_refs) & rejected_ids),
        "integrity_metrics": {"multi_quote_observations": sum(len(o["quotes"]) > 1 for o in grounded),
                              "omission_quotes": sum(bool(q.get("omission")) for o in grounded for q in o["quotes"]),
                              "observations_with_record_metadata": sum(bool(o["provenance"]["metadata"]) for o in grounded),
                              "observations_rejected_for_unsupported_identifiers": sum(r["reason"] == "unsupported_identifiers" for r in rejected)},
        "provenance": {"experiment_id": package["experiment_id"], "title": package["title"], "package_dir": str(package["dir"]),
                       "manifest_sha256": package["manifest_sha256"],
                       "documents": [{k: d[k] for k in ("doc_id", "role", "path", "sha256", "required")} for d in package["documents"]],
                       "model": ident, "started": started, "finished": clock(), "task": package["manifest"].get("task"),
                       "capability": {"contract_version": CONTRACT_VERSION, "module_sha256": _sha256_file(Path(__file__).resolve()),
                                      "source_tree": before.get("source_tree")},
                       "limits": registered_limits() | {"context_size": context_size},
                       "prompt_templates_sha256": template_digests(), "mutation_authority": "none"},
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


def registered_limits() -> dict[str, Any]:
    return {"observe_max_tokens": OBSERVE_MAX_TOKENS, "part_max_tokens": PART_MAX_TOKENS, "document_max_tokens": DOCUMENT_MAX_TOKENS,
            "final_a_max_tokens": FINAL_A_MAX_TOKENS, "final_b_max_tokens": FINAL_B_MAX_TOKENS, "chunk_chars": CHUNK_CHARS,
            "max_observations_per_chunk": MAX_OBSERVATIONS_PER_CHUNK, "max_quotes_per_observation": MAX_QUOTES_PER_OBSERVATION,
            "max_quote_chars": MAX_QUOTE_CHARS, "max_statement_chars": MAX_STATEMENT_CHARS, "max_ids_per_statement": MAX_IDS_PER_STATEMENT,
            "document_unit_max_inputs": DOCUMENT_UNIT_MAX_INPUTS, "document_unit_input_budget_chars": DOCUMENT_UNIT_INPUT_BUDGET_CHARS,
            "final_input_budget_chars": FINAL_INPUT_BUDGET_CHARS, "final_document_statement_budget_chars": FINAL_DOCUMENT_STATEMENT_BUDGET_CHARS,
            "final_line_overhead_chars": FINAL_LINE_OVERHEAD_CHARS, "first_half_summary_chars": FIRST_HALF_SUMMARY_CHARS,
            "calibrated_chars_per_token": CALIBRATED_CHARS_PER_TOKEN, "metadata_keys": list(METADATA_KEYS), "unit_families": dict(UNIT_FAMILIES)}


def template_digests() -> dict[str, str]:
    return {"observe": digest(OBSERVE_PROMPT), "part": digest(PART_PROMPT), "document": digest(DOCUMENT_PROMPT),
            "final_a": digest(FINAL_A_PROMPT), "final_b": digest(FINAL_B_PROMPT)}


def _missing_text(item: Mapping[str, Any]) -> str:
    kind = item["kind"]
    if kind == "required_role_absent":
        return f"required role absent: {item['role']}"
    if kind == "required_part_not_reviewed":
        return f"{item['stage']} not reviewed: {item['reason']}"
    if kind == "synthesis_stage_failed":
        return f"{item['stage']} ({item['level']} level, {item['doc_id']} parts {', '.join(map(str, item['parts']))}) failed: {item['reason']}"
    if kind == "final_input_exceeds_budget":
        return f"final input {item['chars']} characters ({item['carried_inputs']} carried inputs) exceeds the budget of {item['budget']}"
    if kind == "final_capacity_insufficient":
        return f"final capacity insufficient: {item['units']} document units for {item['slots']} statement slots"
    if kind == "final_synthesis_failed":
        return f"{item['stage']} failed: {item['reason']}"
    return json.dumps(item, ensure_ascii=False)


def _cites(entry: Mapping[str, Any] | None) -> str:
    return f" ({', '.join(entry['input_ids'])})" if entry and entry.get("input_ids") else ""


def render_markdown(artifact: Mapping[str, Any]) -> str:
    r, p, c = artifact.get("review") or {}, artifact["provenance"], artifact["coverage"]
    lv, h = c["levels"], artifact["hierarchy"]
    items = {s["id"]: s for s in h["part_statements"] + h["document_statements"]}
    items.update({o["obs_id"]: {"id": o["obs_id"], "statement": o["statement"], "doc_id": o["doc_id"], "part": o["part"]} for o in artifact["grounded_observations"]})
    lines = [f"# Eidolon research review: {p['title']}", "",
             f"Non-authoritative research artifact. Status: {artifact['status']}. Review {artifact['review_id']}, "
             f"model {p['model'].get('model')}, {p['started']} to {p['finished']}. Mutation guard passed: {artifact['mutation_guard']['passed']}.", "",
             f"Required coverage: {c['reviewed_required_parts']} of {c['required_parts']} package parts reviewed ({c['required_coverage']:.0%}). "
             f"Part synthesis: {lv['part_synthesis']['observations_cited']} of {lv['part_synthesis']['observations']} observations cited, "
             f"{lv['part_synthesis']['observations_carried_forward']} carried forward. Document synthesis: {lv['document_synthesis']['inputs_cited']} of "
             f"{lv['document_synthesis']['inputs']} inputs cited, {lv['document_synthesis']['inputs_carried_forward']} carried forward. Final synthesis: "
             f"first half {lv['final']['first_half']}, second half {lv['final']['second_half']}; {lv['final']['inputs_cited']} of {lv['final']['inputs']} "
             f"inputs cited, reaching {lv['final']['observations_reached']} of {lv['part_synthesis']['observations']} observations. Every observation "
             f"represented at the final level: {lv['architecture']['coverage']:.0%}; silently dropped: {len(lv['architecture']['silently_dropped'])}.", ""]
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
        for n, hyp in enumerate(r["competing_hypotheses"], 1):
            lines.append(f"{n}. {hyp['hypothesis']} For: {', '.join(hyp['evidence_for']) or 'none'}. Against: {', '.join(hyp['evidence_against']) or 'none'}.")
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
    if h["final_inputs_not_cited"]:
        lines += ["## Evidence the final synthesis did not cite", ""] + \
                 [f"- {i}: {items[i]['statement']} (observations {', '.join(items[i].get('lineage', [i]))})" for i in h["final_inputs_not_cited"]] + [""]
    if h["document_statements"] or h["part_statements"]:
        lines += ["## Lineage", ""]
        lines += [f"- {s['id']} [{s['doc_id']}, {s['kind']}]: {s['statement']} (cites {', '.join(s['cites'])})" for s in h["document_statements"]]
        lines += [f"- {s['id']} [{s['doc_id']} part {s['part']}, {s['kind']}]: {s['statement']} (cites {', '.join(s['cites'])})" for s in h["part_statements"]]
        lines.append("")
    lines += ["## Grounded observations", ""]
    for o in artifact["grounded_observations"]:
        meta = _metadata_label(o["provenance"]["metadata"])
        marks = "".join(" [omitted suffix]" for q in o["quotes"] if q.get("omission"))
        lines.append(f"- {o['obs_id']} [{o['doc_id']}, lines {', '.join(str(q['line_start']) for q in o['quotes'])}{'; ' + meta if meta else ''}]: "
                     f"{o['statement']}{marks}")
    return "\n".join(lines) + "\n"


__all__ = ["CONTRACT_VERSION", "REVIEW_AREA", "REVIEW_AUTHORITY", "REQUIRED_ROLES", "ReviewPackageError", "load_package", "chunks",
           "snapshot_protected", "compare_snapshots", "ground_observations", "record_metadata", "observation_evidence", "unsupported_identifiers",
           "plan_part_units", "plan_document_units", "part_prompt", "document_prompt", "validate_statements", "allocate", "document_statement_slots",
           "final_block", "validate_final_first", "validate_final_second", "first_half_summary", "final_input_ids", "lineage_of",
           "support_evidence", "input_line", "registered_limits", "template_digests", "review_experiment", "render_markdown",
           "production_call_model", "model_identity", "runtime_root"]
