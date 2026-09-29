"""G-ROUTE4 B′ gold adjudication harness (frozen procedure; amended O2 configuration).

Procedure (DESIGN_CANDIDATE.md "Gold adjudication", G-ROUTE4_OBLIGATIONS.md O1/O2, carried note N4):
- every B′ main fixture gets adjudicator 1;
- each of the 38 audit-sample fixtures always gets adjudicators 2 and 3 (N4);
- a non-sampled fixture whose adjudicator-1 answer disagrees with gold also gets adjudicators 2 and 3;
- disagreement = the answer fails the frozen operational or semantic validator against gold; a second no-answer on a
  slot is a disagreement;
- every answer is sealed by a committed digest before it is compared with gold.

Integrity rules implemented here:
- one fresh, independent Messages API request per invocation; no tools; the frozen prompt and rendering;
- a write-ahead intent record is fsynced before each request; the raw response bytes are fsynced before the result
  record; recovery completes a result from a durable raw response and never re-sends an in-doubt invocation;
- the binding answer is the concatenated text of the first final message for the slot; only the frozen single
  no-answer retry is permitted;
- the `run` path never reads gold; scoring refuses unless the answer digests are committed.

    python -B g4_adjudicate.py verify                              # bindings, no network
    python -B g4_adjudicate.py schedule                            # the phase-1 schedule
    python -B g4_adjudicate.py run --run-id ID --phase 1 [--workers N]
    python -B g4_adjudicate.py seal-answers --run-id ID --phase 1  # writes answers_phase1.json (commit it next)
    python -B g4_adjudicate.py score --run-id ID --phase 1         # requires the committed answers file
    python -B g4_adjudicate.py run --run-id ID --phase 2
    python -B g4_adjudicate.py decide --run-id ID
"""

import argparse
import collections
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "experiments/G-ROUTE4-candidate/blueprint"))
import o2_amendment as O2  # noqa: E402

SEALED = ROOT / "experiments/G-ROUTE4-candidate/sealed"
SAMPLE_FILE = ROOT / "experiments/G-ROUTE4-candidate/audit_sample/AUDIT_SAMPLE.json"
PROFILES = ROOT / "experiments/G-ROUTE1-candidate/prompt_profiles.json"
RUNS = HERE / "runs"
KEY_FILE = Path.home() / ".config/g-route4/anthropic_api_key"
MANIFEST_SHA256 = "98306eeb37f16da6f0991b17ece9e49abb428e2eb28cedc2a2cdd8baf1cd3a01"
SAMPLE_DIGEST = "166f1f44c111a07fd4daee5fd3f12115d02285f3076ad16489b972d674bbd29e"
AMENDED_CONFIG_SHA256 = "7691126e6a96974d43f816ee61253332ba5b2510395de2baa8fdd7342581d516"
NO_ANSWER_STATUSES = {408, 429, 500, 502, 503, 504, 529}
MAX_RETRY_WAIT = 600.0


class StopBatch(Exception):
    def __init__(self, kind, detail):
        super().__init__(f"{kind}: {detail}")
        self.kind, self.detail = kind, detail


class NotSent(Exception):
    """The request never left this machine (connection could not be established)."""


class InDoubt(Exception):
    """The request may have reached the provider, but no response was received."""


