from __future__ import annotations
"""v1193.0-v1193.2 verifier ownership and historical-debt foundations."""
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_VERSION = "v1193.2"
ALLOWED_OWNERS = {"conversation", "cognition", "planning", "campaign", "runtime", "release", "privacy", "platform"}
ALLOWED_CLASSES = {"current_regression", "retained_checkpoint", "historical_debt"}
ALLOWED_SEVERITIES = {"low", "medium", "high"}
ALLOWED_PROFILES = {"focused", "quick", "full"}
PRIVATE_KEYS = {"prompt","conversation","memory","secret","raw_source","patch","stdout","stderr","provider_payload","private_reasoning","content","text"}

def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()

def _is_digest(value: object) -> bool:
    token=str(value or ""); return len(token)==64 and all(c in "0123456789abcdef" for c in token)

def create_verifier_record(*, verifier_id:str, owner:str, classification:str, suite_path:str,
                           source_version:str, fixture_group:str, expected_checks:int,
                           budget_seconds:int, profile_membership:Sequence[str],
                           inherited_from:str="", debt_severity:str="low") -> dict[str,Any]:
    row={"verifier_id":str(verifier_id),"owner":str(owner),"classification":str(classification),
         "suite_path":str(suite_path),"source_version":str(source_version),"fixture_group":str(fixture_group),
         "expected_checks":int(expected_checks),"budget_seconds":int(budget_seconds),
         "profile_membership":sorted({str(x) for x in profile_membership}),"inherited_from":str(inherited_from),
         "debt_severity":str(debt_severity),"authority_state":"separate_not_granted"}
    row["record_digest"]=_digest(row); return row

def validate_verifier_records(records:Sequence[Mapping[str,Any]], *, max_records:int=128)->list[str]:
    errors=[]; rows=[dict(r) for r in records]; ids=[]; paths=[]
    if not rows: errors.append("empty_registry")
    if len(rows)>max_records: errors.append("oversized_registry")
    for row in rows:
        lower={str(k).lower() for k in row}
        if lower & PRIVATE_KEYS: errors.append("private_field")
        ids.append(str(row.get("verifier_id") or "")); paths.append(str(row.get("suite_path") or ""))
        if row.get("owner") not in ALLOWED_OWNERS: errors.append("invalid_owner")
        if row.get("classification") not in ALLOWED_CLASSES: errors.append("invalid_classification")
        if row.get("debt_severity") not in ALLOWED_SEVERITIES: errors.append("invalid_severity")
        if not str(row.get("suite_path") or "").startswith("tools/"): errors.append("invalid_suite_path")
        if int(row.get("expected_checks",-1))<0: errors.append("invalid_expected_checks")
        if not 1 <= int(row.get("budget_seconds",0)) <= 1800: errors.append("invalid_budget")
        profiles=set(row.get("profile_membership") or [])
        if not profiles or not profiles.issubset(ALLOWED_PROFILES): errors.append("invalid_profile_membership")
        classification=row.get("classification")
        if classification=="historical_debt" and not row.get("inherited_from"): errors.append("missing_debt_origin")
        if classification!="historical_debt" and row.get("debt_severity")!="low": errors.append("current_suite_marked_debt")
        if row.get("authority_state")!="separate_not_granted": errors.append("authority_expansion")
        candidate=dict(row); claimed=candidate.pop("record_digest","")
        if not _is_digest(claimed) or claimed!=_digest(candidate): errors.append("record_tamper")
    if len(ids)!=len(set(ids)): errors.append("duplicate_verifier_id")
    if len(paths)!=len(set(paths)): errors.append("duplicate_suite_path")
    return sorted(set(errors))

def build_ownership_registry(records:Sequence[Mapping[str,Any]])->dict[str,Any]:
    rows=[dict(r) for r in records]; errors=validate_verifier_records(rows)
    if errors: return {"status":"blocked","errors":errors,"content_free":True,"execution_invoked":False,"authority_granted":False}
    owners={owner:0 for owner in sorted(ALLOWED_OWNERS)}; classes={name:0 for name in sorted(ALLOWED_CLASSES)}
    for row in rows: owners[row["owner"]]+=1; classes[row["classification"]]+=1
    profile_budgets={p:sum(r["budget_seconds"] for r in rows if p in r["profile_membership"]) for p in sorted(ALLOWED_PROFILES)}
    body={"contract_version":CONTRACT_VERSION,"records":rows,"record_count":len(rows),"owner_counts":owners,
          "classification_counts":classes,"profile_budgets_seconds":profile_budgets,
          "current_regressions_separate_from_historical_debt":True,"duplicate_fixture_groups":sorted({g for g in [r['fixture_group'] for r in rows] if [r['fixture_group'] for r in rows].count(g)>1}),
          "authority_state":"separate_not_granted"}
    return {"status":"registered","registry":body,"registry_digest":_digest(body),"errors":[],"content_free":True,"execution_invoked":False,"authority_granted":False}

def public_ownership_summary(report:Mapping[str,Any])->dict[str,Any]:
    body=report.get("registry") or {}
    return {"contract_version":CONTRACT_VERSION,"status":report.get("status"),"record_count":body.get("record_count",0),
            "owner_count":len([v for v in (body.get("owner_counts") or {}).values() if v]),
            "current_regression_count":(body.get("classification_counts") or {}).get("current_regression",0),
            "retained_checkpoint_count":(body.get("classification_counts") or {}).get("retained_checkpoint",0),
            "historical_debt_count":(body.get("classification_counts") or {}).get("historical_debt",0),
            "duplicate_fixture_group_count":len(body.get("duplicate_fixture_groups") or []),
            "profile_budgets_seconds":dict(body.get("profile_budgets_seconds") or {}),
            "debt_separated":body.get("current_regressions_separate_from_historical_debt") is True,
            "content_free":True,"execution_invoked":False,"authority_granted":False}
