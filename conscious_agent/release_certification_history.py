from __future__ import annotations

"""Read-only certification authority-history reconstruction and reconciliation."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

try:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_certification_evidence import certification_directory, _promotion_context
    from release_certification_plan import _current_certification_state, _plan_binding
    from release_promotion_preview import current_promotion_state_private
except ImportError:
    from release_candidate_identity import atomic_json, digest_payload, read_json, runtime_data_root, utc_now
    from release_certification_evidence import certification_directory, _promotion_context
    from release_certification_plan import _current_certification_state, _plan_binding
    from release_promotion_preview import current_promotion_state_private

CERTIFICATION_HISTORY_CONTRACT_VERSION = "1"
HISTORY_PREVIEW_SCHEMA = "eidolon-certification-authority-history-preview-v1"


def _counts(rows: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    found: Counter[str] = Counter()
    for row in rows or []:
        found[str(row.get("kind") or "unknown")] += max(1, int(row.get("count") or 1))
    return [{"kind": key, "count": found[key]} for key in sorted(found)]


def _public(row: Mapping[str, Any] | None) -> dict[str, Any]:
    record = dict(row or {})
    findings = _counts(record.get("findings") if isinstance(record.get("findings"), list) else [])
    return {
        "ok": bool(record.get("ok")) and not findings,
        "status": str(record.get("status") or "certification_history_not_reconciled"),
        "contract_version": CERTIFICATION_HISTORY_CONTRACT_VERSION,
        "preview_id": str(record.get("preview_id") or ""),
        "generation": int(record.get("generation") or 0),
        "scope": str(record.get("scope") or "all"),
        "candidate_id": str(record.get("candidate_id") or ""),
        "archive_sha256": str(record.get("archive_sha256") or ""),
        "target_project_id": str(record.get("target_project_id") or ""),
        "installed_receipt_sha256": str(record.get("installed_receipt_sha256") or ""),
        "promotion_receipt_sha256": str(record.get("promotion_receipt_sha256") or ""),
        "authority_generation": int(record.get("authority_generation") or 0),
        "authority_state_sha256": str(record.get("authority_state_sha256") or ""),
        "history_sha256": str(record.get("history_sha256") or ""),
        "record_inventory_sha256": str(record.get("record_inventory_sha256") or ""),
        "record_count": int(record.get("record_count") or 0),
        "evidence_count": int(record.get("evidence_count") or 0),
        "plan_count": int(record.get("plan_count") or 0),
        "transaction_count": int(record.get("transaction_count") or 0),
        "receipt_count": int(record.get("receipt_count") or 0),
        "state_count": int(record.get("state_count") or 0),
        "event_count": int(record.get("event_count") or 0),
        "replacement_count": int(record.get("replacement_count") or 0),
        "finding_count": sum(int(x["count"]) for x in findings),
        "findings": findings,
        "history_integrity": "coherent" if not findings else "contradictory_or_uncertain",
        "read_only": True,
        "preview_first": True,
        "history_rewritten": False,
        "paths_suppressed": True,
        "records_external": True,
        "content_free": True,
        "ordinary_conversation_affected": False,
    }


def _digest_valid(row: Mapping[str, Any]) -> bool:
    for field in ("record_sha256", "receipt_sha256", "state_sha256"):
        if field in row:
            material = dict(row); expected = str(material.pop(field, ""))
            return bool(expected) and expected == digest_payload(material)
    return True


def _inventory(runtime_root: str | Path | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = certification_directory(runtime_root)
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    directories = {
        "evidence": "evidence", "plans": "plan", "transactions": "transaction",
        "receipts": "receipt", "states": "state", "replacement_receipts": "replacement",
        "recertification_previews": "recertification", "readiness": "readiness",
    }
    for dirname, kind in directories.items():
        folder = base / dirname
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.json"), key=lambda p: p.name):
            data = read_json(path)
            if not data:
                findings.append({"kind": f"{kind}_record_unreadable"}); continue
            digest = digest_payload(data)
            row = {
                "kind": kind, "name_sha256": digest_payload({"name": path.name}),
                "schema": str(data.get("schema") or ""), "digest": digest,
                "generation": int(data.get("generation") or data.get("plan_generation") or 0),
                "scope": str(data.get("scope") or data.get("certification_scope") or ""),
                "candidate_id": str(data.get("candidate_id") or ""),
                "target_project_id": str(data.get("target_project_id") or ""),
                "promotion_receipt_sha256": str(data.get("promotion_receipt_sha256") or ""),
                "id": str(data.get("evidence_id") or data.get("plan_id") or data.get("certification_transaction_id") or data.get("state_id") or data.get("replacement_id") or ""),
                "data": data,
            }
            rows.append(row)
            if not _digest_valid(data): findings.append({"kind": f"{kind}_digest_link_broken"})
            if kind == "plan" and str(data.get("plan_binding_sha256") or "") != _plan_binding(data):
                findings.append({"kind": "plan_binding_broken"})
    events = base / "events"
    if events.is_dir():
        for path in sorted(events.glob("*.jsonl"), key=lambda p: p.name):
            seqs=[]; tx=""; identity=""
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip(): continue
                    data=json.loads(line); seqs.append(int(data.get("sequence") or 0))
                    tx0=str(data.get("certification_transaction_id") or ""); id0=str(data.get("certification_transaction_identity_sha256") or "")
                    if tx and tx0 != tx: findings.append({"kind":"cross_transaction_event_link"})
                    if identity and id0 != identity: findings.append({"kind":"event_identity_link_broken"})
                    tx=tx or tx0; identity=identity or id0
                    rows.append({"kind":"event","name_sha256":digest_payload({"name":path.name,"sequence":seqs[-1]}),"schema":str(data.get("schema") or ""),"digest":digest_payload(data),"generation":seqs[-1],"scope":str(data.get("scope") or ""),"candidate_id":"","target_project_id":"","promotion_receipt_sha256":"","id":tx,"data":data})
            except Exception:
                findings.append({"kind":"event_log_unreadable"}); continue
            if seqs and sorted(seqs) != list(range(1, max(seqs)+1)): findings.append({"kind":"event_sequence_gap_or_duplicate"})
    return rows, findings


def _generation_findings(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    gens=[int(r["generation"]) for r in rows if r["kind"]==kind and int(r["generation"])>0]
    out=[]
    if len(gens) != len(set(gens)): out.append({"kind":f"duplicate_{kind}_generation"})
    if gens and sorted(set(gens)) != list(range(1, max(gens)+1)): out.append({"kind":f"missing_{kind}_generation"})
    return out


def create_certification_history_reconciliation_preview(scope: str = "all", *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    context, findings = _promotion_context(runtime_root)
    rows, scan_findings = _inventory(runtime_root); findings.extend(scan_findings)
    if scope not in {"all", "general_release", "native_windows", "provider_ollama", "model_specific"}:
        findings.append({"kind":"unsupported_history_scope"})
    for kind in ("evidence","plan","transaction","state","replacement"):
        findings.extend(_generation_findings(rows, kind))
    by_kind=defaultdict(list)
    for row in rows: by_kind[row["kind"]].append(row)
    states=sorted(by_kind["state"], key=lambda x:int(x["generation"]))
    digests={str(r["data"].get("state_sha256") or "") for r in states}
    children=defaultdict(list)
    for r in states:
        d=r["data"]; prev=str(d.get("previous_state_sha256") or "")
        if int(d.get("generation") or 0)>1 and prev not in digests: findings.append({"kind":"authority_state_previous_digest_missing"})
        if prev: children[prev].append(str(d.get("state_sha256") or ""))
    if any(len(v)>1 for v in children.values()): findings.append({"kind":"authority_history_fork"})
    txids={str(r["data"].get("certification_transaction_id") or "") for r in by_kind["transaction"]}
    receipt_tx={str(r["data"].get("certification_transaction_id") or "") for r in by_kind["receipt"]}
    event_tx={str(r["data"].get("certification_transaction_id") or "") for r in by_kind["event"]}
    if receipt_tx-txids: findings.append({"kind":"orphan_certification_receipt","count":len(receipt_tx-txids)})
    if event_tx-txids: findings.append({"kind":"orphan_certification_event","count":len(event_tx-txids)})
    for tx in by_kind["transaction"]:
        d=tx["data"]
        if str(d.get("certification_receipt_sha256") or "") and str(d.get("certification_transaction_id") or "") not in receipt_tx: findings.append({"kind":"transaction_receipt_missing"})
    all_scopes={r["scope"] for r in rows if r["scope"]}
    for r in rows:
        d=r["data"]
        if r["candidate_id"] and r["candidate_id"] != context.get("candidate_id"): findings.append({"kind":"cross_candidate_history_link"})
        if r["target_project_id"] and r["target_project_id"] != context.get("target_project_id"): findings.append({"kind":"cross_project_history_link"})
        if r["promotion_receipt_sha256"] and r["promotion_receipt_sha256"] != context.get("promotion_receipt_sha256"): findings.append({"kind":"cross_promotion_history_link"})
        if scope != "all" and r["scope"] and r["scope"] != scope and r["kind"] in {"receipt","state","transaction"}: findings.append({"kind":"cross_scope_history_link"})
        if d.get("decision") == "certified" and str(d.get("state") or "") in {"certification_declined","insufficient_evidence"}: findings.append({"kind":"impossible_certification_transition"})
    pointer, authority=_current_certification_state(runtime_root)
    if authority and pointer:
        for field in ("state_id","generation","state_sha256","state"):
            if str(pointer.get(field) or "") != str(authority.get(field) or ""): findings.append({"kind":f"active_authority_pointer_{field}_mismatch"})
    _, promotion_state=current_promotion_state_private(runtime_root)
    if authority and promotion_state:
        certified=set(authority.get("certified_scopes") or [])
        promoted=set(promotion_state.get("certified_scopes") or [])
        if certified != promoted: findings.append({"kind":"promotion_authority_descendant_scope_mismatch"})
        if certified and str(promotion_state.get("certification_receipt_sha256") or "") not in set(dict(authority.get("scope_receipts") or {}).values()): findings.append({"kind":"stale_promotion_authority_descendant"})
    private_inventory=[{k:v for k,v in r.items() if k!="data"} for r in rows]
    inventory_sha=digest_payload(private_inventory)
    history_sha=digest_payload({"context":context,"authority":authority,"inventory":private_inventory})
    directory=certification_directory(runtime_root); ptr=read_json(directory/"active_history_preview.json"); generation=int(ptr.get("generation") or 0)+1
    record={
        "schema":HISTORY_PREVIEW_SCHEMA,"preview_id":f"cert-history-{generation}-{secrets.token_hex(8)}","generation":generation,
        "created_at":utc_now(),"scope":scope,"runtime_root_sha256":digest_payload({"runtime_root":str(runtime_data_root(runtime_root).resolve())}),
        **{k:context.get(k) for k in ("candidate_id","archive_sha256","target_project_id","installed_receipt_sha256","promotion_receipt_sha256")},
        "authority_generation":int(authority.get("generation") or 0),"authority_state_sha256":str(authority.get("state_sha256") or ""),
        "record_inventory":private_inventory,"record_inventory_sha256":inventory_sha,"history_sha256":history_sha,
        "record_count":len(rows),"evidence_count":len(by_kind["evidence"]),"plan_count":len(by_kind["plan"]),"transaction_count":len(by_kind["transaction"]),"receipt_count":len(by_kind["receipt"]),"state_count":len(by_kind["state"]),"event_count":len(by_kind["event"]),"replacement_count":len(by_kind["replacement"]),
        "findings":findings,"ok":not findings,"status":"certification_history_coherent" if not findings else "certification_history_contradictory_or_uncertain",
    }
    record["preview_binding_sha256"]=digest_payload({k:v for k,v in record.items() if k not in {"created_at","findings","ok","status","record_inventory"}})
    record["record_sha256"]=digest_payload(record)
    atomic_json(directory/"history_previews"/f"{record['preview_id']}.json",record)
    atomic_json(directory/"active_history_preview.json",{"schema":HISTORY_PREVIEW_SCHEMA,"preview_id":record["preview_id"],"generation":generation,"preview_binding_sha256":record["preview_binding_sha256"],"record_sha256":record["record_sha256"],"content_free":True})
    return _public(record)


def certification_history_status(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    directory=certification_directory(runtime_root); pointer=read_json(directory/"active_history_preview.json")
    pid=str(pointer.get("preview_id") or ""); record=read_json(directory/"history_previews"/f"{pid}.json") if pid else {}
    if not record: return _public({"ok":True,"status":"certification_history_not_reconciled"})
    findings=[]; material=dict(record); expected=str(material.pop("record_sha256", ""))
    if not expected or expected != digest_payload(material): findings.append({"kind":"history_preview_record_digest_mismatch"})
    for field in ("preview_id","generation","preview_binding_sha256","record_sha256"):
        if str(pointer.get(field) or "") != str(record.get(field) or ""): findings.append({"kind":f"history_preview_pointer_{field}_mismatch"})
    rows, scan_findings = _inventory(runtime_root); findings.extend(scan_findings)
    private_inventory=[{k:v for k,v in r.items() if k!="data"} for r in rows]
    if digest_payload(private_inventory) != str(record.get("record_inventory_sha256") or ""):
        findings.append({"kind":"authority_history_record_inventory_drift"})
    context, context_findings = _promotion_context(runtime_root); findings.extend(context_findings)
    for field in ("candidate_id","archive_sha256","target_project_id","installed_receipt_sha256","promotion_receipt_sha256"):
        if str(record.get(field) or "") != str(context.get(field) or ""):
            findings.append({"kind":f"authority_history_{field}_drift"})
    _, authority = _current_certification_state(runtime_root)
    if int(record.get("authority_generation") or 0) != int(authority.get("generation") or 0): findings.append({"kind":"authority_history_generation_drift"})
    if str(record.get("authority_state_sha256") or "") != str(authority.get("state_sha256") or ""): findings.append({"kind":"authority_history_state_drift"})
    current=dict(record); current["findings"]=list(record.get("findings") or [])+findings; current["ok"]=not current["findings"]
    current["status"]="certification_history_coherent" if current["ok"] else "certification_history_stale_or_contradictory"
    return _public(current)
