from __future__ import annotations
"""v1241 Unified Operator Dashboard: deterministic, privacy-filtered, inspection-only."""
import hashlib, html, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION="v1241.8"
MILESTONE_NAME="Unified Operator Dashboard"
ROADMAP_PATH="Balanced Mind-and-Action Path 3"
AUTHORITY_FLAGS={
 "dashboard_inspection_authorized":True,"dashboard_filtering_authorized":True,"dashboard_sorting_authorized":True,
 "provider_execution_authorized":False,"command_execution_authorized":False,"test_execution_authorized":False,
 "tool_invocation_authorized":False,"project_mutation_authorized":False,"queue_mutation_authorized":False,
 "schedule_mutation_authorized":False,"priority_mutation_authorized":False,"approval_creation_authorized":False,
 "launch_authorized":False,"pause_authorized":False,"resume_authorized":False,"cancel_authorized":False,
 "retry_authorized":False,"apply_authorized":False,"rollback_authorized":False,"cognition_write_authorized":False,
 "automatic_continuation_authorized":False,"background_execution_authorized":False,"installation_authorized":False,
 "promotion_authorized":False,"certification_authorized":False,"release_authorized":False,
 "model_management_authorized":False,"old_authority_reusable":False,
}
PANELS=(
 ("work_queue","Work Queue","/api/cognition/unified-development-work-queue-checkpoint","queued work and project state"),
 ("plans","Plans and Revisions","/api/cognition/dynamic-execution-plan-revisions","approved plans and revision proposals"),
 ("dependencies","Dependencies","/api/cognition/dependency-aware-execution-assessments","prerequisites and blockers"),
 ("resources","Resources and Concurrency","/api/cognition/resource-concurrency-assessments","capacity and conflicts"),
 ("sessions","Execution Sessions","/api/cognition/execution-session-pause-resume-cancel-recovery-checkpoint","session lifecycle"),
 ("interventions","Interventions","/api/cognition/live-execution-monitoring-operator-intervention-checkpoint","operator requests"),
 ("outcomes","Outcomes and Rollback","/api/cognition/execution-outcome-reflection-learning-integration-checkpoint","sealed outcomes"),
 ("quality","Requirements and Quality","/api/cognition/requirement-quality-assessments","criteria and remediation"),
 ("lessons","Lessons","/api/cognition/evidence-backed-development-outcome-lessons","revisable learning"),
 ("priorities","Goals and Priorities","/api/cognition/goal-motivation-work-priority-integrations","alignment and priorities"),
 ("orchestration","Tool Orchestration","/api/cognition/multi-tool-orchestration-plans","tools and handoffs"),
 ("adapters","Project Adapters","/api/cognition/broader-project-language-adapter-assessments","project families"),
 ("adversarial","Boundary Findings","/api/cognition/adversarial-boundary-assessments","fail-closed findings"),
 ("benchmark","Developer Beta","/api/cognition/integrated-developer-beta-benchmark","integrated benchmark"),
)
PANEL_IDS=tuple(x[0] for x in PANELS)
STATUS_ORDER={x:i for i,x in enumerate(("conflicted","failed","blocked","stale","paused","awaiting_review","ready","complete","unknown"))}
ALIASES={
 "ready":"ready","admissible":"ready","satisfied":"ready","accepted":"ready",
 "awaiting_review":"awaiting_review","review":"awaiting_review","pending_review":"awaiting_review","proposed":"awaiting_review",
 "blocked":"blocked","missing_evidence":"blocked","unverified":"blocked","held":"blocked",
 "paused":"paused","recovered_to_paused":"paused","failed":"failed","rejected":"failed","cancelled":"failed","canceled":"failed",
 "complete":"complete","completed":"complete","sealed":"complete","terminal":"complete",
 "stale":"stale","expired":"stale","conflicted":"conflicted","contradictory":"conflicted","tampered":"conflicted",
 "unknown":"unknown","unavailable":"unknown","partial":"unknown",
}
PRIVATE_TOKENS=("path","secret","token","password","prompt","content","provider_output","test_output","source_text","private","credential")
_SHOW=re.compile(r"^show unified operator dashboard[.!?]*$",re.I)
_SHOW_REGISTRY=re.compile(r"^show unified operator dashboard registry[.!?]*$",re.I)

def _digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _text(v,n=180): return " ".join(str(v or "").split())[:n]

