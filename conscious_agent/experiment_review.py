from __future__ import annotations

"""Supervised, read-only experiment self-review (spec 2.18, review_experiment).

Given one explicitly selected, completed experiment package, Eidolon inspects it and writes a structured research
review into a separate review area. The review is a non-authoritative research artifact: it cannot change gold labels,
registered verdicts, evidence, memories, beliefs, policies, configuration, patches, experiment authorization or release
state, and this module has no code path that writes anywhere except the review area.

How the review is bounded:
- The package is a directory with ``package_manifest.json``. Only the documents listed there are read. Each must lie
  inside the package directory and match its recorded SHA-256; anything else fails closed before any model call.
- The local model receives text only; it has no tools and no authority. Its reply is data.
- Observation passes: each bounded document chunk yields observations, each carrying a verbatim quote that must be
  found in that chunk. Ungrounded observations are kept in the artifact as rejected and are never used downstream.
- Two synthesis passes turn the grounded observations into the required review sections. Interpretation is kept
  apart from observation, and every interpretive entry refers to observation ids that are checked to exist.
- A deterministic mutation guard fingerprints the protected state before and after the review: the source tree, the
  package, the operator-named registered files, and every file of each protected runtime root except the review area.
  Any change marks the review ``mutation_guard_failed``; the guard does not rely on prompt instructions.
"""

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

from cognitive_coding_foundations import DENIED_AUTHORITY, digest
from json_storage import write_text_atomic

