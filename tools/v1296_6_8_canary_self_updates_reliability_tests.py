from __future__ import annotations
import hashlib,json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1296-'))
from canary_self_updates_foundations import *
from canary_self_updates import evaluate_canary
from canary_self_updates_reliability import *
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
def d(x):return hashlib.sha256(str(x).encode()).hexdigest()
i=seal_canary_identity(update_id='selfupdate_'+('c'*24),baseline_source_digest=d('b'),candidate_source_digest=d('c'),update_packet_digest=d('u'),review_decision_digest=d('r'),baseline_workspace_digest=d('bw'),candidate_workspace_digest=d('cw'))
def rows(role):return [canary_observation(i,role=role,signal=s,status='passed',evidence_digest=d((role,s)),quality_score=.95,latency_ms=10) for s in MANDATORY_SIGNALS]
r=evaluate_canary(i,rows('baseline'),rows('candidate'));a=audit_canary_result(r);req(a['ok'],'audit_good');req(r['status']=='portable_canary_ready_native_pending','pending')
tampered={**r,'active_replacement_performed':True};req(not audit_canary_result(tampered)['ok'],'replacement_claim');tampered={**r,'self_update_authorized':True};req(not audit_canary_result(tampered)['ok'],'authority');tampered={**r,'requires_separate_v1269_exact_authorization':False};req(not audit_canary_result(tampered)['ok'],'auth_boundary');tampered={**r,'status':'canary_ready_for_operator_replacement_review'};req(not audit_canary_result(tampered)['ok'],'native_false_ready')
stale=rows('candidate');stale[0]={**stale[0],'fresh':False};req(evaluate_canary(i,rows('baseline'),stale)['status']=='canary_integrity_blocked','stale');fail=rows('candidate');fail[0]={**fail[0],'status':'failed'};req(evaluate_canary(i,rows('baseline'),fail)['status']=='canary_failed','failure');dup=rows('candidate')+[rows('candidate')[0]];req(evaluate_canary(i,rows('baseline'),dup)['status']=='canary_integrity_blocked','duplicate')
h=inspect_canary_surface_health(source_root=ROOT);req(h['ok'],'surface');req(h['native_windows_validation']=='desktop_review_required','native_handoff');req(not any(h[k] for k in DENIED_AUTHORITY),'surface_authority');req(CONTRACT_VERSION=='v1296.8','version')
print(json.dumps({'suite':'v1296.6-v1296.8-canary-self-updates-reliability','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