def dashboard_panel_registry()->dict[str,Any]:
 p=[{"panel_id":i,"title":t,"get_path":g,"description":d,"read_only":True,"mutation_controls_present":False} for i,t,g,d in PANELS]
 r={"ok":True,"status":"unified_operator_dashboard_registry_ready","contract_version":CONTRACT_VERSION,"panel_count":len(p),"panels":p,"content_free":True,"read_only":True,**AUTHORITY_FLAGS}; r["registry_digest"]=_digest(r); return r

def normalize_dashboard_status(value,*,stale=False,contradictory=False,available=True):
 if contradictory:return "conflicted"
 if stale:return "stale"
 if not available:return "unknown"
 return ALIASES.get(str(value or "unknown").strip().lower().replace("-","_").replace(" ","_"),"unknown")

def _sanitize(raw:Mapping[str,Any],idx:int)->dict[str,Any]:
 panel=str(raw.get("panel_id") or "benchmark"); panel=panel if panel in PANEL_IDS else "benchmark"
 project=_text(raw.get("project_id") or "unscoped",80); session=_text(raw.get("session_id") or "",80)
 status=normalize_dashboard_status(raw.get("status"),stale=bool(raw.get("stale")),contradictory=bool(raw.get("contradictory")),available=raw.get("available") is not False)
 authority=str(raw.get("authority_state") or "none").lower(); authority=authority if authority in {"none","valid","consumed","expired","not_applicable"} else "none"
 row={"record_id":_text(raw.get("record_id") or f"dashboard-record-{idx:04d}",96),"project_id":project,"session_id":session,
      "panel_id":panel,"status":status,"summary":_text(raw.get("summary") or "Content-free operator summary."),
      "evidence_digest":_text(raw.get("evidence_digest") or _digest({"i":idx,"p":panel,"project":project}),64),
      "lineage_digest":_text(raw.get("lineage_digest") or "",64),"authority_state":authority,
      "priority":max(0,min(100,int(raw.get("priority") or 0))),"updated_generation":max(0,int(raw.get("updated_generation") or 0)),
      "review_required":bool(raw.get("review_required")) or status=="awaiting_review","blocker_count":max(0,int(raw.get("blocker_count") or 0)),
      "risk_count":max(0,int(raw.get("risk_count") or 0)),"available":raw.get("available") is not False}
 actions={"conflicted":"inspect_evidence_and_request_exact_operator_decision","failed":"inspect_evidence_and_request_exact_operator_decision",
 "blocked":"inspect_evidence_and_request_exact_operator_decision","stale":"inspect_evidence_and_request_exact_operator_decision",
 "paused":"inspect_pause_reason_and_require_fresh_resume_authority","awaiting_review":"review_exact_record",
 "ready":"inspect_readiness_and_obtain_separate_execution_authority","complete":"inspect_outcome_and_quality_evidence","unknown":"inspect_subsystem_availability"}
 row["safe_next_action"]=actions[status]; row["record_digest"]=_digest(row); return row

def _defaults(): return [{"record_id":f"panel-{i}","project_id":"unscoped","panel_id":i,"status":"unknown","summary":f"{t} inspection is available through its GET-only surface.","authority_state":"not_applicable"} for i,t,_,_ in PANELS]

def build_unified_operator_dashboard_snapshot(records:Sequence[Mapping[str,Any]]|None=None,*,source_version="v1241.8")->dict[str,Any]:
 rows=[_sanitize(x,i) for i,x in enumerate(records if records is not None else _defaults(),1)]
 rows.sort(key=lambda x:(STATUS_ORDER[x["status"]],-x["priority"],x["project_id"],x["panel_id"],x["record_id"]))
 counts={k:sum(x["status"]==k for x in rows) for k in STATUS_ORDER}; projects=sorted({x["project_id"] for x in rows}); sessions=sorted({x["session_id"] for x in rows if x["session_id"]})
 conflicts=counts["conflicted"]
 r={"ok":conflicts==0,"status":"unified_operator_dashboard_ready" if not conflicts else "unified_operator_dashboard_conflicted",
 "contract_version":CONTRACT_VERSION,"source_version":source_version,"record_count":len(rows),"project_count":len(projects),"session_count":len(sessions),"panel_count":len(PANELS),
 "projects":projects,"status_counts":counts,"authority_summary":{"valid":sum(x["authority_state"]=="valid" for x in rows),"consumed":sum(x["authority_state"]=="consumed" for x in rows),"dashboard_grants_authority":False},
 "records":rows,"read_only":True,"content_free":True,"private_fields_suppressed":True,"opening_record_mutates_state":False,"filtering_mutates_state":False,"sorting_mutates_state":False,
 "partial_subsystem_availability_supported":True,"cross_project_records_kept_separate":True,**AUTHORITY_FLAGS}
 r["snapshot_digest"]=_digest(r); return r

