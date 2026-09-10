from __future__ import annotations
"""Explicit operator-recorded v1089.1 reproducibility review."""
from datetime import datetime, timezone
import hashlib, json, re, uuid
from typing import Any, Mapping
from conversation_evaluation_finding import EvaluationFindingError, load_evaluation_finding_private, mutate_evaluation_finding

REPRODUCTION_OUTCOMES=("reproduced","not_reproduced","inconclusive","blocked")
REPRODUCTION_ENVIRONMENTS=("same_environment","clean_restart","provider_unavailable","alternate_provider","other")
MAX_REPRODUCTION_ATTEMPTS=24; MAX_ENVIRONMENT_LABEL_CHARS=160; MAX_REPRODUCTION_NOTE_CHARS=2000
_SHA=re.compile(r"^[a-fA-F0-9]{64}$")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def _digest(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def _bounded(v:str,m:int,label:str)->str:
 t=str(v or "").strip()
 if len(t)>m: raise EvaluationFindingError(f"{label} exceeds the {m}-character limit.")
 return t

def _public_attempt(row:Mapping[str,Any])->dict[str,Any]:
 label=str(row.get("private_environment_label") or ""); note=str(row.get("private_note") or "")
 return {"attempt_id":str(row.get("attempt_id") or ""),"recorded_at":str(row.get("recorded_at") or ""),"outcome":str(row.get("outcome") or "inconclusive"),"environment_kind":str(row.get("environment_kind") or "other"),"environment_label_present":bool(label),"environment_label_digest":_digest(label) if label else "","note_present":bool(note),"note_digest":_digest(note) if note else "","evidence_digest":str(row.get("evidence_digest") or "")}
def build_finding_reproducibility(finding_id:str)->dict[str,Any]:
 r=load_evaluation_finding_private(finding_id); rows=[x for x in list(r.get("reproduction_attempts") or []) if isinstance(x,Mapping)]; pub=[_public_attempt(x) for x in rows]; counts={k:0 for k in REPRODUCTION_OUTCOMES}
 for x in pub: counts[x["outcome"]]=counts.get(x["outcome"],0)+1
 if counts["reproduced"] and (counts["not_reproduced"] or counts["inconclusive"] or counts["blocked"]): status="mixed"
 elif counts["reproduced"]: status="confirmed"
 elif counts["not_reproduced"]: status="not_reproduced"
 elif rows: status="inconclusive"
 else: status="not_reviewed"
 return {"ok":True,"type":"desktop_alpha_evaluation_finding_reproducibility","finding_id":str(r.get("finding_id") or ""),"finding_revision":int(r.get("revision") or 0),"reproducibility_status":status,"attempt_count":len(pub),"maximum_attempts":MAX_REPRODUCTION_ATTEMPTS,"outcome_counts":counts,"attempts":pub,"attempts_digest":_digest(pub),"private_environment_labels_returned":False,"private_notes_returned":False,"operator_confirmation_required":True,"optimistic_revision_required":True,"automatic_rerun":False,"provider_invoked":False,"automatic_replay":False,"automatic_resend":False,"automatic_task_created":False,"patch_generated":False,"release_certified":False,"writes_state":False,"content_free":True,"redacted":True}
def record_reproduction_attempt(finding_id:str,*,outcome:str,environment_kind:str,environment_label:str="",note:str="",evidence_digest:str="",expected_revision:int|None,operator_confirmed:bool)->dict[str,Any]:
 out=str(outcome or "").strip().lower(); env=str(environment_kind or "").strip().lower()
 if out not in REPRODUCTION_OUTCOMES: raise EvaluationFindingError("Unsupported reproduction outcome.")
 if env not in REPRODUCTION_ENVIRONMENTS: raise EvaluationFindingError("Unsupported reproduction environment kind.")
 label=_bounded(environment_label,MAX_ENVIRONMENT_LABEL_CHARS,"Environment label"); private_note=_bounded(note,MAX_REPRODUCTION_NOTE_CHARS,"Reproduction note"); ed=str(evidence_digest or "").strip().lower()
 if ed and not _SHA.fullmatch(ed): raise EvaluationFindingError("Evidence digest must be a SHA-256 hexadecimal digest.")
 duplicate={"value":False}
 def apply(r):
  rows=[x for x in list(r.get("reproduction_attempts") or []) if isinstance(x,dict)]
  key=(out,env,label,private_note,ed)
  for x in rows:
   if (x.get("outcome"),x.get("environment_kind"),x.get("private_environment_label"),x.get("private_note"),x.get("evidence_digest"))==key: duplicate["value"]=True; raise _Idempotent
  if len(rows)>=MAX_REPRODUCTION_ATTEMPTS: raise EvaluationFindingError("The finding has reached the reproduction-attempt limit.")
  rows.append({"attempt_id":f"repro_attempt_{uuid.uuid4().hex[:16]}","recorded_at":_now(),"outcome":out,"environment_kind":env,"private_environment_label":label,"private_note":private_note,"evidence_digest":ed}); r["reproduction_attempts"]=rows
 class _Idempotent(Exception): pass
 try: summary=mutate_evaluation_finding(finding_id,expected_revision=expected_revision,operator_confirmed=operator_confirmed,mutator=apply)
 except _Idempotent:
  result=build_finding_reproducibility(finding_id); result["duplicate_attempt"]=True; return result
 result=build_finding_reproducibility(finding_id); result["duplicate_attempt"]=False; return result
def remove_reproduction_attempt(finding_id:str,attempt_id:str,*,expected_revision:int|None,operator_confirmed:bool)->dict[str,Any]:
 token=str(attempt_id or "").strip()
 def apply(r):
  rows=[x for x in list(r.get("reproduction_attempts") or []) if isinstance(x,dict)]; kept=[x for x in rows if str(x.get("attempt_id") or "")!=token]
  if len(kept)==len(rows): raise EvaluationFindingError("Reproduction attempt not found.")
  r["reproduction_attempts"]=kept
 mutate_evaluation_finding(finding_id,expected_revision=expected_revision,operator_confirmed=operator_confirmed,mutator=apply); return build_finding_reproducibility(finding_id)