class SimulatedCrash(BaseException):
    """Test-only: stands in for a process death at a named point."""


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def lf_sha256(path):
    return sha256(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def utc_now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def fsync_write(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


# ---------------------------------------------------------------- frozen inputs (model-facing only on the run path)
def amended_config():
    cfg = O2.verify()
    if cfg["config_sha256"] != AMENDED_CONFIG_SHA256:
        raise StopBatch("binding", "amended O2 configuration digest differs from the recorded amendment")
    return cfg


def model_facing_b():
    fixtures = json.loads((SEALED / "corpus_b.json").read_text(encoding="utf-8"))["fixtures"]
    return {f["fixture_id"]: f for f in fixtures}


def audit_sample():
    record = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    if sha256(json.dumps(record["sample"], sort_keys=True).encode("ascii")) != SAMPLE_DIGEST:
        raise StopBatch("binding", "audit sample digest differs")
    return sorted(i for ids in record["sample"].values() for i in ids)


def render(fixture, cfg):
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]
    template = cfg["prompt_template"]
    return {"system": template["system"].replace("{PROMPT_PROFILE_TEXT}", profiles[fixture["validator_profile"]]),
            "user": template["user"].replace("{FIXTURE_PROMPT}", fixture["prompt"])
                                    .replace("{CANONICAL_INPUT_JSON}", canonical(fixture["input"]))}


def request_body(fixture, cfg):
    """The exact request bytes: the amended body template, filled; nothing else."""
    rendered = render(fixture, cfg)
    template = cfg["request"]["body_template"]
    body = {"model": template["model"], "max_tokens": template["max_tokens"], "system": rendered["system"],
            "messages": [{"role": "user", "content": rendered["user"]}],
            "output_config": dict(template["output_config"])}
    forbidden = set(cfg["request"]["absent_fields"]) & set(body)
    if forbidden:
        raise StopBatch("binding", f"request would carry forbidden fields {sorted(forbidden)}")
    return canonical(body).encode("utf-8")


def phase1_schedule(fixture_ids, sample_ids):
    return [(fid, 1) for fid in sorted(fixture_ids)] + [(fid, s) for fid in sorted(sample_ids) for s in (2, 3)]


def verify_bindings(repo=ROOT):
    """Everything the run binds to, checked from the committed tree. No network."""
    out = {}
    head = git("rev-parse", "HEAD", cwd=repo).stdout.strip()
    out["head"] = head
    for name, commit in (("seal", O2.SEAL_COMMIT), ("audit_sample", O2.AUDIT_SAMPLE_COMMIT)):
        if git("merge-base", "--is-ancestor", commit, head, cwd=repo).returncode != 0:
            raise StopBatch("binding", f"{name} commit {commit} is not an ancestor of HEAD")
    if git("rev-parse", f"{O2.AUDIT_SAMPLE_COMMIT}^", cwd=repo).stdout.strip() != O2.SEAL_COMMIT or \
            git("rev-parse", f"{O2.SEAL_COMMIT}^", cwd=repo).stdout.strip() != "1156d0645b1b113b91c65e4a485b7f75ffa10061":
        raise StopBatch("binding", "seal or audit-sample parentage differs")
    # digests are over the committed (LF) bytes; a Windows checkout may show CRLF, so compare LF-normalized content
    if lf_sha256(SEALED / "SEAL_MANIFEST.json") != MANIFEST_SHA256:
        raise StopBatch("binding", "seal manifest digest differs")
    manifest = json.loads((SEALED / "SEAL_MANIFEST.json").read_text(encoding="utf-8"))
    for name, rec in manifest["files"].items():
        if lf_sha256(SEALED / name) != rec["file_sha256"]:
            raise StopBatch("binding", f"sealed file {name} differs from the manifest")
    sealed_cfg = json.loads((SEALED / "adjudicator_config.json").read_text(encoding="utf-8"))
    if sealed_cfg["config_sha256"] != O2.SEALED_CONFIG_SHA256:
        raise StopBatch("binding", "sealed O2 configuration digest differs")
    cfg = amended_config()
    for key in ("adjudicator", "sessions", "input_rendering", "prompt_template", "judgement"):
        if cfg[key] != sealed_cfg[key]:
            raise StopBatch("binding", f"amended O2 {key} differs from the sealed configuration")
    if lf_sha256(ROOT / "tools/g_route3_contract.py") != cfg["input_rendering"]["render_tool_sha256"] or \
            lf_sha256(PROFILES) != cfg["input_rendering"]["prompt_profiles_sha256"]:
        raise StopBatch("binding", "rendering tool or prompt profiles differ from the pinned digests")
    fixtures = model_facing_b()
    sample = audit_sample()
    import audit_sample as AS
    blueprint = json.loads((ROOT / "experiments/G-ROUTE4-candidate/blueprint/BLUEPRINT.json").read_text(encoding="utf-8"))
    derived = AS.derive_sample(O2.SEAL_COMMIT, AS.b_cells_from_blueprint(blueprint))
    if sorted(i for ids in derived.values() for i in ids) != sample or len(sample) != 38 or \
            not set(sample) <= set(fixtures):
        raise StopBatch("binding", "audit sample does not re-derive from the seal id, or is not in B′ main")
    from g_route3_contract import render_prompt
    for fid, fixture in fixtures.items():
        r = render(fixture, cfg)
        ref = render_prompt(fixture)
        if r != {"system": ref["system"], "user": ref["prompt"]}:
            raise StopBatch("binding", f"{fid}: frozen-template rendering differs from the models' rendering")
    out.update({"b_main_fixtures": len(fixtures), "audit_sample": len(sample), "sealed_config": O2.SEALED_CONFIG_SHA256,
                "amended_config": cfg["config_sha256"], "manifest": MANIFEST_SHA256, "sample_digest": SAMPLE_DIGEST})
    return out


# ---------------------------------------------------------------- journal
class Journal:
    """Append-only, hash-chained, fsynced JSON-lines log. Each record carries the previous record's sha256."""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.records, self.prev = [], "0" * 64
        if self.path.exists():
            for n, line in enumerate(self.path.read_bytes().decode("utf-8").splitlines()):
                rec = json.loads(line)
                if rec.get("seq") != n or rec.get("prev") != self.prev:
                    raise StopBatch("integrity", f"journal chain broken at line {n}")
                self.records.append(rec)
                self.prev = sha256(line)

    def append(self, record):
        with self.lock:
            rec = dict(record, seq=len(self.records), prev=self.prev, utc=utc_now())
            line = canonical(rec)
            with open(self.path, "ab") as handle:
                handle.write(line.encode("utf-8") + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            self.records.append(rec)
            self.prev = sha256(line)
            return rec


# ---------------------------------------------------------------- provider
class AnthropicProvider:
    """The frozen channel: POST to the Messages API with the operator's key. The key never leaves this object."""

    def __init__(self, cfg, key_file=KEY_FILE):
        import httpx
        key = Path(key_file).read_text(encoding="ascii").strip()
        if not key.startswith("sk-ant-") or any(c.isspace() for c in key):
            raise StopBatch("credential", "API key file is not a well-formed key")
        self._headers = {"x-api-key": key, "anthropic-version": cfg["request"]["headers"]["anthropic-version"],
                         "content-type": "application/json"}
        self._url = cfg["request"]["endpoint"]
        self._client = httpx.Client(trust_env=False, timeout=httpx.Timeout(900.0, connect=30.0))
        self._httpx = httpx

    def preflight(self, model):
        """A non-generation check of the key and model id (Models API). No model is invoked."""
        try:
            r = self._client.get(f"https://api.anthropic.com/v1/models/{model}", headers=self._headers)
        except self._httpx.HTTPError as exc:
            raise StopBatch("credential", f"preflight transport failure: {type(exc).__name__}")
        return r.status_code, {k: v for k, v in r.headers.items() if k.lower() in ("request-id",)}, r.content

    def send(self, body):
        try:
            r = self._client.post(self._url, content=body, headers=self._headers)
        except (self._httpx.ConnectError, self._httpx.ConnectTimeout) as exc:
            raise NotSent(type(exc).__name__)
        except self._httpx.HTTPError as exc:
            raise InDoubt(type(exc).__name__)
        return r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.content


KEPT_HEADERS = ("request-id", "retry-after", "content-type", "anthropic-organization-id")


def kept_headers(headers):
    return {k: v for k, v in headers.items() if k in KEPT_HEADERS or k.startswith("anthropic-ratelimit-")}


class Pacer:
    """Waits before sending when the provider's own rate-limit headers show the window is nearly spent."""

    def __init__(self, sleep=time.sleep, clock=time.time):
        self.lock, self.until, self.sleep, self.clock = threading.Lock(), 0.0, sleep, clock

    def wait(self):
        while True:
            with self.lock:
                delay = self.until - self.clock()
            if delay <= 0:
                return
            self.sleep(min(delay, 30.0))

    def hold(self, seconds):
        with self.lock:
            self.until = max(self.until, self.clock() + seconds)

    def update(self, headers):
        def remaining(name):
            try:
                return int(headers.get(f"anthropic-ratelimit-{name}-remaining", ""))
            except ValueError:
                return None

        def reset(name):
            value = headers.get(f"anthropic-ratelimit-{name}-reset")
            if not value:
                return 60.0
            try:
                when = dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
                return max(1.0, when - self.clock())
            except ValueError:
                return 60.0
        for name, floor in (("requests", 2), ("input-tokens", 8000), ("output-tokens", 8000)):
            left = remaining(name)
            if left is not None and left < floor:
                self.hold(reset(name))


# ---------------------------------------------------------------- the run
def binding_text(message):
    return "".join(block.get("text", "") for block in message.get("content", []) if block.get("type") == "text")


def classify(status, headers, body, model):
    rec = {"status": status, "headers": kept_headers(headers), "raw_body_sha256": sha256(body)}
    if status == 200:
        try:
            message = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            message = None
        if not isinstance(message, dict) or message.get("type") != "message":
            return dict(rec, kind="integrity", detail="HTTP 200 without a message object")
        fallback = any(b.get("type") == "fallback" for b in message.get("content", []) if isinstance(b, dict)) or \
            any("fallback" in str(it.get("type", "")) for it in (message.get("usage") or {}).get("iterations", [])
                if isinstance(it, dict))
        text = binding_text(message)
        rec.update(kind="final_message", message_id=message.get("id"), model=message.get("model"),
                   stop_reason=message.get("stop_reason"), usage=message.get("usage"),
                   binding_text_sha256=sha256(text), binding_text_chars=len(text))
        if message.get("model") != model or fallback:
            rec.update(kind="integrity", detail="response model differs from the frozen model, or a fallback ran")
        return rec
    if status in NO_ANSWER_STATUSES:
        return dict(rec, kind="no_answer")
    return dict(rec, kind="request_rejected")


def retry_after(headers):
    try:
        return min(MAX_RETRY_WAIT, max(1.0, float(headers.get("retry-after", "60"))))
    except ValueError:
        return 60.0


class Runner:
    def __init__(self, run_dir, cfg, provider, fixtures, workers=2, sleep=time.sleep, crash=None, pacer=None):
        self.dir = Path(run_dir)
        self.raw = self.dir / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.cfg, self.provider, self.fixtures, self.workers = cfg, provider, fixtures, workers
        self.sleep, self.crash = sleep, crash or (lambda point, slot, inv: None)
        self.pacer = pacer or Pacer(sleep=sleep)
        self.journal = Journal(self.dir / "journal.jsonl")
        self.stop = threading.Event()
        self.model = cfg["request"]["body_template"]["model"]

    # ---- state
    def slots(self):
        """{(fid, slot): {"invocations": {inv: {"intent":..., "result":...}}, "in_doubt": bool}}"""
        state = {}
        for rec in self.journal.records:
            if rec["type"] not in ("intent", "result", "in_doubt"):
                continue
            key = (rec["fixture_id"], rec["slot"])
            entry = state.setdefault(key, {"invocations": {}, "in_doubt": False})
            inv = entry["invocations"].setdefault(rec["invocation"], {})
            if rec["type"] == "intent":
                inv["intent"] = rec
            elif rec["type"] == "result":
                inv["result"] = rec
            else:
                entry["in_doubt"] = True
        return state

    def slot_outcome(self, entry):
        if entry["in_doubt"]:
            return "in_doubt"
        results = [entry["invocations"][i].get("result") for i in sorted(entry["invocations"])]
        kinds = [r["kind"] for r in results if r and r["kind"] != "not_sent"]   # never sent: slot not consumed
        if "final_message" in kinds:
            return "bound"
        if "integrity" in kinds or "request_rejected" in kinds:
            return "stopped"
        if kinds.count("no_answer") >= 2:
            return "no_answer_twice"
        return "retry" if kinds.count("no_answer") == 1 else "pending"

    def unresolved_stops(self):
        resolved = {r["resolves"] for r in self.journal.records if r["type"] == "operator_resolution"}
        return [r for r in self.journal.records if r["type"] == "stop" and r["seq"] not in resolved]

    def raw_paths(self, fid, slot, inv):
        stem = f"{fid}__s{slot}__i{inv}"
        return self.raw / f"{stem}.body", self.raw / f"{stem}.meta.json"

    def recover(self):
        """Complete results for durable raw responses; mark everything else interrupted as in doubt."""
        in_doubt = []
        for (fid, slot), entry in sorted(self.slots().items()):
            for inv, parts in sorted(entry["invocations"].items()):
                if "intent" in parts and "result" not in parts and not entry["in_doubt"]:
                    body_path, meta_path = self.raw_paths(fid, slot, inv)
                    if body_path.exists() and meta_path.exists():
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                        body = body_path.read_bytes()
                        if meta.get("raw_body_sha256") == sha256(body) and \
                                meta.get("request_sha256") == parts["intent"]["request_sha256"]:
                            rec = classify(meta["status"], meta["headers"], body, self.model)
                            self.journal.append(dict(rec, type="result", fixture_id=fid, slot=slot, invocation=inv,
                                                     config_sha256=self.cfg["config_sha256"],
                                                     request_sha256=meta["request_sha256"], recovered=True))
                            continue
                    self.journal.append({"type": "in_doubt", "fixture_id": fid, "slot": slot, "invocation": inv,
                                         "config_sha256": self.cfg["config_sha256"],
                                         "detail": "write-ahead intent without a durable response; never re-sent"})
                    in_doubt.append((fid, slot, inv))
        return in_doubt

    # ---- one slot
    def run_slot(self, fid, slot):
        body = request_body(self.fixtures[fid], self.cfg)
        request_sha = sha256(body)
        while not self.stop.is_set():
            entry = self.slots().get((fid, slot), {"invocations": {}, "in_doubt": False})
            outcome = self.slot_outcome(entry)
            if outcome not in ("pending", "retry"):
                return outcome
            inv = max(entry["invocations"], default=0) + 1
            if outcome == "retry":
                last = entry["invocations"][inv - 1]["result"]
                self.sleep(retry_after(last["headers"]))
            self.pacer.wait()
            if self.stop.is_set():
                return "not_started"
            self.crash("before_intent", (fid, slot), inv)
            self.journal.append({"type": "intent", "fixture_id": fid, "slot": slot, "invocation": inv,
                                 "request_sha256": request_sha, "config_sha256": self.cfg["config_sha256"]})
            self.crash("after_intent", (fid, slot), inv)
            try:
                status, headers, raw = self.provider.send(body)
            except NotSent as exc:
                self.journal.append({"type": "result", "kind": "not_sent", "fixture_id": fid, "slot": slot,
                                     "invocation": inv, "detail": str(exc), "request_sha256": request_sha,
                                     "config_sha256": self.cfg["config_sha256"]})
                raise StopBatch("not_sent", f"{fid} slot {slot}: connection failed before sending ({exc})")
            except InDoubt as exc:
                self.journal.append({"type": "in_doubt", "fixture_id": fid, "slot": slot, "invocation": inv,
                                     "config_sha256": self.cfg["config_sha256"],
                                     "detail": f"transport failure after sending: {exc}"})
                raise StopBatch("in_doubt", f"{fid} slot {slot} invocation {inv}: {exc}")
            self.crash("after_send", (fid, slot), inv)
            body_path, meta_path = self.raw_paths(fid, slot, inv)
            fsync_write(body_path, raw)
            fsync_write(meta_path, canonical({"status": status, "headers": kept_headers(headers),
                                              "raw_body_sha256": sha256(raw), "request_sha256": request_sha,
                                              "config_sha256": self.cfg["config_sha256"],
                                              "received_utc": utc_now()}).encode("utf-8"))
            self.crash("after_raw", (fid, slot), inv)
            rec = classify(status, headers, raw, self.model)
            self.journal.append(dict(rec, type="result", fixture_id=fid, slot=slot, invocation=inv,
                                     request_sha256=request_sha, config_sha256=self.cfg["config_sha256"]))
            self.pacer.update(headers)
            if rec["kind"] == "final_message":
                return "bound"
            if rec["kind"] == "integrity":
                raise StopBatch("integrity", f"{fid} slot {slot}: {rec.get('detail')}")
            if rec["kind"] == "request_rejected":
                raise StopBatch("request_rejected", f"{fid} slot {slot}: HTTP {status}")
            if status in (429, 529):
                self.pacer.hold(retry_after(headers))
            if inv >= 2 or self.slot_outcome(self.slots()[(fid, slot)]) == "no_answer_twice":
                raise StopBatch("no_answer_twice", f"{fid} slot {slot}: second no-answer (HTTP {status}); "
                                                   "recorded as a disagreement")
        return "not_started"

    # ---- a schedule
    def run(self, schedule, phase):
        stops = self.unresolved_stops()
        if stops:
            raise StopBatch("unresolved_stop", f"journal has an unresolved stop (seq {stops[0]['seq']}): "
                                               f"{stops[0]['kind']}")
        in_doubt = self.recover()
        if in_doubt:
            rec = self.journal.append({"type": "stop", "kind": "in_doubt", "phase": phase,
                                       "detail": f"in-doubt invocations {in_doubt}"})
            raise StopBatch("in_doubt", f"stop seq {rec['seq']}: {in_doubt}")
        self.journal.append({"type": "phase_start", "phase": phase, "schedule_sha256": sha256(canonical(schedule)),
                             "slots": len(schedule), "config_sha256": self.cfg["config_sha256"]})
        failures = []

        def work(item):
            if self.stop.is_set():
                return item, "not_started"
            try:
                return item, self.run_slot(*item)
            except StopBatch as exc:
                self.stop.set()
                failures.append(exc)
                return item, "stopped"

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
            outcomes = dict(pool.map(work, [tuple(s) for s in schedule]))
        if failures:
            first = failures[0]
            self.journal.append({"type": "stop", "kind": first.kind, "phase": phase, "detail": first.detail,
                                 "all": [str(f) for f in failures]})
            raise first
        self.journal.append({"type": "phase_complete", "phase": phase,
                             "outcomes": dict(sorted(collections.Counter(outcomes.values()).items()))})
        return outcomes


# ---------------------------------------------------------------- answers, scoring, decisions (gold is read here only)
def answers(runner, schedule, phase):
    state = runner.slots()
    rows = []
    for fid, slot in schedule:
        entry = state.get((fid, slot))
        if entry is None:
            raise StopBatch("incomplete", f"{fid} slot {slot} was never contacted")
        outcome = runner.slot_outcome(entry)
        if outcome in ("pending", "retry"):
            raise StopBatch("incomplete", f"{fid} slot {slot} is not finished ({outcome})")
        invocations = []
        for inv, parts in sorted(entry["invocations"].items()):
            r = parts.get("result") or {}
            invocations.append({"invocation": inv, "kind": r.get("kind", "in_doubt"), "status": r.get("status"),
                                "raw_body_sha256": r.get("raw_body_sha256"),
                                "request_sha256": parts["intent"]["request_sha256"],
                                "request_id": (r.get("headers") or {}).get("request-id"),
                                "message_id": r.get("message_id"), "stop_reason": r.get("stop_reason"),
                                "binding_text_sha256": r.get("binding_text_sha256")})
        binding = next((i for i in invocations if i["kind"] == "final_message"), None)
        rows.append({"fixture_id": fid, "slot": slot, "outcome": outcome, "invocations": invocations,
                     "binding_invocation": binding and binding["invocation"],
                     "binding_text_sha256": binding and binding["binding_text_sha256"]})
    return {"schema_version": "g-route4.adjudication-answers.v1", "phase": phase,
            "config_sha256": runner.cfg["config_sha256"], "journal_sha256": sha256(runner.journal.path.read_bytes()),
            "journal_records": len(runner.journal.records), "schedule_sha256": sha256(canonical(schedule)),
            "slots": rows}


def require_committed(path, repo=ROOT):
    rel = Path(path).resolve().relative_to(Path(repo).resolve()).as_posix()
    if git("ls-files", "--error-unmatch", rel, cwd=repo).returncode != 0:
        raise StopBatch("not_sealed", f"{rel} is not committed; answers must be sealed by a commit before comparison")
    if git("diff", "--quiet", "HEAD", "--", rel, cwd=repo).returncode != 0:
        raise StopBatch("not_sealed", f"{rel} differs from its committed version")
    return git("log", "-1", "--format=%H", "--", rel, cwd=repo).stdout.strip()


def score(runner, answers_path, repo=ROOT, gold_path=SEALED / "gold_b.json"):
    commit = require_committed(answers_path, repo)
    sealed_answers = json.loads(Path(answers_path).read_text(encoding="utf-8"))
    from g_route3_operational import validate_operational
    from g_route3_semantics import validate_fixture_output
    gold = {g["fixture_id"]: g for g in json.loads(Path(gold_path).read_text(encoding="utf-8"))["items"]}
    rows = []
    for row in sealed_answers["slots"]:
        fid, slot = row["fixture_id"], row["slot"]
        result = {"fixture_id": fid, "slot": slot, "outcome": row["outcome"]}
        if row["outcome"] == "bound":
            body_path, _ = runner.raw_paths(fid, slot, row["binding_invocation"])
            raw = body_path.read_bytes()
            binding = next(i for i in row["invocations"] if i["invocation"] == row["binding_invocation"])
            if sha256(raw) != binding["raw_body_sha256"]:
                raise StopBatch("integrity", f"{fid} slot {slot}: raw response differs from its sealed digest")
            text = binding_text(json.loads(raw.decode("utf-8")))
            if sha256(text) != row["binding_text_sha256"]:
                raise StopBatch("integrity", f"{fid} slot {slot}: binding text differs from its sealed digest")
            fixture = runner.fixtures[fid]
            op = validate_operational(fixture, text)
            sem = validate_fixture_output(fixture, gold[fid], text)
            agree = bool(op.get("accepted")) and bool(sem.get("hard_gate_pass"))
            result.update(agree=agree, stop_reason=binding["stop_reason"],
                          operational_reasons=op.get("reasons", []), semantic_reasons=sem.get("reasons", []))
        elif row["outcome"] == "no_answer_twice":
            result.update(agree=False, reason="second no-answer (frozen rule: a disagreement)")
        else:
            result.update(agree=None, reason=f"no verdict: slot outcome {row['outcome']}")
        rows.append(result)
    return {"schema_version": "g-route4.adjudication-scores.v1", "phase": sealed_answers["phase"],
            "answers_commit": commit, "answers_sha256": sha256(Path(answers_path).read_bytes()),
            "config_sha256": sealed_answers["config_sha256"], "slots": rows}


def phase2_schedule(scores_phase1, sample_ids):
    sample = set(sample_ids)
    disagreed = sorted(r["fixture_id"] for r in scores_phase1["slots"]
                       if r["slot"] == 1 and r["agree"] is False and r["fixture_id"] not in sample)
    return [(fid, s) for fid in disagreed for s in (2, 3)]


def decide(score_rows, fixture_ids, sample_ids):
    """Frozen B′ decision per fixture. 'operator' means the operator decides (never automatically)."""
    by = {(r["fixture_id"], r["slot"]): r["agree"] for r in score_rows}
    sample = set(sample_ids)
    out = {}
    for fid in sorted(fixture_ids):
        a1, a2, a3 = by.get((fid, 1)), by.get((fid, 2)), by.get((fid, 3))
        sampled = fid in sample
        if a1 is None or ((sampled or a1 is False) and (a2 is None or a3 is None)):
            decision = "incomplete"
        elif a1 and not sampled:
            decision = "keep"
        elif a1 and sampled:
            decision = "keep" if (a2 and a3) else "operator"
        else:
            decision = "keep" if (a2 and a3) else "operator"
        out[fid] = {"sampled": sampled, "a1": a1, "a2": a2, "a3": a3, "decision": decision,
                    "flag": "first adjudicator disagreed; two further agreed" if (a1 is False and a2 and a3) else None}
    return out


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["verify", "schedule", "run", "seal-answers", "score", "decide", "resolve"])
    ap.add_argument("--run-id")
    ap.add_argument("--phase", type=int, choices=[1, 2])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--stop-seq", type=int)
    ap.add_argument("--decision")
    args = ap.parse_args(argv)
    cfg = amended_config()
    fixtures = model_facing_b()
    sample = audit_sample()
    if args.command == "verify":
        print(json.dumps(verify_bindings(), indent=1))
        return 0
    if args.command == "schedule":
        s1 = phase1_schedule(fixtures, sample)
        print(json.dumps({"phase1_slots": len(s1), "first_adjudicator_slots": sum(1 for _, s in s1 if s == 1),
                          "audit_additional_slots": sum(1 for _, s in s1 if s > 1),
                          "schedule_sha256": sha256(canonical(s1))}, indent=1))
        return 0
    run_dir = RUNS / args.run_id
    if args.command == "resolve":
        runner = Runner(run_dir, cfg, None, fixtures)
        runner.journal.append({"type": "operator_resolution", "resolves": args.stop_seq, "decision": args.decision})
        return 0
    if args.command == "run":
        for path in (Path(__file__), HERE / "o2_amendment.py", HERE / "adjudicator_config_amended.json"):
            require_committed(path)                  # a run binds to a committed harness and amendment
        verify_bindings()
        provider = AnthropicProvider(cfg)
        runner = Runner(run_dir, cfg, provider, fixtures, workers=args.workers)
        if not any(r["type"] == "run_start" for r in runner.journal.records):
            status, headers, body = provider.preflight(cfg["request"]["body_template"]["model"])
            runner.journal.append({"type": "preflight", "endpoint": "GET /v1/models/{model}", "status": status,
                                   "request_id": headers.get("request-id"), "body_sha256": sha256(body)})
            if status != 200 or json.loads(body.decode("utf-8")).get("id") != cfg["request"]["body_template"]["model"]:
                raise StopBatch("credential", f"Models API preflight returned HTTP {status}")
            runner.journal.append({"type": "run_start", "config_sha256": cfg["config_sha256"],
                                   "harness_sha256": lf_sha256(__file__), "harness_commit": git("rev-parse", "HEAD").stdout.strip(),
                                   "seal_commit": O2.SEAL_COMMIT, "audit_sample_commit": O2.AUDIT_SAMPLE_COMMIT,
                                   "sealed_config_sha256": O2.SEALED_CONFIG_SHA256, "manifest_sha256": MANIFEST_SHA256,
                                   "sample_digest": SAMPLE_DIGEST})
        if args.phase == 1:
            schedule = phase1_schedule(fixtures, sample)
        else:
            scores1 = json.loads((run_dir / "scores_phase1.json").read_text(encoding="utf-8"))
            require_committed(run_dir / "scores_phase1.json")
            schedule = phase2_schedule(scores1, sample)
        outcomes = runner.run(schedule, args.phase)
        print(json.dumps(dict(sorted(collections.Counter(outcomes.values()).items()))))
        return 0
    runner = Runner(run_dir, cfg, None, fixtures)
    if args.command == "seal-answers":
        if args.phase == 1:
            schedule = phase1_schedule(fixtures, sample)
        else:
            schedule = phase2_schedule(json.loads((run_dir / "scores_phase1.json").read_text(encoding="utf-8")), sample)
        doc = answers(runner, schedule, args.phase)
        fsync_write(run_dir / f"answers_phase{args.phase}.json", (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print(json.dumps({"answers": f"answers_phase{args.phase}.json", "slots": len(doc["slots"]),
                          "sha256": sha256((run_dir / f"answers_phase{args.phase}.json").read_bytes())}))
        return 0
    if args.command == "score":
        doc = score(runner, run_dir / f"answers_phase{args.phase}.json")
        fsync_write(run_dir / f"scores_phase{args.phase}.json", (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print(json.dumps({"scored": len(doc["slots"]), "agree": sum(1 for r in doc["slots"] if r["agree"]),
                          "disagree": sum(1 for r in doc["slots"] if r["agree"] is False),
                          "no_verdict": sum(1 for r in doc["slots"] if r["agree"] is None)}))
        return 0
    if args.command == "decide":
        rows = []
        for phase in (1, 2):
            path = run_dir / f"scores_phase{phase}.json"
            if path.exists():
                require_committed(path)
                rows += json.loads(path.read_text(encoding="utf-8"))["slots"]
        decisions = decide(rows, fixtures, sample)
        fsync_write(run_dir / "decisions.json", (json.dumps(decisions, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print(json.dumps(dict(sorted(collections.Counter(d["decision"] for d in decisions.values()).items()))))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except StopBatch as exc:
        print(f"STOPPED ({exc.kind}): {exc.detail}", file=sys.stderr)
        sys.exit(3)