def filter_unified_operator_dashboard_snapshot(snapshot:Mapping[str,Any],*,project_id="",panel_id="",status=""):
 expected=str(snapshot.get("snapshot_digest") or ""); copy=dict(snapshot); copy.pop("snapshot_digest",None)
 if expected and expected!=_digest(copy): return {"ok":False,"status":"unified_operator_dashboard_snapshot_tampered","records":[],"read_only":True,"content_free":True,**AUTHORITY_FLAGS}
 rows=list(snapshot.get("records") or [])
 if project_id: rows=[x for x in rows if x.get("project_id")==project_id]
 if panel_id: rows=[x for x in rows if x.get("panel_id")==panel_id]
 if status: rows=[x for x in rows if x.get("status")==normalize_dashboard_status(status)]
 r={"ok":True,"status":"unified_operator_dashboard_filter_ready","filters":{"project_id":project_id,"panel_id":panel_id,"status":status},"record_count":len(rows),"records":rows,"source_snapshot_digest":expected,"read_only":True,"content_free":True,**AUTHORITY_FLAGS}; r["filter_digest"]=_digest(r); return r

def render_unified_operator_dashboard_html(snapshot:Mapping[str,Any]|None=None)->str:
 s=dict(snapshot or build_unified_operator_dashboard_snapshot()); cards=[]
 for p in dashboard_panel_registry()["panels"]:
  count=sum(x.get("panel_id")==p["panel_id"] for x in s.get("records",[])); cards.append(f"<article class='dashboard-card' data-tip='{html.escape(p['description'])}'><h2>{html.escape(p['title'])}</h2><p>{count} summarized record(s)</p><code>{html.escape(p['get_path'])}</code></article>")
 counts=" ".join(f"<span>{html.escape(k)}: {v}</span>" for k,v in s.get("status_counts",{}).items())
 return "<!doctype html><html><head><meta charset='utf-8'><title>Unified Operator Dashboard</title><style>body{font-family:system-ui;background:#0d1117;color:#e6edf3;margin:0;padding:24px}.command-deck{max-width:1200px;margin:auto}.summary,.grid{display:grid;gap:12px}.summary{grid-template-columns:repeat(auto-fit,minmax(130px,1fr));margin:18px 0}.summary span,.dashboard-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px}.grid{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}.muted{color:#8b949e}code{word-break:break-all}</style></head><body><main class='command-deck operator-console'><h1>Unified Operator Dashboard</h1><p class='muted'>GET-only consolidated inspection. No button, filter, sort, or record view grants authority.</p><p class='muted'>Multi-day session continuity: <code>/api/cognition/session-continuity-assessments</code></p><p class='muted'>Cross-session project understanding: <code>/api/cognition/project-understanding-reconciliations</code></p><p class='muted'>Initiative and proposal pacing: <code>/api/cognition/initiative-pacing-decisions</code></p><p class='muted'>Privacy, security, and secret-management audit: <code>/api/cognition/privacy-security-audits</code></p><p class='muted'>Feature freeze and final hardening: <code>/api/cognition/feature-freeze-final-hardening-report</code></p><p class='muted'>Integrated mind, conversation, and development benchmark: <code>/api/cognition/integrated-mind-conversation-development-benchmark</code></p><section class='summary'>"+counts+"</section><section class='grid'>"+"".join(cards)+"</section></main></body></html>"

def unified_operator_dashboard_response(row):
 if row.get("status")=="unified_operator_dashboard_registry_ready": return f"The Unified Operator Dashboard exposes {row.get('panel_count')} read-only panels and grants no execution authority."
 return f"Unified Operator Dashboard: {row.get('status')}. Records: {row.get('record_count',0)}; projects: {row.get('project_count',0)}. Inspection only."

def process_unified_operator_dashboard_control(user_text,*,runtime_root=None):
 del runtime_root; text=str(user_text or "").strip()
 if _SHOW_REGISTRY.fullmatch(text):
  row=dashboard_panel_registry(); return {"active":True,"response":unified_operator_dashboard_response(row),"unified_operator_dashboard":row}
 if _SHOW.fullmatch(text):
  row=build_unified_operator_dashboard_snapshot(); return {"active":True,"response":unified_operator_dashboard_response(row),"unified_operator_dashboard":row}
 return {"active":False}
