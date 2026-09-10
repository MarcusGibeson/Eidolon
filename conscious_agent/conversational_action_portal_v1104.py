from __future__ import annotations

"""Read-only conversational action classification, catalog, and proposal cards.

The module is intentionally pure: importing or calling it never creates runtime
files, stores the request, invokes a provider, validates/runs a shell command,
creates an approval, or mutates conversation/release state.
"""

import re
from typing import Any, Mapping

from release_metadata import WORKING_SOURCE_VERSION
from conversational_capability_boundary import is_supervised_capability_catalog_request

ACTION_PORTAL_SCHEMA_VERSION = "1"
ACTION_PORTAL_CONTRACT_VERSION = "v1104.2"
DIRECT_COMMAND = "direct_command"
DIRECT_FUNCTION = "direct_function"
APPROVAL = "approval"
BLOCKED = "blocked"
INFO = "info"

_REGISTERED_TOOLS: tuple[dict[str, Any], ...] = (
    {"id":"diagnostics","label":"diagnostics and system health","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Inspect bounded system-health and diagnostic evidence.","risk_level":"low","approval_required":False},
    {"id":"maintenance","label":"maintenance scans","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Run a bounded, read-oriented maintenance scan.","risk_level":"low","approval_required":False},
    {"id":"settings_health","label":"settings and configured-model health","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Inspect configured settings and local-model readiness without generation.","risk_level":"low","approval_required":False},
    {"id":"approvals","label":"approval inbox review","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Review the operator-controlled approval inbox without deciding anything.","risk_level":"low","approval_required":False},
    {"id":"task_project","label":"task and project status","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Inspect bounded task and active-project status.","risk_level":"low","approval_required":False},
    {"id":"memory","label":"memory status","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Inspect memory health and compaction status without reading private memory content.","risk_level":"low","approval_required":False},
    {"id":"attention_center","label":"redacted operator attention center","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Show a redacted operator-attention summary across supervised surfaces.","risk_level":"low","approval_required":False},
    {"id":"notifications","label":"notifications and bounded watch checks","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Inspect notifications or perform one bounded watch check.","risk_level":"low","approval_required":False},
    {"id":"planning","label":"session planning","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Create a bounded session plan without executing its steps.","risk_level":"low","approval_required":False},
    {"id":"file_review","label":"safe static file review","mode":DIRECT_COMMAND,"boundary":"allowlisted read","description":"Perform static review of one explicitly named source file.","risk_level":"low","approval_required":False},
    {"id":"patch_proposal","label":"patch proposals without automatic application","mode":DIRECT_FUNCTION,"boundary":"proposal only","description":"Prepare a patch proposal for review without applying it.","risk_level":"medium","approval_required":True},
    {"id":"self_development","label":"proposal-only supervised self-development","mode":DIRECT_COMMAND,"boundary":"proposal only","description":"Prepare one supervised self-development proposal and stop before source edits.","risk_level":"medium","approval_required":True},
    {"id":"software_development","label":"supervised software development","mode":DIRECT_FUNCTION,"boundary":"isolated workspace after approval","description":"Prepare a governed development proposal; the v1200 alpha can build and test the calculator benchmark after explicit approval.","risk_level":"medium","approval_required":True},
)

_CONVERSATION_ONLY = re.compile(r"^\s*(?:hi|hello|hey|yo|howdy|good\s+(?:morning|afternoon|evening)|thanks|thank\s+you|awesome|nice|cool|how\s+are\s+you|tell\s+me\s+a\s+joke)\b[\s!.?]*$",re.I)
_AMBIGUOUS_ACTION = re.compile(r"^\s*(?:do|handle|fix|run|check|take\s+care\s+of|deal\s+with)\s+(?:it|that|this|the\s+thing)(?:\s+for\s+me)?[\s!.?]*$",re.I)
_MIXED_CONVERSATION_CUE = re.compile(r"\b(?:thanks|thank\s+you|how\s+are\s+you|hope\s+you(?:'re|\s+are)|please)\b",re.I)
_ACTION_CUE = re.compile(r"\b(?:run|check|show|review|scan|plan|apply|approve|install|rollback|revert|cancel|retry|suggest|patch|diagnostic|maintenance|status|notification|approval|task|project|memory|file|watch)\b",re.I)
_BLOCKED_SCOPE = re.compile(r"\b(?:bypass\s+(?:approval|safety)|disable\s+(?:approval|safety|governance)|unrestricted\s+(?:shell|command)|execute\s+(?:arbitrary|raw)\s+(?:shell|command)|(?:download|delete|remove|replace|switch|change|install)\b[^\n]{0,60}\b(?:model|provider)|(?:promote|certify|authorize|install)\s+(?:the\s+)?release|expose\s+(?:secrets|credentials)|make\s+(?:yourself|eidolon)\s+autonomous)\b",re.I)
_FOLLOW_UP = (
    ("status",re.compile(r"^(?:please\s+)?(?:did (?:that|it) finish|is (?:that|it) (?:done|finished|still running)|what happened(?: with (?:that|it))?|how did (?:that|it) go|did (?:that|it) work|show me (?:the )?(?:result|status)|what(?:'s| is) the (?:result|status)|why did (?:that|it) fail)\s*[?.!]*$",re.I)),
    ("retry",re.compile(r"^(?:please\s+)?(?:try|retry|run|do) (?:that|it)(?: again| one more time)?\s*[?.!]*$",re.I)),
    ("cancel",re.compile(r"^(?:please\s+)?(?:cancel|stop|hold) (?:that|it)(?: for now)?\s*[?.!]*$",re.I)),
    ("approval",re.compile(r"^(?:please\s+)?(?:approve (?:that|it)|review the approval for (?:that|it)|show the approval for (?:that|it))\s*[?.!]*$",re.I)),
)


