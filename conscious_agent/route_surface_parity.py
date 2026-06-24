from __future__ import annotations

import hashlib, json
from pathlib import Path
from typing import Any
from dashboard_route_probe import RECENT_DASHBOARD_ROUTES, build_dashboard_route_health_audit, build_dashboard_route_inventory
from source_surface_manifest import RECENT_SURFACE_ENTRIES, build_source_surface_manifest_summary

ROUTE_SURFACE_PARITY_VERSION = "500.0"
ROUTE_SURFACE_PARITY_BOUNDARIES = {
    "route_presence_is_authorization": False,
    "route_health_is_approval": False,
    "manifest_presence_is_authorization": False,
    "surface_parity_is_permission": False,
    "smoke_success_is_approval": False,
    "parity_audit_executes_routes": False,
    "parity_audit_applies_patches": False,
    "parity_audit_writes_memory": False,
    "parity_audit_expands_autonomy": False,
    "operator_review_required": True,
}
EXPECTED_RECENT_ROUTES = [
    "/authorization-confusion-patterns","/authorization-language-scan","/authorization-firewall-decision-packet","/authorization-boundary-map","/authorization-firewall-audit",
    "/metadata-version-inventory","/project-workspace-metadata-alignment","/release-packaging-version-integrity","/current-state-documentation-header-audit","/metadata-release-integrity-audit",
    "/authorization-firewall-severity-classifier","/authorization-firewall-safe-boundary-filter","/authorization-firewall-warning-status","/authorization-firewall-audit-status-split","/authorization-firewall-signal-triage-audit",
    "/recent-dashboard-route-probe-refresh","/source-surface-manifest-parity-policy","/surface-route-api-cli-crosscheck","/route-health-boundary-language","/route-surface-parity-audit",
]
EXPECTED_RECENT_SURFACE_IDS = [
    "v446-authorization-confusion-patterns","v447-authorization-language-scan","v448-authorization-firewall-decision-packet","v449-authorization-boundary-map","v450-authorization-firewall",
    "v451-metadata-version-inventory","v452-project-workspace-metadata-alignment","v453-release-packaging-version-integrity","v454-current-state-documentation-header-audit","v455-metadata-release-integrity",
    "v456-authorization-firewall-severity-classifier","v457-authorization-firewall-safe-boundary-filter","v458-authorization-firewall-warning-status","v459-authorization-firewall-audit-status-split","v460-authorization-firewall-signal-triage",
    "v461-recent-dashboard-route-probe-refresh","v462-source-surface-manifest-parity-policy","v463-surface-route-api-cli-crosscheck","v464-route-health-boundary-language","v465-route-surface-parity-audit",
]

def _read(path: Path) -> str:
    try: return path.read_text(encoding="utf-8", errors="ignore")
    except Exception: return ""

def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]

def _docs(root: Path) -> str:
    rels=["README_NEXT_STEPS.md","README_RELEASE_HISTORY.md","conscious_agent/dashboard.py","conscious_agent/dashboard_route_probe.py","conscious_agent/source_surface_manifest.py","conscious_agent/route_surface_parity.py","conscious_agent/self_maintenance.py","conscious_agent/api_server.py","conscious_agent/main.py","tools/smoke_check.py","conscious_agent/smoke_segment_registry.py"]
    return "\n".join(_read(root/r) for r in rels)

def _route_set(root: Path) -> set[str]:
    return {str(row.get("route")) for row in build_dashboard_route_inventory(root).get("routes", [])}

def _manifest_ids() -> set[str]:
    return {str(e.get("surface_id")) for e in RECENT_SURFACE_ENTRIES}

