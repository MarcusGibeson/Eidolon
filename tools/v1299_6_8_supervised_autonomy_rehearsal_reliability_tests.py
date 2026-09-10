from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1299-test-'))
from supervised_autonomy_rehearsal import evaluate_supervised_rehearsal
from supervised_autonomy_rehearsal_reliability import audit_supervised_rehearsal
from supervised_autonomy_rehearsal_foundations import DENIED_AUTHORITY,digest
from v1299_test_support import identity,complete_steps,repair_checks
checks=[]
def req(v,n):checks.append(n);assert v,n
ident=identity();steps=complete_steps(ident);good=evaluate_supervised_rehearsal(ident,steps,repaired_consumer_checks=repair_checks());audit=audit_supervised_rehearsal(good);req(audit['ok'] and audit['status']=='supervised_autonomy_rehearsal_reliable','reliable');req(audit['operator_controls_preserved'],'controls_preserved');req(audit['native_windows_rehearsal_pending'],'native_pending')
# Replayed sequence/stage is rejected.
replay=[dict(x) for x in steps];replay[4]=dict(replay[3]);r=evaluate_supervised_rehearsal(ident,replay,repaired_consumer_checks=repair_checks());req(not r['ok'] and any(x.startswith('duplicate_sequence:') for x in r['integrity_violations']),'replay_blocked')
# Tampered sealed step is rejected.
tam=[dict(x) for x in steps];tam[5]['result']='forged';r2=evaluate_supervised_rehearsal(ident,tam,repaired_consumer_checks=repair_checks());req(not r2['ok'] and any(x.startswith('step_digest_mismatch:') for x in r2['integrity_violations']),'step_tamper_blocked')
# Source-lineage swap is rejected even if the row is resealed.
swap=[dict(x) for x in steps];row=swap[0];row['source_digest']=ident['repaired_source_digest'];payload={k:v for k,v in row.items() if k!='step_digest' and k not in DENIED_AUTHORITY};row['step_digest']=digest(payload);r3=evaluate_supervised_rehearsal(ident,swap,repaired_consumer_checks=repair_checks());req(not r3['ok'] and 'prebuild_source_mismatch:inspect' in r3['integrity_violations'],'source_lineage_blocked')
# Authority expansion is blocked even if a caller attempts to reseal around it.
auth=[dict(x) for x in steps];auth[2]['self_update_authorized']=True;r4=evaluate_supervised_rehearsal(ident,auth,repaired_consumer_checks=repair_checks());req(not r4['ok'] and any('step_authority_expansion' in x for x in r4['integrity_violations']),'authority_expansion_blocked')
# Portable code cannot self-attest Windows success.
native=evaluate_supervised_rehearsal(ident,steps,repaired_consumer_checks=repair_checks(),native_windows_status='passed');req(not native['ok'] and 'portable_rehearsal_cannot_self_attest_native_windows' in native['integrity_violations'],'native_false_pass_blocked')
# Reliability audit catches post-evaluation tamper.
tg=dict(good);tg['generic_authorization_phrase_is_sufficient']=True;ta=audit_supervised_rehearsal(tg);req(not ta['ok'] and 'generic_authorization_expansion' in ta['findings'],'generic_auth_tamper_blocked')
td=dict(good);td['status']='forged';ta2=audit_supervised_rehearsal(td);req(not ta2['ok'] and 'rehearsal_digest_mismatch' in ta2['findings'],'result_digest_tamper_blocked')
req(not any(audit[k] for k in DENIED_AUTHORITY),'audit_no_authority')
print(json.dumps({'suite':'v1299.6-v1299.8-supervised-autonomy-rehearsal-reliability','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
