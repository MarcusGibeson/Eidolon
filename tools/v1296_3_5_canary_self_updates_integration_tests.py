from __future__ import annotations
import hashlib,json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1296-'))
from canary_self_updates_foundations import *
from canary_self_updates import evaluate_canary
from v1296_test_support import run_fixture,d
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
base=run_fixture('baseline');cand=run_fixture('candidate');req(base['returncode']==cand['returncode']==0,'fixture_process');req(base['workspace_digest']!=cand['workspace_digest'],'fixture_isolated')
i=seal_canary_identity(update_id='selfupdate_'+('b'*24),baseline_source_digest=d('src-base'),candidate_source_digest=d('src-cand'),update_packet_digest=d('packet'),review_decision_digest=d('review'),baseline_workspace_digest=str(base['workspace_digest']),candidate_workspace_digest=str(cand['workspace_digest']))
def rows(role,fixture,native=False):
 out=[]
 for s in MANDATORY_SIGNALS:
  out.append(canary_observation(i,role=role,signal=s,status='passed',evidence_digest=d((role,s,fixture['evidence_digest'])),quality_score=float(fixture['quality']),latency_ms=float(fixture['latency']) if s in {'startup','conversation_smoke'} else 0))
 if native:out.append(canary_observation(i,role=role,signal=NATIVE_SIGNAL,status='passed',evidence_digest=d((role,'native')),platform_name='windows',native_attested=True))
 return out
b=rows('baseline',base);c=rows('candidate',cand);r=evaluate_canary(i,b,c);req(r['status']=='portable_canary_ready_native_pending','portable_pending');req(r['portable_canary_passed'] and not r['native_windows_canary_passed'],'portable_truth');req(not r['ok'],'native_required');req(not r['active_replacement_performed'],'no_apply')
r2=evaluate_canary(i,rows('baseline',base,True),rows('candidate',cand,True));req(r2['ok'] and r2['status']=='canary_ready_for_operator_replacement_review','native_ready');req(r2['requires_separate_v1269_exact_authorization'],'separate_auth')
bad=run_fixture('candidate',regression=True);r3=evaluate_canary(i,b,rows('candidate',bad));req(r3['status']=='canary_regression_detected','regression');req(bool(r3['regressions']),'regression_evidence')
missing=evaluate_canary(i,b,c[:-1]);req(missing['status']=='canary_integrity_blocked','missing_blocked');req(any('missing_observation' in x for x in missing['integrity_violations']),'missing_named')
leak=list(c);leak[0]={**leak[0],'private_finding_count':1};r4=evaluate_canary(i,b,leak);req(r4['status']=='canary_integrity_blocked','private_blocked')
shared=list(c);shared[1]={**shared[1],'shared_mutable_runtime':True};r5=evaluate_canary(i,b,shared);req(r5['status']=='canary_integrity_blocked','shared_blocked')
print(json.dumps({'suite':'v1296.3-v1296.5-canary-self-updates-integration','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
