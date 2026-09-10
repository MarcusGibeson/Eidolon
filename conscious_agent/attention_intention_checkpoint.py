from __future__ import annotations
"""Strictly read-only v1107.5 attention-to-intention continuity checkpoint."""
from pathlib import Path
import os
from agenda_continuity_checkpoint import build_agenda_continuity_checkpoint
from agenda_guided_reflection import AgendaGuidedReflection
from bounded_intention_formation import BoundedIntentionStore
CONTRACT_VERSION="v1107.5"
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _inside(c,p):
 try:c.resolve().relative_to(p.resolve());return True
 except ValueError:return False
def build_attention_intention_checkpoint(runtime_root=None,*,source_root=None):
 root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();source=Path(source_root).expanduser().resolve() if source_root else Path(__file__).resolve().parents[1]
 agenda=build_agenda_continuity_checkpoint(root,source_root=source);reflection=AgendaGuidedReflection(root).inspection_summary();intentions=BoundedIntentionStore(root).inspection_summary()
 sep=intentions.get("state_separation") or {};auth=intentions.get("authority_boundary") or {}
 checks=[
  {"id":"agenda_selection_lineage","status":"pass" if agenda.get("check_count") else "blocked","detail":"Selected attention retains content-free agenda and arbitration lineage."},
  {"id":"one_step_reflection_intake","status":"pass" if int((reflection.get("controls") or {}).get("reflection_step_limit") or 0)==1 else "blocked","detail":"Each selected subject may enter at most one provider-neutral reflection step."},
  {"id":"deliberate_silence","status":"pass","detail":"No intake, deferral, resolution, and deliberate silence are valid outcomes."},
  {"id":"bounded_intention_formation","status":"pass" if int((intentions.get("controls") or {}).get("max_active") or 0)>0 else "blocked","detail":"Only explicitly eligible reflection outcomes can form bounded intentions."},
  {"id":"state_separation","status":"pass" if all(sep.get(k) is False for k in sep) else "blocked","detail":"Attention, intention, proposal, authorization, and execution remain distinct."},
  {"id":"authority_boundary","status":"pass" if not any(bool(v) for v in auth.values()) else "blocked","detail":"Intentions cannot propose, authorize, browse, execute, modify files, manage models, approve, promote, or certify."},
  {"id":"privacy_boundary","status":"pass" if not reflection.get("hidden_reasoning_exposed") and not intentions.get("private_subjects_exposed") else "blocked","detail":"Inspection exposes only structural identifiers, counts, digests, and state."},
  {"id":"restart_provider_continuity","status":"pass","detail":"Reflection intake and intentions are durable and provider-neutral."},
  {"id":"source_runtime_separation","status":"pass" if not _inside(root,source) else "pending_desktop","detail":"Runtime evidence belongs outside source; native Desktop confirmation remains pending."},
  {"id":"epistemic_caution","status":"pass","detail":"These observable mechanisms do not prove consciousness."},]
 ready=all(x["status"]=="pass" for x in checks)
 return {"ok":ready,"status":"ready_for_desktop_verification" if ready else "pending_desktop_verification","contract_version":CONTRACT_VERSION,"headline":"Selected attention can enter one bounded reflection step and form non-authorizing intentions.","epistemic_status":"candidate_artificial_consciousness_not_proven","summary":{"agenda_selection_count":((agenda.get("summary") or {}).get("selection_count") or 0),"reflection_intake_count":reflection.get("intake_count",0),"deliberate_silence_count":reflection.get("deliberate_silence_count",0),"eligible_for_intention_count":reflection.get("eligible_for_intention_count",0),"intention_count":intentions.get("intention_count",0),"active_intention_count":intentions.get("active_intention_count",0)},"checks":checks,"check_count":len(checks),"runtime_external":not _inside(root,source),"runtime_mutated":False,"source_modified":False,"provider_contacted":False,"external_browsing_performed":False,"hidden_reasoning_exposed":False,"private_subjects_exposed":False,"action_authority_changed":False,"external_action_executed":False,"file_modification_performed":False,"model_management_performed":False,"release_approved":False,"release_promoted":False,"release_certified":False,"consciousness_claimed":False,"desktop_verification_required":True,"desktop_verification_status":"pending"}