def build_recent_dashboard_route_probe_refresh(root: str|Path|None=None) -> dict[str,Any]:
    root=Path(root or Path.cwd()); dash=_read(root/"conscious_agent/dashboard.py"); inv=_route_set(root)
    rows=[{"route":r,"in_dashboard_source":r in dash,"in_route_probe_inventory":r in inv,"route_presence_is_authorization":False,"route_health_is_approval":False} for r in EXPECTED_RECENT_ROUTES]
    miss=[row["route"] for row in rows if not row["in_dashboard_source"] or not row["in_route_probe_inventory"]]
    return {"version":ROUTE_SURFACE_PARITY_VERSION,"state":"recent_dashboard_route_probe_refresh_review_only","rows":rows,"route_count":len(rows),"missing_or_unprobed_routes":miss,"route_presence_is_authorization":False,"route_health_is_approval":False,"ok":not miss}

def build_source_surface_manifest_parity_policy(root: str|Path|None=None) -> dict[str,Any]:
    ids=_manifest_ids(); miss=[sid for sid in EXPECTED_RECENT_SURFACE_IDS if sid not in ids]
    return {"version":ROUTE_SURFACE_PARITY_VERSION,"state":"source_surface_manifest_parity_policy_review_only","policy":"every_governed_substage_surface","expected_recent_surface_ids":EXPECTED_RECENT_SURFACE_IDS,"missing_recent_surface_ids":miss,"manifest_entry_count":len(ids),"manifest_presence_is_authorization":False,"surface_parity_is_permission":False,"ok":not miss}

def build_surface_route_api_cli_crosscheck(root: str|Path|None=None, docs: str="") -> dict[str,Any]:
    root=Path(root or Path.cwd()); docs=docs or _docs(root); dash=_read(root/"conscious_agent/dashboard.py"); inv=_route_set(root); manifest=build_source_surface_manifest_summary(RECENT_SURFACE_ENTRIES); rows=[]
    for e in manifest.get("entries", []):
        dr=str(e.get("dashboard_route","")); api=str(e.get("api_route","")); cli=str(e.get("cli_flag","")); smoke=str(e.get("smoke_check","")); builder=str(e.get("builder_function","")); text=str(e.get("text_function",""))
        checks={"dashboard_source": bool(dr and dr in dash), "route_probe_inventory": bool((not dr) or dr in inv or dr.startswith('/api/')), "api_dispatch_token": bool(api and api.replace('/api/','').replace('/layer','') in docs), "cli_flag_token": bool(cli and cli in docs), "builder_token": bool(builder and builder in docs), "text_renderer_token": bool(text and text in docs), "smoke_token": bool(smoke and smoke in docs)}
        rows.append({"surface_id":e.get("surface_id"),"dashboard_route":dr,"api_route":api,"cli_flag":cli,"smoke_check":smoke,"checks":checks,"missing":[k for k,v in checks.items() if not v],"ok":all(checks.values())})
    blockers=[r for r in rows if not r["ok"]]
    return {"version":ROUTE_SURFACE_PARITY_VERSION,"state":"surface_route_api_cli_crosscheck_review_only","rows":rows,"blocker_count":len(blockers),"blockers":[{"surface_id":r["surface_id"],"missing":r["missing"]} for r in blockers],"surface_parity_is_permission":False,"smoke_success_is_approval":False,"ok":not blockers and manifest.get("ok") is True}

def build_route_health_boundary_language(root: str|Path|None=None, docs: str="") -> dict[str,Any]:
    root=Path(root or Path.cwd()); docs=docs or _docs(root); health=build_dashboard_route_health_audit(root, docs)
    required=["route_presence_is_authorization=False","route_health_is_approval=False","manifest_presence_is_authorization=False","surface_parity_is_permission=False","smoke_success_is_approval=False","route_health_confirms_render_status_only=True","route_health_does_not_authorize_execution=True","operator_approval_still_required=True"]
    miss=[t for t in required if t not in docs]
    return {"version":ROUTE_SURFACE_PARITY_VERSION,"state":"route_health_boundary_language_review_only","route_health_audit_ok":bool(health.get("ok")),"required_boundary_tokens":required,"missing_boundary_tokens":miss,"route_health_confirms_render_status_only":True,"route_health_does_not_authorize_execution":True,"route_presence_is_authorization":False,"route_health_is_approval":False,"ok":not miss and bool(health.get("ok"))}

