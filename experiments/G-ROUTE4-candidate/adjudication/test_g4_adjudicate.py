"""Offline tests of the G-ROUTE4 adjudication harness against a fake provider. No network, no model.

Covers: success, refusal, malformed answer, truncation, no-answer retry, second no-answer, provider rejection,
crash before send, crash after the write-ahead record, crash after send before the durable record, crash after the
durable record (exactly-once recovery), transport ambiguity, connection failure before sending, fallback or model
substitution, idempotent re-runs, the exact HTTP request (headers, body, no beta header, key never written), gold
blindness of the run path, the commit gate before comparison, the frozen B′ decision rules end to end, journal
tamper detection, and the real 381-slot schedule.

    python -B test_g4_adjudicate.py
"""

import builtins
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g4_adjudicate as H  # noqa: E402

CFG = H.amended_config()
FIXTURES = H.model_facing_b()
SAMPLE = H.audit_sample()
GOLD = {g["fixture_id"]: g for g in json.loads((H.SEALED / "gold_b.json").read_text(encoding="utf-8"))["items"]}
MODEL = CFG["request"]["body_template"]["model"]
RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition)))
    print(("PASS " if condition else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def message(text=None, stop_reason="end_turn", model=MODEL, content=None, usage=None):
    blocks = content if content is not None else [{"type": "thinking", "thinking": "", "signature": "sig"},
                                                  {"type": "text", "text": text}]
    return json.dumps({"id": "msg_fake", "type": "message", "role": "assistant", "model": model, "content": blocks,
                       "stop_reason": stop_reason, "usage": usage or {"input_tokens": 10, "output_tokens": 5}}).encode()


def correct(fid):
    ref = GOLD[fid]["reference_output"]
    return ref if isinstance(ref, str) else json.dumps(ref)


class FakeProvider:
    """Scripted responses per (fixture, slot): a list consumed one per send. Items are (status, headers, body) or
    an exception instance to raise. Unscripted slots get a correct answer."""

    def __init__(self, script=None):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.calls = []
        self.current = None

    def send(self, body):
        req = json.loads(body.decode("utf-8"))
        fid = next(f for f, fx in FIXTURES.items() if H.render(fx, CFG)["user"] == req["messages"][0]["content"])
        slot = self.current_slot(fid)
        self.calls.append((fid, slot))
        queue = self.script.get((fid, slot))
        item = queue.pop(0) if queue else (200, {"request-id": "req_fake"}, message(correct(fid)))
        if isinstance(item, BaseException):
            raise item
        return item

    def current_slot(self, fid):
        return getattr(self, "slot_of", {}).get(fid, 1)


class SlotAwareRunner(H.Runner):
    """Test-only: slots 2 and 3 send byte-identical requests (fresh sessions, same prompt), so the fake provider is
    told which slot it is serving. The harness itself is unchanged."""

    def run_slot(self, fid, slot):
        if hasattr(self.provider, "slots_served"):
            self.provider.slot_of = {fid: slot}
        return super().run_slot(fid, slot)


def runner(tmp, provider, crash=None, fixtures=None):
    if isinstance(provider, FakeProvider):
        provider.slots_served = True
    return SlotAwareRunner(tmp, CFG, provider, fixtures or FIXTURES, workers=1, sleep=lambda s: None, crash=crash,
                           pacer=H.Pacer(sleep=lambda s: None))


def fresh():
    return Path(tempfile.mkdtemp(prefix="g4adj-test-"))


def outcome(r, fid, slot):
    return r.slot_outcome(r.slots()[(fid, slot)])


def run_one(fid, script, crash=None, tmp=None):
    tmp = tmp or fresh()
    p = FakeProvider({(fid, 1): script})
    r = runner(tmp, p, crash)
    try:
        r.run([(fid, 1)], 1)
        err = None
    except H.StopBatch as exc:
        err = exc
    return tmp, p, r, err


def main():
    ids = sorted(FIXTURES)
    f1, f2, f3, f4 = ids[0], ids[1], ids[2], ids[3]

    # ---- final messages bind, whatever they contain
    tmp, p, r, err = run_one(f1, [(200, {}, message(correct(f1)))])
    check("success binds", err is None and outcome(r, f1, 1) == "bound" and len(p.calls) == 1)
    tmp, p, r, err = run_one(f1, [(200, {}, message(content=[], stop_reason="refusal"))])
    rec = [x for x in r.journal.records if x["type"] == "result"][0]
    check("refusal binds (no retry)", err is None and rec["kind"] == "final_message" and rec["stop_reason"] ==
          "refusal" and len(p.calls) == 1 and rec["binding_text_chars"] == 0)
    tmp, p, r, err = run_one(f1, [(200, {}, message("not json {"))])
    check("malformed answer binds (no retry)", err is None and outcome(r, f1, 1) == "bound" and len(p.calls) == 1)
    tmp, p, r, err = run_one(f1, [(200, {}, message('{"partial": ', stop_reason="max_tokens"))])
    check("truncated answer binds (no retry)", err is None and outcome(r, f1, 1) == "bound" and len(p.calls) == 1)
    text = H.binding_text(json.loads(message(content=[{"type": "thinking", "thinking": "zzz"},
                                                      {"type": "text", "text": "A"},
                                                      {"type": "text", "text": "B"}]).decode()))
    check("binding text = concatenated text blocks only", text == "AB")

    # ---- the single permitted no-answer retry
    tmp, p, r, err = run_one(f1, [(529, {"retry-after": "3"}, b'{"type":"error"}'), (200, {}, message(correct(f1)))])
    invs = r.slots()[(f1, 1)]["invocations"]
    check("no-answer then answer: one retry, invocation 2 binds", err is None and len(p.calls) == 2 and
          invs[1]["result"]["kind"] == "no_answer" and invs[2]["result"]["kind"] == "final_message")
    tmp, p, r, err = run_one(f1, [(500, {}, b"{}"), (503, {}, b"{}")])
    check("second no-answer: disagreement, batch stops, no third call",
          err is not None and err.kind == "no_answer_twice" and len(p.calls) == 2 and
          outcome(r, f1, 1) == "no_answer_twice")
    tmp, p, r, err = run_one(f1, [(400, {}, b'{"type":"error","error":{"type":"invalid_request_error"}}')])
    check("provider rejection (400): stop, never retried", err is not None and err.kind == "request_rejected" and
          len(p.calls) == 1)

    # ---- crashes and exactly-once recovery
    def crash_at(point):
        fired = {"done": False}

        def hook(where, slot, inv):
            if where == point and not fired["done"]:
                fired["done"] = True
                raise H.SimulatedCrash(point)
        return hook

    for point, expect_calls_total, expect in (("before_intent", 1, "bound"), ("after_intent", 0, "in_doubt"),
                                              ("after_send", 1, "in_doubt"), ("after_raw", 1, "bound")):
        tmp = fresh()
        p = FakeProvider()
        r = runner(tmp, p, crash_at(point))
        try:
            r.run([(f2, 1)], 1)
        except H.SimulatedCrash:
            pass
        r2 = runner(tmp, p)                                   # the restarted process
        try:
            r2.run([(f2, 1)], 1)
            err = None
        except H.StopBatch as exc:
            err = exc
        got = outcome(r2, f2, 1)
        intents = [x for x in r2.journal.records if x["type"] == "intent"]
        recovered = any(x.get("recovered") for x in r2.journal.records if x["type"] == "result")
        ok = len(p.calls) == expect_calls_total and got == expect
        if point == "before_intent":
            ok = ok and err is None and len(intents) == 1
        elif point == "after_raw":
            ok = ok and err is None and recovered and len(intents) == 1
        else:
            ok = ok and err is not None and err.kind == "in_doubt"
        check(f"crash {point}: {expect}, provider calls {len(p.calls)}", ok)
        if point in ("after_intent", "after_send"):
            try:
                runner(tmp, p).run([(f2, 1)], 1)
                blocked = False
            except H.StopBatch as exc:
                blocked = exc.kind == "unresolved_stop"
            r3 = runner(tmp, p)
            r3.journal.append({"type": "operator_resolution", "resolves": r3.unresolved_stops()[0]["seq"],
                               "decision": "test: continue other slots; the in-doubt slot is never re-sent"})
            calls_before = len(p.calls)
            runner(tmp, p).run([(f2, 1)], 1)
            check(f"crash {point}: resume blocked until resolved; in-doubt slot never re-sent",
                  blocked and len(p.calls) == calls_before)

    tmp, p, r, err = run_one(f3, [H.InDoubt("ReadTimeout")])
    check("transport failure after send: in doubt, stop, no retry", err is not None and err.kind == "in_doubt" and
          len(p.calls) == 1 and outcome(r, f3, 1) == "in_doubt")
    tmp, p, r, err = run_one(f3, [H.NotSent("ConnectError"), (200, {}, message(correct(f3)))])
    r.journal.append({"type": "operator_resolution", "resolves": r.unresolved_stops()[0]["seq"], "decision": "test"})
    runner(tmp, p).run([(f3, 1)], 1)
    r = runner(tmp, p)
    check("connection failure before sending: stop; slot not consumed; resumes to a binding answer",
          err is not None and err.kind == "not_sent" and outcome(r, f3, 1) == "bound" and len(p.calls) == 2)

    # ---- no substitution
    tmp, p, r, err = run_one(f4, [(200, {}, message(correct(f4), model="claude-opus-5"))])
    check("different model in response: integrity stop", err is not None and err.kind == "integrity")
    tmp, p, r, err = run_one(f4, [(200, {}, message(correct(f4), usage={"iterations": [{"type": "fallback_message"}]}))])
    check("fallback reported: integrity stop", err is not None and err.kind == "integrity")

    # ---- idempotent: a finished schedule sends nothing more
    tmp = fresh()
    p = FakeProvider()
    r = runner(tmp, p)
    r.run([(f1, 1), (f2, 1)], 1)
    before = len(p.calls)
    runner(tmp, p).run([(f1, 1), (f2, 1)], 1)
    check("re-running a completed schedule contacts nobody", len(p.calls) == before == 2)

    # ---- the exact HTTP request, through the real provider class and a mock transport
    import httpx
    seen = []
    key_dir = fresh()
    key_file = key_dir / "key"
    fake_key = "sk-ant-api03-" + "x" * 95
    key_file.write_text(fake_key, encoding="ascii")

    def handler(request):
        seen.append(request)
        return httpx.Response(200, headers={"request-id": "req_mock"}, content=message(correct(f1)))
    prov = H.AnthropicProvider(CFG, key_file=key_file)
    prov._client = httpx.Client(transport=httpx.MockTransport(handler))
    tmp = fresh()
    runner(tmp, prov).run([(f1, 1)], 1)
    req = seen[0]
    body = json.loads(req.content.decode("utf-8"))
    rendered = H.render(FIXTURES[f1], CFG)
    check("request goes to the frozen endpoint with the frozen headers",
          str(req.url) == "https://api.anthropic.com/v1/messages" and req.method == "POST" and
          req.headers["anthropic-version"] == "2023-06-01" and req.headers["x-api-key"] == fake_key and
          "anthropic-beta" not in req.headers)
    check("request body is exactly the amended template",
          set(body) == {"model", "max_tokens", "system", "messages", "output_config"} and body["model"] == MODEL and
          body["max_tokens"] == 32000 and body["output_config"] == {"effort": "high"} and
          body["system"] == rendered["system"] and
          body["messages"] == [{"role": "user", "content": rendered["user"]}] and
          req.content == H.request_body(FIXTURES[f1], CFG))
    leaked = [f for f in tmp.rglob("*") if f.is_file() and fake_key.encode() in f.read_bytes()]
    check("API key never written to the run directory", not leaked)
    check("request carries no gold, rationale, sample or ledger content",
          not any(w in req.content.decode("utf-8") for w in ('"expected"', '"reference_output"', '"rationale"',
                                                               '"required_terms"', "near_miss", "research_contract",
                                                               "AUDIT_SAMPLE", "sampled")))

    # ---- blindness of the run path: gold files are never opened
    gold_names = ("gold_a.json", "gold_b.json", "reserve_gold_a.json", "reserve_gold_b.json", "authoring_ledger.json")
    real_open, real_read = builtins.open, Path.read_text
    opened = []

    def guarded_open(file, *a, **k):
        if any(str(file).endswith(n) for n in gold_names):
            opened.append(str(file))
            raise AssertionError("gold opened on the run path")
        return real_open(file, *a, **k)

    def guarded_read(self, *a, **k):
        if any(str(self).endswith(n) for n in gold_names):
            opened.append(str(self))
            raise AssertionError("gold opened on the run path")
        return real_read(self, *a, **k)
    builtins.open, Path.read_text = guarded_open, guarded_read
    try:
        tmp = fresh()
        runner(tmp, FakeProvider()).run([(f1, 1), (f2, 1)], 1)
    finally:
        builtins.open, Path.read_text = real_open, real_read
    check("run path never opens gold, rationales or the ledger", not opened)

    # ---- sealing before comparison, and the frozen B′ decision rules end to end
    repo = fresh()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    run_dir = repo / "run"
    sampled = [i for i in SAMPLE][:2]
    others = [i for i in ids if i not in SAMPLE][:4]
    subset = {i: FIXTURES[i] for i in sampled + others}
    wrong = message('{"wrong": true}')
    script = {(others[0], 1): [(200, {}, wrong)],                      # non-sampled disagree -> slots 2, 3
              (others[1], 1): [(200, {}, wrong)],
              (sampled[0], 2): [(200, {}, wrong)]}                     # sampled agreed, a further disagrees
    p = FakeProvider(script)
    r = runner(run_dir, p, fixtures=subset)
    schedule1 = H.phase1_schedule(subset, sampled)
    r.run(schedule1, 1)
    answers_path = run_dir / "answers_phase1.json"
    answers_path.write_text(json.dumps(H.answers(r, schedule1, 1), indent=1) + "\n", encoding="utf-8")
    try:
        H.score(r, answers_path, repo=repo)
        gate = False
    except H.StopBatch as exc:
        gate = exc.kind == "not_sealed"
    check("comparison with gold refused until the answers are committed", gate)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "seal answers"], check=True)
    s1 = H.score(r, answers_path, repo=repo)
    by = {(x["fixture_id"], x["slot"]): x["agree"] for x in s1["slots"]}
    check("correct answers agree and wrong answers disagree under the frozen validators",
          by[(others[2], 1)] is True and by[(others[0], 1)] is False and by[(sampled[0], 2)] is False and
          by[(sampled[1], 3)] is True)
    schedule2 = H.phase2_schedule(s1, sampled)
    check("phase 2 = slots 2 and 3 for non-sampled first-adjudicator disagreements only",
          schedule2 == [(others[0], 2), (others[0], 3), (others[1], 2), (others[1], 3)])
    p.script[(others[1], 2)] = [(200, {}, wrong)]
    r.run(schedule2, 2)
    a2 = run_dir / "answers_phase2.json"
    a2.write_text(json.dumps(H.answers(r, schedule2, 2), indent=1) + "\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "seal phase 2"], check=True)
    s2 = H.score(r, a2, repo=repo)
    d = H.decide(s1["slots"] + s2["slots"], subset, sampled)
    check("decisions follow the frozen B′ rules",
          d[others[2]]["decision"] == "keep" and d[others[0]]["decision"] == "keep" and
          d[others[0]]["flag"] is not None and d[others[1]]["decision"] == "operator" and
          d[sampled[0]]["decision"] == "operator" and d[sampled[1]]["decision"] == "keep",
          json.dumps({k: v["decision"] for k, v in d.items()}))
    raw_file = next(run_dir.joinpath("raw").glob("*.body"))
    raw_file.write_bytes(raw_file.read_bytes() + b" ")
    try:
        H.score(r, answers_path, repo=repo)
        tamper = False
    except H.StopBatch as exc:
        tamper = exc.kind in ("integrity", "not_sealed")
    check("a changed raw response is caught at scoring", tamper)

    # ---- journal tamper, and the real schedule
    tmp = fresh()
    r = runner(tmp, FakeProvider())
    r.run([(f1, 1)], 1)
    lines = (tmp / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace('"slot":1', '"slot":2')
    (tmp / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        H.Journal(tmp / "journal.jsonl")
        caught = False
    except H.StopBatch:
        caught = True
    check("an edited journal line breaks the hash chain", caught)
    full = H.phase1_schedule(FIXTURES, SAMPLE)
    extra = {}
    for fid, slot in full:
        if slot > 1:
            extra.setdefault(fid, []).append(slot)
    check("real schedule: 305 first-adjudicator slots; each of the 38 sampled fixtures bound to slots 2 and 3",
          len(full) == 381 and sum(1 for _, s in full if s == 1) == 305 and len(set(f for f, s in full if s == 1)) == 305
          and sorted(extra) == SAMPLE and all(v == [2, 3] for v in extra.values()) and len(extra) == 38)

    # ---- fix rounds: the overlay replaces exactly the fixed fixtures, bound to their recorded digests
    fixes_dir = HERE / "fixes" / "round1_bmain"
    if fixes_dir.exists():
        fixed = H.fixed_fixtures(fixes_dir)
        record = {r["fixture_id"]: r for r in json.loads((fixes_dir / "FIX_RECORD.json").read_text(encoding="utf-8"))["fixes"]}
        overlay = H.model_facing_b(fixes_dir)
        check("fix overlay: 14 fixed fixtures replace exactly their sealed versions",
              len(fixed) == 14 and all(overlay[f] == fixed[f] for f in fixed) and
              all(overlay[f] == FIXTURES[f] for f in FIXTURES if f not in fixed))
        p6 = "B4-RSRCH-R1-06"
        body = H.request_body(fixed[p6], CFG).decode("utf-8")
        check("fix overlay: the request carries the fixed text and not the sealed one",
              "covers the town routes." in body and "covers the town routes only" not in body)
        tmpfix = fresh()
        for n in ("corpus_fixed.json", "gold_fixed.json", "ledger_fixed.json", "FIX_RECORD.json"):
            shutil.copy(fixes_dir / n, tmpfix / n)
        doc = json.loads((tmpfix / "corpus_fixed.json").read_text(encoding="utf-8"))
        doc["fixtures"][0]["title"] += " (tampered)"
        (tmpfix / "corpus_fixed.json").write_text(json.dumps(doc), encoding="utf-8")
        try:
            H.fixed_fixtures(tmpfix)
            refused = False
        except H.StopBatch as exc:
            refused = exc.kind == "binding"
        check("fix overlay: a fixed fixture that differs from its recorded digest is refused", refused)
        gold_fixed = H.gold_path_overlay(fixes_dir)
        sy1 = "B4-SYNTH-R2-14"
        from g_route3_semantics import validate_fixture_output
        new_ok = validate_fixture_output(fixed[sy1], gold_fixed[sy1], json.dumps(gold_fixed[sy1]["reference_output"]))
        old_ok = validate_fixture_output(fixed[sy1], gold_fixed[sy1], json.dumps(GOLD[sy1]["reference_output"]))
        check("fix overlay: scoring uses the fixed gold (fixed reference agrees; sealed-role reference does not)",
              new_ok.get("hard_gate_pass") and not old_ok.get("hard_gate_pass") and
              gold_fixed[sy1] != GOLD[sy1] and record[sy1]["fixed_sha256"]["gold"] == H.sha256(H.canonical(gold_fixed[sy1])))
        scope = sorted(fixed)
        sched = H.phase1_schedule(scope, [f for f in SAMPLE if f in scope])
        check("fix round schedule: adjudicator 1 for each of the 14 fixed fixtures (none is sampled)",
              sched == [(f, 1) for f in scope] and not set(scope) & set(SAMPLE))

    # ---- A′ batch: three adjudicators for every fixture, kept only if all three agree
    A = H.model_facing_a()
    GOLD_A = {g["fixture_id"]: g for g in json.loads((H.SEALED / "gold_a.json").read_text(encoding="utf-8"))["items"]}
    sa = H.a_schedule(A)
    check("A′ schedule: the 80 A′ main fixtures, slots 1, 2 and 3 each (240), nothing else",
          len(A) == 80 and len(sa) == 240 and sorted({f for f, _ in sa}) == sorted(A) and
          all(sorted(s for f2, s in sa if f2 == f) == [1, 2, 3] for f in A) and not set(A) & set(FIXTURES))
    d = H.decide_a([{"fixture_id": "X", "slot": s, "agree": True} for s in (1, 2, 3)] +
                   [{"fixture_id": "Y", "slot": 1, "agree": True}, {"fixture_id": "Y", "slot": 2, "agree": False},
                    {"fixture_id": "Y", "slot": 3, "agree": True}] +
                   [{"fixture_id": "Z", "slot": 1, "agree": True}, {"fixture_id": "Z", "slot": 2, "agree": None},
                    {"fixture_id": "Z", "slot": 3, "agree": True}], ["X", "Y", "Z"])
    check("A′ decision rule: all three agree -> keep; any disagreement -> operator; no verdict -> incomplete",
          d["X"]["decision"] == "keep" and d["Y"]["decision"] == "operator" and d["Z"]["decision"] == "incomplete")
    repo = fresh()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    ids_a = sorted(f for f in A if A[f]["task_class"] != "ordinary_conversation")[:3]   # JSON-answer classes
    subset_a = {i: A[i] for i in ids_a}
    ref_a = lambda fid: GOLD_A[fid]["reference_output"] if isinstance(GOLD_A[fid]["reference_output"], str) \
        else json.dumps(GOLD_A[fid]["reference_output"])

    class FakeA(FakeProvider):
        def send(self, body):
            req = json.loads(body.decode("utf-8"))
            fid = next(f for f, fx in subset_a.items() if H.render(fx, CFG)["user"] == req["messages"][0]["content"])
            slot = self.current_slot(fid)
            self.calls.append((fid, slot))
            if (fid, slot) == (ids_a[1], 2):
                return 200, {}, message("```json\n" + ref_a(fid) + "\n```")
            return 200, {}, message(ref_a(fid))
    pa = FakeA()
    ra = runner(repo / "run", pa, fixtures=subset_a)
    sched_a = H.a_schedule(subset_a)
    ra.run(sched_a, 1)
    ap = repo / "run" / "answers_phase1.json"
    ap.write_text(json.dumps(H.answers(ra, sched_a, 1), indent=1) + "\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "seal A answers"], check=True)
    sc = H.score(ra, ap, repo=repo, gold_path=H.SEALED / "gold_a.json")
    da = H.decide_a(sc["slots"], subset_a)
    check("A′ end to end: 9 sessions; a fenced answer is a disagreement and sends its fixture to the operator",
          len(pa.calls) == 9 and da[ids_a[0]]["decision"] == "keep" and da[ids_a[1]]["decision"] == "operator" and
          da[ids_a[2]]["decision"] == "keep" and
          [r for r in sc["slots"] if r["agree"] is False][0]["operational_reasons"] == ["malformed_json"])

    # ---- operator reclassification of a provider rejection as a no-answer (the frozen single retry)
    billing = (400, {"request-id": "req_x"}, b'{"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low"}}')
    for second, expect in (((200, {}, message(correct(f2))), "bound"), ((503, {}, b"{}"), "no_answer_twice")):
        tmp = fresh()
        p = FakeProvider({(f2, 1): [billing, second]})
        r = runner(tmp, p)
        try:
            r.run([(f2, 1)], 1)
        except H.StopBatch:
            pass
        blocked_before = outcome(r, f2, 1) == "stopped"
        r.journal.append({"type": "operator_resolution", "resolves": r.unresolved_stops()[0]["seq"], "decision": "test"})
        r.reclassify(f2, 1, 1, "test: billing rejection counts as a no-answer")
        try:
            runner(tmp, p).run([(f2, 1)], 1)
            err = None
        except H.StopBatch as exc:
            err = exc
        r = runner(tmp, p)
        inv1 = r.slots()[(f2, 1)]["invocations"][1]["result"]
        raw_rec = [x for x in r.journal.records if x["type"] == "result" and x["invocation"] == 1][0]
        check(f"reclassified rejection: one retry only, then {expect}",
              blocked_before and outcome(r, f2, 1) == expect and len(p.calls) == 2 and inv1["kind"] == "no_answer" and
              inv1["recorded_kind"] == "request_rejected" and raw_rec["kind"] == "request_rejected" and
              (err is None) == (expect == "bound"))
    try:
        r.reclassify(f2, 1, 2, "test")
        refused = False
    except H.StopBatch:
        refused = True
    check("reclassification is refused for anything but an unreclassified provider rejection", refused)

    failed = [n for n, ok in RESULTS if not ok]
    print(f"{len(RESULTS) - len(failed)} of {len(RESULTS)} offline harness checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
