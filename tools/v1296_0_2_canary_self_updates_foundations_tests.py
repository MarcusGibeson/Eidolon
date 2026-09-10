from __future__ import annotations
import hashlib,json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1296-'))
from canary_self_updates_foundations import *
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
def d(x):return hashlib.sha256(str(x).encode()).hexdigest()
i=seal_canary_identity(update_id='selfupdate_'+('a'*24),baseline_source_digest=d('b'),candidate_source_digest=d('c'),update_packet_digest=d('u'),review_decision_digest=d('r'),baseline_workspace_digest=d('bw'),candidate_workspace_digest=d('cw'))
req(i['canary_id'].startswith('canary_'),'id');req(valid_digest(i['identity_digest']),'digest');req(i['baseline_workspace_digest']!=i['candidate_workspace_digest'],'isolation');req(i['observation_budget']>=16,'budget');req(not any(i[k] for k in DENIED_AUTHORITY),'authority')
o=canary_observation(i,role='candidate',signal='startup',status='passed',evidence_digest=d('e'),quality_score=.9,latency_ms=10);req(o['status']=='passed' and o['fresh'],'obs');req(valid_digest(o['observation_digest']),'obs_digest')
for kwargs in [dict(update_id='bad',baseline_source_digest=d('b'),candidate_source_digest=d('c'),update_packet_digest=d('u'),review_decision_digest=d('r'),baseline_workspace_digest=d('bw'),candidate_workspace_digest=d('cw')),dict(update_id='selfupdate_'+('a'*24),baseline_source_digest=d('b'),candidate_source_digest=d('b'),update_packet_digest=d('u'),review_decision_digest=d('r'),baseline_workspace_digest=d('bw'),candidate_workspace_digest=d('cw')),dict(update_id='selfupdate_'+('a'*24),baseline_source_digest=d('b'),candidate_source_digest=d('c'),update_packet_digest=d('u'),review_decision_digest=d('r'),baseline_workspace_digest=d('same'),candidate_workspace_digest=d('same'))]:
    try:seal_canary_identity(**kwargs);bad=False
    except ValueError:bad=True
    req(bad,'bad_identity_rejected')
try:canary_observation(i,role='candidate',signal=NATIVE_SIGNAL,status='passed',evidence_digest=d('n'),platform_name='linux',native_attested=True);bad=False
except ValueError:bad=True
req(bad,'false_native_pass_rejected')
n=canary_observation(i,role='candidate',signal=NATIVE_SIGNAL,status='passed',evidence_digest=d('nw'),platform_name='windows',native_attested=True);req(n['native_attested'],'native_attested')
req(set(MANDATORY_SIGNALS)>= {'startup','verification','runtime_isolation','privacy_security'},'signals');req(CONTRACT_VERSION=='v1296.2','version')
print(json.dumps({'suite':'v1296.0-v1296.2-canary-self-updates-foundations','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
