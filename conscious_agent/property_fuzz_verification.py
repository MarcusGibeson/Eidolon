from __future__ import annotations
"""v1355 bounded deterministic property/fuzz verification.

The engine deliberately supports a small built-in vocabulary of pure generators and
oracles.  It never evaluates generated source or invokes tools/providers.
"""
import hashlib, json, random, re, time
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1355.8"
DENIED = {
    "test_execution_authorized": False,
    "source_mutation_authorized": False,
    "provider_contact_authorized": False,
    "network_authorized": False,
    "release_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}
ORACLES = {"identifier_validity", "json_roundtrip", "bounded_integer", "lifecycle_transition", "recovery_idempotence", "nonzero_integer"}
GENERATORS = {"identifier", "json_value", "bounded_integer", "lifecycle_transition"}
_ALLOWED_TRANSITIONS = {"new": {"running"}, "running": {"paused", "complete", "failed"}, "paused": {"running", "failed"}, "complete": set(), "failed": set()}

def _d(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()

def _root(runtime_root=None) -> Path:
    p = Path(runtime_root or ".").resolve() / "phase6_property_fuzz"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _safe_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", value))

def _generate(generator: str, rng: random.Random, index: int) -> object:
    if generator == "identifier":
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        n = rng.randint(1, 24)
        return "".join(rng.choice(alphabet) for _ in range(n))
    if generator == "json_value":
        choice = rng.randrange(5)
        if choice == 0: return rng.randint(-10000, 10000)
        if choice == 1: return bool(rng.randrange(2))
        if choice == 2: return None
        if choice == 3: return [rng.randint(-20, 20) for _ in range(rng.randrange(6))]
        return {f"k{j}": rng.randint(-20, 20) for j in range(rng.randrange(5))}
    if generator == "bounded_integer":
        # Include zero deterministically so a seeded failing non-zero property has a
        # stable minimal counterexample independent of RNG implementation details.
        if index == 0: return 0
        return rng.randint(-1000, 1000)
    if generator == "lifecycle_transition":
        states = tuple(_ALLOWED_TRANSITIONS)
        src = states[rng.randrange(len(states))]
        candidates = tuple(sorted(_ALLOWED_TRANSITIONS[src]))
        dst = candidates[rng.randrange(len(candidates))] if candidates else src
        return [src, dst]
    raise ValueError("unsupported_generator")

def _oracle(name: str, value: object) -> bool:
    if name == "identifier_validity":
        return isinstance(value, str) and _safe_id(value)
    if name == "json_roundtrip":
        try: return json.loads(json.dumps(value, sort_keys=True)) == value
        except Exception: return False
    if name == "bounded_integer":
        return isinstance(value, int) and not isinstance(value, bool) and -1000 <= value <= 1000
    if name == "nonzero_integer":
        return isinstance(value, int) and not isinstance(value, bool) and value != 0
    if name == "lifecycle_transition":
        return isinstance(value, list) and len(value) == 2 and (value[1] in _ALLOWED_TRANSITIONS.get(str(value[0]), set()) or (str(value[0]) in {'complete','failed'} and value[0] == value[1]))
    if name == "recovery_idempotence":
        # Terminal recovery is represented by repeating the same terminal value.
        return isinstance(value, list) and len(value) == 2 and (value[0] not in {"complete", "failed"} or value[0] == value[1])
    return False

def _shrink_metadata(value: object) -> dict[str, Any]:
    if isinstance(value, int) and not isinstance(value, bool):
        return {"strategy": "integer_toward_zero", "steps": abs(value).bit_length(), "minimal_digest": _d(0)}
    if isinstance(value, str):
        return {"strategy": "string_prefix", "steps": max(0, len(value) - 1), "minimal_digest": _d(value[:1])}
    if isinstance(value, (list, dict)):
        return {"strategy": "structural_reduction", "steps": len(value), "minimal_digest": _d([] if isinstance(value, list) else {})}
    return {"strategy": "none", "steps": 0, "minimal_digest": _d(value)}

def build_property_fuzz_report(*, source_manifest_digest: str, properties: Sequence[Mapping[str, Any]], seed: int = 1355, max_cases: int = 256, max_seconds: float = 3.0, runtime_root=None) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}", str(source_manifest_digest or "")):
        return {"ok": False, "status": "property_fuzz_source_lineage_required", "action_executed": False, **DENIED}
    try:
        seed = int(seed); max_cases = int(max_cases); max_seconds = float(max_seconds)
    except Exception:
        return {"ok": False, "status": "property_fuzz_budget_invalid", "action_executed": False, **DENIED}
    if not properties or len(properties) > 64 or max_cases < 1 or max_cases > 1000 or max_seconds <= 0 or max_seconds > 10:
        return {"ok": False, "status": "property_fuzz_budget_invalid", "action_executed": False, **DENIED}
    normalized=[]; seen=set(); total_requested=0
    for raw in properties:
        pid=str(raw.get("property_id") or ""); oracle=str(raw.get("oracle") or ""); generator=str(raw.get("generator") or ""); evidence=str(raw.get("evidence_digest") or ""); cases=int(raw.get("cases") or 0)
        if not _safe_id(pid) or pid in seen or oracle not in ORACLES or generator not in GENERATORS or not re.fullmatch(r"[a-f0-9]{64}", evidence) or cases < 1:
            return {"ok": False, "status": "property_fuzz_definition_invalid", "action_executed": False, **DENIED}
        if oracle == "recovery_idempotence" and generator != "lifecycle_transition":
            return {"ok": False, "status": "property_fuzz_definition_invalid", "action_executed": False, **DENIED}
        seen.add(pid); total_requested += cases
        normalized.append((pid,oracle,generator,evidence,cases))
    if total_requested > max_cases:
        return {"ok": False, "status": "property_fuzz_case_budget_exceeded", "action_executed": False, **DENIED}
    material={"contract":CONTRACT_VERSION,"source":source_manifest_digest,"seed":seed,"max_cases":max_cases,"properties":[{"id":_d(p),"oracle":o,"generator":g,"evidence":e,"cases":c} for p,o,g,e,c in normalized]}
    report_id="pfz_"+_d(material)[:24]; path=_root(runtime_root)/(report_id+".json")
    if path.is_file():
        loaded=load_property_fuzz_report(report_id,runtime_root=runtime_root)
        if loaded: return {"ok": loaded.get("all_properties_passed") is True, "status": "property_fuzz_report_already_exists", "property_fuzz_report": loaded, "action_executed": False, **DENIED}
    start=time.monotonic(); rows=[]; total_run=0; failed=0
    for pindex,(pid,oracle,generator,evidence,cases) in enumerate(normalized):
        rng=random.Random(seed + pindex * 1000003); failure_digests=[]; case_digests=[]; shrink=[]; executed=0
        for idx in range(cases):
            if time.monotonic()-start > max_seconds: break
            value=_generate(generator,rng,idx); executed += 1; total_run += 1
            case_digests.append(_d({"property":_d(pid),"index":idx,"value":_d(value)}))
            if not _oracle(oracle,value):
                failure_digests.append(_d({"property":_d(pid),"index":idx,"value":_d(value),"oracle":oracle})); shrink.append(_shrink_metadata(value))
        timed_out=executed < cases; passed=not failure_digests and not timed_out
        if not passed: failed += 1
        rows.append({"property_id_digest":_d(pid),"oracle":oracle,"generator":generator,"evidence_digest":evidence,"requested_cases":cases,"executed_cases":executed,"case_digest":_d(case_digests),"failure_count":len(failure_digests),"failure_digests":failure_digests[:16],"shrink_metadata":shrink[:16],"timed_out":timed_out,"passed":passed})
    rec={"contract_version":CONTRACT_VERSION,"property_fuzz_report_id":report_id,"source_manifest_digest":source_manifest_digest,"seed":seed,"property_count":len(rows),"case_count":total_run,"failed_property_count":failed,"properties":rows,"all_properties_passed":failed==0,"bounded":True,"deterministic":True,"generated_code":False,"payloads_persisted":False,"content_free":True,"action_executed":False,**DENIED}
    rec["record_digest"]=_d(rec); path.write_text(json.dumps(rec,sort_keys=True),encoding="utf-8")
    return {"ok": failed==0, "status": "property_fuzz_passed" if failed==0 else "property_fuzz_counterexample_found", "property_fuzz_report":rec, "action_executed":False, **DENIED}

def load_property_fuzz_report(report_id: str, *, runtime_root=None) -> dict[str, Any]:
    if not re.fullmatch(r"pfz_[a-f0-9]{24}",str(report_id or "")): return {}
    p=_root(runtime_root)/(report_id+".json")
    if not p.is_file(): return {}
    try: rec=json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}
    claimed=rec.pop("record_digest",None)
    if claimed != _d(rec): return {}
    rec["record_digest"]=claimed; return rec

def process_property_fuzz_control(text: str, *, project_state=None, runtime_root=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show property fuzz verification","inspect property fuzz verification","show fuzz tests"}: return {"active":False}
    rid=str((project_state or {}).get("property_fuzz_report_id") or ""); rec=load_property_fuzz_report(rid,runtime_root=runtime_root) if rid else {}
    return {"active":True,"ok":bool(rec),"status":"property_fuzz_report_found" if rec else "property_fuzz_report_missing","property_fuzz_report":rec,"action_executed":False,**DENIED}