def _clean(value:Any,limit:int=280)->str:return " ".join(str(value or "").split())[:max(0,int(limit))]

def _follow_up_kind(request:str)->str:
    for kind,pattern in _FOLLOW_UP:
        if pattern.fullmatch(request):return kind
    return ""

def _descriptor(request:str)->dict[str,Any]|None:
    lower=request.lower()
    def d(tool_id:str,intent:str,title:str,summary:str,mode:str=DIRECT_COMMAND,risk:str="low",boundary:str="")->dict[str,Any]:
        return {"tool_id":tool_id,"intent":intent,"title":title,"summary":summary,"execution_mode":mode,"risk_level":risk,"safety_boundary":boundary or "This preview does not execute, save, authorize, contact a provider, or expose a raw command."}
    from release_self_knowledge import is_grouped_release_inspection
    if is_grouped_release_inspection(request):return d("release_summary","release_summary","Inspect current release evidence","Read the allowlisted release authority and README files once, then report only the verified current-release summary.",DIRECT_FUNCTION,"low","The inspection is read-only, provider-free, source-preserving, and grants no release authority.")
    if is_supervised_capability_catalog_request(request):return d("","supervised_capabilities","Current supervised capabilities","Show the bounded operator-visible tool catalog.",INFO,"low","The catalog is informational and cannot execute any tool.")
    if any(target in lower for target in ("web page","webpage","website","web app","application","software","program")) and any(verb in lower for verb in ("make","build","create","develop","implement","code")):return d("software_development","supervised_software_development_campaign_request","Prepare supervised development proposal","Inspect, specify, plan, and present a bounded development proposal. Workspace writes and tests require a separate explicit operator approval.",DIRECT_FUNCTION,"medium","The preview does not write files. The v1200 executable alpha is limited to the calculator web-app benchmark and writes only to an isolated runtime workspace after approval.")
    if any(x in lower for x in ("diagnostic","system health","health check","system check","is everything working")):return d("diagnostics","run_diagnostics","Run diagnostics","Inspect one bounded diagnostics report.")
    if any(x in lower for x in ("settings health","model health","configuration health","ollama health")):return d("settings_health","settings_health","Check settings and model health","Inspect configured settings and local-model availability without generation.")
    if any(x in lower for x in ("maintenance","maintainence","maintenance scan","need maintenance")):return d("maintenance","maintenance_scan","Run maintenance scan","Prepare one bounded no-AI maintenance scan.")
    if any(x in lower for x in ("attention center","what needs my attention","what needs attention","anything need attention","anything needs attention")):return d("attention_center","attention_center","Show attention center","Show one redacted read-only operator-attention view.")
    if any(x in lower for x in ("notification","alert","messages for me","watch check","run watch","check watch")):return d("notifications","notifications","Show notifications or run a watch check","Inspect unread notifications or one bounded watch result.")
    if any(x in lower for x in ("approval","permission","waiting for review","waiting for approval")) and not re.search(r"\bapply\b.*\bpatch\b",lower):return d("approvals","approval_inbox","Show approval inbox","Review pending approval requests without deciding them.")
    if "plan" in lower or "what next" in lower or "next step" in lower or "next session" in lower:return d("planning","plan_session","Plan next session","Create a bounded plan without executing its steps.")
    if "task status" in lower or "task queue" in lower or "next task" in lower or "current task" in lower:return d("task_project","task_status","Show task status","Inspect the bounded task queue.")
    if any(x in lower for x in ("project status","active project","how is the project","where are we on the project")):return d("task_project","project_status","Show project status","Inspect the active project status.")
    if any(x in lower for x in ("memory status","how is your memory","check your memory","show memory")):return d("memory","memory_status","Show memory status","Inspect memory size and compaction status without private memory content.")
    if re.search(r"\breview\b",lower) and re.search(r"(?:[a-z0-9_.-]+/)+[a-z0-9_.-]+",request,re.I):return d("file_review","review_file","Review one source file","Perform bounded static review of the explicitly named source file.")
    if re.search(r"\b(?:apply|install|approve)\b.*\bpatch\b|\bapply\b.*\blatest\b",lower):return d("patch_proposal","request_apply_patch","Request approval to apply a patch","Applying a patch changes source and therefore requires a separate approval.",APPROVAL,"medium","The preview cannot create or approve the write. A separate governed approval remains required.")
    if re.search(r"\b(?:rollback|undo|revert)\b.*\b(?:patch|latest|change)\b",lower):return d("patch_proposal","request_rollback_patch","Request approval to rollback a patch","Rollback changes source and requires a separate approval.",APPROVAL,"medium","The preview cannot authorize or perform rollback.")
    if any(x in lower for x in ("suggest patch","suggest improvement","patch proposal")) or ("fix " in lower and re.search(r"(?:[a-z0-9_.-]+/)+[a-z0-9_.-]+",request,re.I)):return d("patch_proposal","suggest_patch","Prepare patch proposal","Create a review-only proposal without applying source changes.",DIRECT_FUNCTION,"medium","Proposal generation remains review-only; applying still requires explicit approval.")
    if "self development" in lower or "self-development" in lower or "dev loop" in lower or "improve yourself" in lower:return d("self_development","self_development_cycle","Prepare supervised self-development proposal","Inspect and rank bounded improvement candidates, then stop before source edits.",DIRECT_COMMAND,"medium","Self-development remains proposal-only and cannot edit source or expand autonomy automatically.")
    return None

