from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1300-test-'))
from supervised_self_development_beta import evaluate_supervised_self_development_beta
from supervised_self_development_beta_reliability import audit_supervised_self_development_beta
from supervised_self_development_beta_foundations import DENIED_AUTHORITY,digest
from v1300_test_support import identity,steps,update_evidence,recovery_evidence
checks=[]
def req(v,n):checks.append(n);assert v,n
i=identity();s=steps(i);u=update_evidence();r=recovery_evidence();good=evaluate_supervised_self_development_beta(i,s,update_evidence=u,recovery_evidence=r);audit=audit_supervised_self_development_beta(good);req(audit['ok'] and audit['status']=='supervised_self_development_beta_reliable','reliable');req(audit['roadmap_complete_through_v1300'],'complete');req(audit['native_windows_beta_validation_pending'],'native_pending')
missing=evaluate_supervised_self_development_beta(i,s[:-1],update_evidence=u,recovery_evidence=r);req(not missing['ok'] and 'incomplete_beta_stage_set' in missing['integrity_violations'],'missing_stage')
tam=[dict(x) for x in s];tam[6]['result']='forged';x=evaluate_supervised_self_development_beta(i,tam,update_evidence=u,recovery_evidence=r);req(not x['ok'] and any(v.startswith('step_digest_mismatch:') for v in x['integrity_violations']),'step_tamper')
badu=dict(u);badu['generic_authorization_rejected']=False;x=evaluate_supervised_self_development_beta(i,s,update_evidence=badu,recovery_evidence=r);req(not x['ok'] and 'update_evidence_invalid:generic_authorization_rejected' in x['integrity_violations'],'generic_false_pass')
badu=dict(u);badu['exact_authorization_consumed']=False;x=evaluate_supervised_self_development_beta(i,s,update_evidence=badu,recovery_evidence=r);req(not x['ok'] and 'update_evidence_invalid:exact_authorization_consumed' in x['integrity_violations'],'exact_auth_required')
badr=dict(r);badr['automatic_recovery_completed']=False;x=evaluate_supervised_self_development_beta(i,s,update_evidence=u,recovery_evidence=badr);req(not x['ok'] and 'recovery_evidence_invalid:automatic_recovery_completed' in x['integrity_violations'],'recovery_required')
native=evaluate_supervised_self_development_beta(i,s,update_evidence=u,recovery_evidence=r,native_windows_status='passed');req(not native['ok'] and 'portable_beta_cannot_self_attest_native_windows' in native['integrity_violations'],'native_false_pass')
tg=dict(good);tg['generic_authorization_phrase_is_sufficient']=True;ta=audit_supervised_self_development_beta(tg);req(not ta['ok'] and 'generic_authorization_expansion' in ta['findings'],'audit_generic_tamper')
td=dict(good);td['status']='forged';ta=audit_supervised_self_development_beta(td);req(not ta['ok'] and 'beta_digest_mismatch' in ta['findings'],'audit_digest_tamper');req(not any(audit[k] for k in DENIED_AUTHORITY),'audit_no_authority')
print(json.dumps({'suite':'v1300.6-v1300.8-supervised-self-development-beta-reliability','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