CONTRACT_VERSION = "v2731.5"
REVIEW_AREA = "research_reviews"
MANIFEST_NAME = "package_manifest.json"
DOCUMENT_ROLES = ("design", "prompts", "corpus", "raw_outputs", "scorer", "evidence", "notes", "prior_evidence")
TASK_KINDS = ("independent_review",)
CHUNK_CHARS = 6500
MAX_OBSERVATIONS_PER_CHUNK = 8
MAX_QUOTE_CHARS = 240
MAX_OBSERVATION_CHARS = 300
SYNTHESIS_OBSERVATION_BUDGET_CHARS = 14000
OBSERVE_MAX_TOKENS = 700
SYNTHESIS_MAX_TOKENS = 1600
REVIEW_READ_TIMEOUT_SECONDS = 900.0
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
    "not what it means. For each, copy a short exact quote from this part (quote, at most {max_quote} characters) that shows it. "
    "Also list questions this part raises but does not answer.\n"
    'Return only JSON: {{"observations": [{{"statement": "...", "quote": "..."}}], "open_questions": ["..."]}}'
)
SYNTHESIS_A_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "These are the observations extracted from the package documents, each with an id (observations only; no interpretation yet):\n"
    "{observations}\n"
    "Write the first half of your review. Each entry that interprets the evidence must cite the ids of the observations it rests on "
    "(obs_ids). Keep entries short. Record uncertainty instead of manufacturing a conclusion.\n"
    'Return only JSON: {{"experiment_understanding": "...", "observations": [{{"statement": "...", "obs_ids": ["O1"]}}], '
    '"passed": [{{"statement": "...", "obs_ids": []}}], "failed": [{{"statement": "...", "obs_ids": []}}], '
    '"failure_clusters": [{{"statement": "...", "obs_ids": []}}], "possible_harness_or_measurement_failures": [{{"statement": "...", "obs_ids": []}}], '
    '"possible_model_or_reasoning_failures": [{{"statement": "...", "obs_ids": []}}], "ambiguous_cases": [{{"statement": "...", "obs_ids": []}}]}}'
)
SYNTHESIS_B_PROMPT = (
    FRAME +
    "Experiment: {title}\nTask brief: {brief}\n"
    "Observations from the package (id: statement):\n{observations}\n"
    "Your first-half review found:\n{first_half}\n"
    "Write the second half. Give competing hypotheses that could explain what was observed, each with the observation ids for and "
    "against it. List unknowns. Rate your confidence (low, medium or high) with a reason. Propose the smallest experiments that would "
    "discriminate between the hypotheses, naming which hypotheses each distinguishes (by number, starting at 1). List what the "
    "evidence does not establish.\n"
    'Return only JSON: {{"competing_hypotheses": [{{"hypothesis": "...", "evidence_for": ["O1"], "evidence_against": ["O2"]}}], '
    '"unknowns": ["..."], "confidence": {{"level": "low|medium|high", "reason": "..."}}, '
    '"discriminating_experiments": [{{"experiment": "...", "distinguishes": [1, 2]}}], "not_established": ["..."]}}'
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
        if not target.is_file() or _sha256_file(target) != str(entry.get("sha256") or ""):
            raise ReviewPackageError("package_document_digest_mismatch")
        documents.append({"doc_id": str(entry["doc_id"]), "role": entry["role"], "description": str(entry.get("description") or "")[:200],
                          "path": rel, "sha256": entry["sha256"], "text": target.read_text(encoding="utf-8")})
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
    """Fingerprint everything the review must leave unchanged. The review area itself is the only excluded location."""
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


def _ask(call_model, prompt: str, max_tokens: int, accept: Callable[[dict[str, Any]], bool], ledger: list[dict[str, Any]], stage: str):
    """At most one repair retry over the identical input; every attempt is recorded in the ledger."""
    for attempt, text in enumerate((prompt, REPAIR_PREFACE + prompt), 1):
        raw, meta = call_model(text, max_tokens)
        parsed = _parse(raw or "")
        ok = parsed is not None and accept(parsed)
        ledger.append({"stage": stage, "attempt": attempt, "prompt_sha256": hashlib.sha256(text.encode()).hexdigest()[:16], "reply": raw,
                       "accepted": ok, **meta})
        if ok:
            return parsed
    return None


# --- validation -------------------------------------------------------------------------------------------------------------
def ground_observations(parsed: Mapping[str, Any], chunk_text: str, doc_id: str, part: int, start_index: int):
    grounded, rejected = [], []
    haystack = _norm(chunk_text)
    for n, item in enumerate(parsed.get("observations") or [], 0):
        if not isinstance(item, dict) or len(grounded) + len(rejected) >= MAX_OBSERVATIONS_PER_CHUNK:
            continue
        statement, quote = _norm(item.get("statement") or "")[:MAX_OBSERVATION_CHARS], _norm(item.get("quote") or "")[:MAX_QUOTE_CHARS]
        row = {"doc_id": doc_id, "part": part, "statement": statement, "quote": quote}
        if statement and len(quote) >= 4 and quote in haystack:
            grounded.append({**row, "obs_id": f"O{start_index + len(grounded)}"})
        else:
            rejected.append({**row, "reason": "quote_not_found_in_document" if statement else "empty_statement"})
    questions = [_norm(q)[:300] for q in (parsed.get("open_questions") or []) if isinstance(q, str) and q.strip()][:5]
    return grounded, rejected, questions


def _entries(value: Any, known: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    out, unknown = [], []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict) and _norm(item.get("statement") or ""):
            ids = [str(x) for x in item.get("obs_ids") or [] if isinstance(x, (str, int))]
            bad = [i for i in ids if i not in known]
            unknown += bad
            out.append({"statement": _norm(item["statement"])[:600], "obs_ids": [i for i in ids if i in known], "unknown_obs_ids": bad})
    return out, unknown


def validate_first_half(parsed: Mapping[str, Any], known: set[str]) -> tuple[dict[str, Any], list[str]]:
    section = {"experiment_understanding": _norm(parsed.get("experiment_understanding") or "")[:2000]}
    unknown: list[str] = []
    for key in SECTIONS_A[1:]:
        section[key], bad = _entries(parsed.get(key), known)
        unknown += bad
    return section, unknown


def validate_second_half(parsed: Mapping[str, Any], known: set[str]) -> tuple[dict[str, Any], list[str]]:
    unknown: list[str] = []
    hypotheses = []
    for item in parsed.get("competing_hypotheses") or []:
        if isinstance(item, dict) and _norm(item.get("hypothesis") or ""):
            row = {"hypothesis": _norm(item["hypothesis"])[:600]}
            for side in ("evidence_for", "evidence_against"):
                ids = [str(x) for x in item.get(side) or [] if isinstance(x, (str, int))]
                unknown += [i for i in ids if i not in known]
                row[side] = [i for i in ids if i in known]
            hypotheses.append(row)
    conf = parsed.get("confidence") if isinstance(parsed.get("confidence"), dict) else {}
    experiments = []
    for item in parsed.get("discriminating_experiments") or []:
        if isinstance(item, dict) and _norm(item.get("experiment") or ""):
            idx = [int(x) for x in item.get("distinguishes") or [] if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
            experiments.append({"experiment": _norm(item["experiment"])[:600],
                                "distinguishes": [i for i in idx if 1 <= i <= len(hypotheses)],
                                "distinguishes_unknown": [i for i in idx if not 1 <= i <= len(hypotheses)]})
    listed = lambda key: [_norm(x)[:400] for x in parsed.get(key) or [] if isinstance(x, str) and x.strip()]  # noqa: E731
    return ({"competing_hypotheses": hypotheses, "unknowns": listed("unknowns"),
             "confidence": {"level": conf.get("level") if conf.get("level") in CONFIDENCE_LEVELS else None, "reason": _norm(conf.get("reason") or "")[:600]},
             "discriminating_experiments": experiments, "not_established": listed("not_established")}, unknown)


def _accept_first(parsed: Mapping[str, Any]) -> bool:
    return isinstance(parsed.get("experiment_understanding"), str) and all(isinstance(parsed.get(k), list) for k in SECTIONS_A[1:])


def _accept_second(parsed: Mapping[str, Any]) -> bool:
    return isinstance(parsed.get("competing_hypotheses"), list) and isinstance(parsed.get("confidence"), dict) and \
        all(isinstance(parsed.get(k), list) for k in ("unknowns", "discriminating_experiments", "not_established"))


def _observation_block(grounded: Sequence[Mapping[str, Any]]) -> str:
    lines, used = [], 0
    for o in grounded:
        line = f"{o['obs_id']} [{o['doc_id']}]: {o['statement']}"
        if used + len(line) + 1 > SYNTHESIS_OBSERVATION_BUDGET_CHARS:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


# --- the operation ----------------------------------------------------------------------------------------------------------
def review_experiment(package_dir: str | Path, *, call_model: Callable[[str, int], tuple[str, dict[str, Any]]] | None = None,
                      runtime_root_path: str | Path | None = None, source_root: str | Path | None = None,
                      protected_paths: Iterable[str | Path] = (), protected_roots: Iterable[str | Path] = (),
                      identity: Mapping[str, Any] | None = None, clock: Callable[[], str] = _now) -> dict[str, Any]:
    """Review one explicitly selected package and write the artifact into ``<runtime root>/research_reviews/<review_id>/``."""
    package = load_package(package_dir)
    root = runtime_root(runtime_root_path)
    area = root / REVIEW_AREA
    guarded_roots = [root, *[Path(r).expanduser().resolve() for r in protected_roots]]
    guarded_paths = [Path(p).expanduser().resolve() for p in protected_paths]
    src = Path(source_root).expanduser().resolve() if source_root is not None else None
    before = snapshot_protected(source_root=src, package_dir=package["dir"], protected_paths=guarded_paths, protected_roots=guarded_roots,
                                review_area=area)
    call_model = call_model or production_call_model()
    ident = dict(identity) if identity is not None else model_identity()
    started = clock()
    review_id = hashlib.sha256(f"{package['manifest_sha256']}|{started}".encode()).hexdigest()[:16]
    ledger: list[dict[str, Any]] = []
    grounded, rejected, questions = [], [], []
    for doc in package["documents"]:
        parts = chunks(doc["text"])
        for part, chunk_text in enumerate(parts, 1):
            prompt = OBSERVE_PROMPT.format(title=package["title"], brief=package["brief"], doc_id=doc["doc_id"], role=doc["role"],
                                           description=doc["description"], part=part, parts=len(parts), chunk=chunk_text,
                                           max_obs=MAX_OBSERVATIONS_PER_CHUNK, max_quote=MAX_QUOTE_CHARS)
            parsed = _ask(call_model, prompt, OBSERVE_MAX_TOKENS, lambda p: isinstance(p.get("observations"), list), ledger,
                          f"observe:{doc['doc_id']}:{part}")
            if parsed is None:
                continue
            g, r, q = ground_observations(parsed, chunk_text, doc["doc_id"], part, len(grounded) + 1)
            grounded += g
            rejected += r
            questions += [{"doc_id": doc["doc_id"], "part": part, "question": x} for x in q]
    known = {o["obs_id"] for o in grounded}
    block = _observation_block(grounded)
    first = _ask(call_model, SYNTHESIS_A_PROMPT.format(title=package["title"], brief=package["brief"], observations=block),
                 SYNTHESIS_MAX_TOKENS, _accept_first, ledger, "synthesis:first_half")
    first_half, unknown_a = validate_first_half(first, known) if first else ({}, [])
    second = None
    if first:
        summary = json.dumps({k: [e["statement"] for e in first_half.get(k, [])][:6] for k in SECTIONS_A[2:]}, ensure_ascii=False)[:4000]
        second = _ask(call_model, SYNTHESIS_B_PROMPT.format(title=package["title"], brief=package["brief"], observations=block, first_half=summary),
                      SYNTHESIS_MAX_TOKENS, _accept_second, ledger, "synthesis:second_half")
    second_half, unknown_b = validate_second_half(second, known) if second else ({}, [])
    after = snapshot_protected(source_root=src, package_dir=package["dir"], protected_paths=guarded_paths, protected_roots=guarded_roots,
                               review_area=area)
    changes = compare_snapshots(before, after)
    attempts = len(ledger)
    status = "mutation_guard_failed" if changes else "complete" if first and second else "incomplete"
    artifact = {
        "object": "experiment_review", "contract_version": CONTRACT_VERSION, "review_id": review_id, "status": status,
        "non_authoritative": True, "authority": dict(REVIEW_AUTHORITY),
        "review": {**first_half, **second_half} if first or second else {},
        "grounded_observations": grounded, "rejected_observations": rejected, "open_questions": questions,
        "unknown_references": sorted(set(unknown_a + unknown_b)),
        "provenance": {"experiment_id": package["experiment_id"], "title": package["title"], "package_dir": str(package["dir"]),
                       "manifest_sha256": package["manifest_sha256"],
                       "documents": [{k: d[k] for k in ("doc_id", "role", "path", "sha256")} for d in package["documents"]],
                       "model": ident, "started": started, "finished": clock(), "task": package["manifest"].get("task"),
                       "prompt_templates_sha256": {"observe": digest(OBSERVE_PROMPT), "synthesis_a": digest(SYNTHESIS_A_PROMPT),
                                                   "synthesis_b": digest(SYNTHESIS_B_PROMPT)},
                       "mutation_authority": "none"},
        "runtime_accounting": {"provider_attempts": attempts, "failed_attempts": sum(bool(x.get("error")) for x in ledger),
                               "timeout_attempts": sum("Timeout" in str(x.get("error", "")) for x in ledger),
                               "unparseable_or_rejected_replies": sum(not x["accepted"] and not x.get("error") for x in ledger),
                               "retries": sum(x["attempt"] > 1 for x in ledger),
                               "stages_without_accepted_reply": sorted({x["stage"] for x in ledger} - {x["stage"] for x in ledger if x["accepted"]})},
        "mutation_guard": {"passed": not changes, "changes": changes[:50],
                           "protected": {"source_tree": src is not None, "package": True, "paths": [str(p) for p in guarded_paths],
                                         "roots": [str(r) for r in guarded_roots], "excluded": str(area)}},
        "ledger": ledger,
    }
    out_dir = area / review_id
    write_text_atomic(out_dir / "review.json", json.dumps(artifact, indent=1, ensure_ascii=False))
    write_text_atomic(out_dir / "review.md", render_markdown(artifact))
    return artifact


def render_markdown(artifact: Mapping[str, Any]) -> str:
    r, p = artifact.get("review") or {}, artifact["provenance"]
    lines = [f"# Eidolon research review: {p['title']}", "",
             f"Non-authoritative research artifact. Status: {artifact['status']}. Review {artifact['review_id']}, "
             f"model {p['model'].get('model')}, {p['started']} to {p['finished']}. Mutation guard passed: {artifact['mutation_guard']['passed']}.", ""]
    if r.get("experiment_understanding"):
        lines += ["## Experiment understanding", "", r["experiment_understanding"], ""]
    titles = {"observations": "Observations", "passed": "Behaviours that passed", "failed": "Behaviours that failed",
              "failure_clusters": "Failure clusters", "possible_harness_or_measurement_failures": "Possible harness or measurement failures",
              "possible_model_or_reasoning_failures": "Possible model or reasoning failures", "ambiguous_cases": "Ambiguous cases"}
    for key, title in titles.items():
        if r.get(key):
            lines += [f"## {title}", ""] + [f"- {e['statement']}" + (f" ({', '.join(e['obs_ids'])})" if e["obs_ids"] else "") for e in r[key]] + [""]
    if r.get("competing_hypotheses"):
        lines += ["## Competing hypotheses", ""]
        for n, h in enumerate(r["competing_hypotheses"], 1):
            lines.append(f"{n}. {h['hypothesis']} For: {', '.join(h['evidence_for']) or 'none'}. Against: {', '.join(h['evidence_against']) or 'none'}.")
        lines.append("")
    for key, title in (("unknowns", "Unknowns"), ("not_established", "Not established by the evidence")):
        if r.get(key):
            lines += [f"## {title}", ""] + [f"- {x}" for x in r[key]] + [""]
    if r.get("confidence"):
        lines += ["## Confidence", "", f"{r['confidence'].get('level')}: {r['confidence'].get('reason')}", ""]
    if r.get("discriminating_experiments"):
        lines += ["## Smallest discriminating experiments", ""] + \
                 [f"- {e['experiment']} (distinguishes hypotheses {', '.join(map(str, e['distinguishes'])) or 'none named'})" for e in r["discriminating_experiments"]] + [""]
    lines += ["## Grounded observations", ""] + [f"- {o['obs_id']} [{o['doc_id']}]: {o['statement']}" for o in artifact["grounded_observations"]]
    return "\n".join(lines) + "\n"


__all__ = ["CONTRACT_VERSION", "REVIEW_AREA", "REVIEW_AUTHORITY", "ReviewPackageError", "load_package", "chunks", "snapshot_protected",
           "compare_snapshots", "ground_observations", "validate_first_half", "validate_second_half", "review_experiment", "render_markdown",
           "production_call_model", "model_identity", "runtime_root"]