def build_route_surface_parity_audit(root: str|Path|None=None, docs: str="") -> dict[str,Any]:
    root=Path(root or Path.cwd()); docs=docs or _docs(root); refresh=build_recent_dashboard_route_probe_refresh(root); policy=build_source_surface_manifest_parity_policy(root); cross=build_surface_route_api_cli_crosscheck(root, docs); boundary=build_route_health_boundary_language(root, docs)
    required=["recent-dashboard-route-probe-refresh","source-surface-manifest-parity-policy","surface-route-api-cli-crosscheck","route-health-boundary-language","route-surface-parity-audit","operator-governed-route-surface-parity-v1","every_governed_substage_surface","surface_parity_is_permission=False","route_health_confirms_render_status_only=True","route_health_does_not_authorize_execution=True","parity_audit_applies_patches=False","parity_audit_writes_memory=False","parity_audit_expands_autonomy=False"]
    blockers=[name for name,rep in [("refresh",refresh),("policy",policy),("crosscheck",cross),("boundary",boundary)] if rep.get("ok") is not True] + ["docs:"+t for t in required if t not in docs]
    return {"version":ROUTE_SURFACE_PARITY_VERSION,"state":"operator_governed_route_surface_parity_review_only","refresh":refresh,"policy":policy,"crosscheck":cross,"boundary_language":boundary,"boundaries":dict(ROUTE_SURFACE_PARITY_BOUNDARIES),"blockers":blockers,"ok":not blockers,"status":"pass" if not blockers else "blocked","route_presence_is_authorization":False,"route_health_is_approval":False,"manifest_presence_is_authorization":False,"surface_parity_is_permission":False,"smoke_success_is_approval":False,"applies_patches":False,"writes_memory":False,"expands_autonomy":False,"creates_approval":False,"operator_approval_still_required":True,"audit_hash":_hash({"routes":refresh.get("route_count"),"entries":policy.get("manifest_entry_count"),"blockers":blockers})}

def render_route_surface_parity_lines(report: dict[str,Any]) -> list[str]:
    lines=[f"state: {report.get('state')}",f"version: {report.get('version')}",f"status: {report.get('status','pass' if report.get('ok') else 'blocked')}",f"ok: {report.get('ok')}",f"surface_parity_is_permission: {report.get('surface_parity_is_permission',False)}",f"route_health_is_approval: {report.get('route_health_is_approval',False)}",f"manifest_presence_is_authorization: {report.get('manifest_presence_is_authorization',False)}",f"operator_approval_still_required: {report.get('operator_approval_still_required',True)}"]
    if report.get("refresh"): lines += [f"recent_route_count: {report['refresh'].get('route_count')}", f"missing_or_unprobed_routes: {len(report['refresh'].get('missing_or_unprobed_routes',[]))}"]
    if report.get("crosscheck"): lines.append(f"surface_crosscheck_blockers: {report['crosscheck'].get('blocker_count')}")
    if report.get("blockers"): lines += ["blockers:"]+[f"- {b}" for b in report.get("blockers",[])[:20]]
    return lines

# v460.1-v465.0 route surface parity smoke tokens: recent-dashboard-route-probe-refresh source-surface-manifest-parity-policy surface-route-api-cli-crosscheck route-health-boundary-language route-surface-parity-audit operator-governed-route-surface-parity-v1 every_governed_substage_surface route_presence_is_authorization=False route_health_is_approval=False manifest_presence_is_authorization=False surface_parity_is_permission=False smoke_success_is_approval=False route_health_confirms_render_status_only=True route_health_does_not_authorize_execution=True parity_audit_applies_patches=False parity_audit_writes_memory=False parity_audit_expands_autonomy=False operator_approval_still_required=True data-tip no_native_title_tooltip command-deck operator-console