def build_operator_tool_catalog()->dict[str,Any]:
    tools=[]
    for position,row in enumerate(_REGISTERED_TOOLS,start=1):
        tools.append({"position":position,"tool_id":row["id"],"label":row["label"],"description":row["description"],"mode":row["mode"],"boundary":row["boundary"],"risk_level":row["risk_level"],"approval_required":bool(row["approval_required"]),"preview_available":True,"automatic_execution":False,"automatic_authorization":False,"operator_visible":True})
    return {"schema_version":ACTION_PORTAL_SCHEMA_VERSION,"contract_version":"v1200.0","working_source_version":str(WORKING_SOURCE_VERSION),"status":"ready","tool_count":len(tools),"tools":tools,"catalog_bounded":len(tools)==13,"raw_commands_included":False,"private_arguments_included":False,"provider_contacted":False,"runtime_mutated":False,"approval_granted":False,"release_authorized":False,"content_free":True}

def classify_conversation_action(user_text:str)->dict[str,Any]:
    request=_clean(user_text,4000); reason=[]; desc=None; follow=""
    if not request:classification="ambiguous";confidence=0.0;reason=["empty_turn"]
    elif _BLOCKED_SCOPE.search(request):classification="blocked";confidence=.99;reason=["prohibited_scope","operator_boundary_required"]
    elif _AMBIGUOUS_ACTION.fullmatch(request):classification="ambiguous";confidence=.42;reason=["action_language_without_target","clarification_required"]
    else:
        follow=_follow_up_kind(request);desc=_descriptor(request)
        mixed=bool(desc and _MIXED_CONVERSATION_CUE.search(request) and _ACTION_CUE.search(request))
        if follow:classification="follow_up";confidence=.94;reason=["recognized_action_follow_up",f"follow_up_{follow}"]
        elif mixed:classification="mixed";confidence=.87;reason=["conversation_and_action_in_same_turn","action_preview_required"]
        elif desc:classification="action";confidence=.97 if desc["execution_mode"]==APPROVAL else .95;reason=["registered_action_match",f"mode_{desc['execution_mode']}"]
        elif _CONVERSATION_ONLY.fullmatch(request):classification="conversation";confidence=.93;reason=["conversation_only_turn"]
        elif _ACTION_CUE.search(request):classification="ambiguous";confidence=.48;reason=["unregistered_or_underspecified_action","clarification_required"]
        else:classification="conversation";confidence=.78;reason=["no_registered_action_required"]
    return {"schema_version":ACTION_PORTAL_SCHEMA_VERSION,"contract_version":ACTION_PORTAL_CONTRACT_VERSION,"working_source_version":str(WORKING_SOURCE_VERSION),"status":"classified","classification":classification,"confidence":round(confidence,2),"reason_codes":reason,"action_candidate":classification in {"action","mixed","follow_up","ambiguous","blocked"},"tool_id":desc["tool_id"] if desc and classification in {"action","mixed"} else "","intent":desc["intent"] if desc and classification in {"action","mixed"} else "","execution_mode":desc["execution_mode"] if desc and classification in {"action","mixed"} else "","requires_clarification":classification=="ambiguous","blocked":classification=="blocked","request_stored":False,"provider_contacted":False,"runtime_mutated":False,"approval_granted":False,"release_authorized":False,"content_free":True,"private_values_included":False}

def build_action_proposal_card(user_text:str)->dict[str,Any]:
    classification=classify_conversation_action(user_text);kind=classification["classification"]
    base={"schema_version":ACTION_PORTAL_SCHEMA_VERSION,"contract_version":ACTION_PORTAL_CONTRACT_VERSION,"working_source_version":str(WORKING_SOURCE_VERSION),"status":"preview","classification":kind,"confidence":classification["confidence"],"reason_codes":list(classification["reason_codes"]),"preview_only":True,"will_execute":False,"request_stored":False,"provider_contacted":False,"runtime_mutated":False,"approval_granted":False,"release_authorized":False,"automatic_execution":False,"automatic_authorization":False,"private_arguments_included":False,"raw_command_included":False,"content_free":True,"private_values_included":False,"operator_authority_required":True}
    if kind=="conversation":base.update({"card_type":"conversation_only","title":"Conversation only","summary":"This turn does not require an Eidolon tool or operator action.","tool_id":"","risk_level":"none","approval_required":False,"execution_timing":"not_applicable","operator_decision":"continue_conversation","safety_boundary":"No command, approval, provider request, or runtime mutation is proposed."});return base
    if kind=="ambiguous":base.update({"card_type":"clarification_required","title":"Clarification required","summary":"The request sounds actionable, but the target or intended outcome is not specific enough to select a bounded tool safely.","tool_id":"","risk_level":"unknown","approval_required":False,"execution_timing":"after_clarification_and_new_preview","operator_decision":"clarify_target_or_outcome","safety_boundary":"No tool is selected by guessing and nothing runs automatically."});return base
    if kind=="blocked":base.update({"card_type":"blocked_request","title":"Request blocked by operator boundaries","summary":"The requested scope is not available through the conversational action portal.","tool_id":"","risk_level":"prohibited","approval_required":True,"execution_timing":"not_available","operator_decision":"use_an_explicit_governed_surface_or_reframe","safety_boundary":"Unrestricted commands, safety bypass, model/provider management, and release authority remain outside chat actions."});return base
    if kind=="follow_up":base.update({"card_type":"information_card","title":"Action follow-up","summary":"This refers to a prior supervised action. Resolve the exact target before status, cancellation, retry, or approval review.","tool_id":"","intent":"action_follow_up","execution_mode":INFO,"risk_level":"low","approval_required":False,"execution_timing":"after_exact_target_resolution","operator_decision":"review_exact_prior_action","safety_boundary":"The preview does not infer or mutate a prior action."});return base
    desc=_descriptor(_clean(user_text,4000)) or {"tool_id":"","intent":"unknown","title":"Supervised action preview","summary":"Review the requested scope before doing anything.","execution_mode":BLOCKED,"risk_level":"unknown","safety_boundary":"Nothing runs automatically."}
    mode=desc["execution_mode"];risk=desc["risk_level"]
    if mode==APPROVAL:card="approval_proposal";timing="only_after_separate_explicit_approval";decision="review_then_create_approval_request"
    elif mode in {DIRECT_COMMAND,DIRECT_FUNCTION}:card="action_proposal";timing="only_after_visible_explanation_and_explicit_operator_send";decision="review_then_explicitly_request_execution"
    elif mode==BLOCKED:card="blocked_request";timing="not_available";decision="reframe_or_use_governed_surface"
    else:card="information_card";timing="not_applicable";decision="review_information"
    base.update({"card_type":card,"title":desc["title"],"summary":desc["summary"],"tool_id":desc["tool_id"],"intent":desc["intent"],"execution_mode":mode,"risk_level":risk,"approval_required":mode==APPROVAL or risk in {"medium","high"},"execution_timing":timing,"operator_decision":decision,"safety_boundary":desc["safety_boundary"],"prohibited_side_effects":["automatic_execution","automatic_approval","provider_or_model_change","release_promotion_or_certification","private_argument_disclosure"]});return base

def action_portal_contains_private_fields(value:Any)->bool:
    forbidden={"command","args","arguments","path","root","content","draft","message","prompt","response","payload","secret","credential","endpoint","memory","conversation_id","session_id","project_id","model_name","provider_payload","history","transcript","user_request","request_text"}
    if isinstance(value,Mapping):
        for key,item in value.items():
            low=str(key).lower()
            if low in forbidden or low.endswith("_command") or low.endswith("_args"):return True
            if action_portal_contains_private_fields(item):return True
    elif isinstance(value,list):return any(action_portal_contains_private_fields(item) for item in value)
    return False
