from __future__ import annotations
from datetime import datetime,timedelta,timezone
import json,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'): sys.path.insert(0,str(item))
from v1097_bundle_a_test_support import prepare_promoted_fixture,evidence_payload,write_evidence
from release_certification_evidence import select_certification_evidence,create_certification_readiness_preview,certification_directory
from release_certification_plan import create_certification_plan,preview_certification_authorization
from release_certification_transaction import apply_authorized_certification,CERTIFICATION_APPLY_CONFIRMATION,certification_status
from release_certification_freshness import *
from release_candidate_identity import read_json,atomic_json

def c(n,o): return {'name':n,'ok':bool(o)}
def populate(base,f):
    paths={}
    for scope in ('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'):
        p=write_evidence(base/'evidence'/f'{scope}.json',evidence_payload(f,scope)); paths[scope]=p
        select_certification_evidence(p,runtime_root=f['handoff_runtime'])
    return paths

def certify(f):
    create_certification_readiness_preview(runtime_root=f['handoff_runtime']);create_certification_plan(runtime_root=f['handoff_runtime']);a=preview_certification_authorization(runtime_root=f['handoff_runtime']);return apply_authorized_certification(a['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'])

def main():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='eidolon-v1097-5-') as td:
        base=Path(td);f=prepare_promoted_fixture(base);paths=populate(base,f);cert=certify(f)
        fresh=evidence_freshness_status(runtime_root=f['handoff_runtime'])
        rows += [c('fresh-evidence-detected',fresh.get('ok') and fresh.get('fresh_scope_count')==4),c('certification-preserved',certification_status(runtime_root=f['handoff_runtime']).get('general_release_certified'))]
        # Expire one exact selected artifact through its preserved payload and valid record digest.
        d=certification_directory(f['handoff_runtime']);idx=read_json(d/'evidence_index.json');target=None
        for eid in idx['evidence_ids']:
            rec=read_json(d/'evidence'/f'{eid}.json')
            if rec.get('scope')=='startup_daily_use': target=(eid,rec);break
        target[1]['payload']['expires_at']=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat();target[1]['record_sha256']='';target[1]['record_sha256']=__import__('release_certification_evidence')._record_digest(target[1]);atomic_json(d/'evidence'/f'{target[0]}.json',target[1])
        expired=evidence_freshness_status(runtime_root=f['handoff_runtime']);recert=create_recertification_readiness_preview(runtime_root=f['handoff_runtime'])
        rows += [c('expiry-detected','startup_daily_use' in expired.get('expired_scopes',[])),c('recertification-preview-required',recert.get('recertification_required') and not recert.get('ready_to_recertify')),c('expiry-does-not-auto-revoke',certification_status(runtime_root=f['handoff_runtime']).get('general_release_certified'))]
        replacement_payload=evidence_payload(f,'startup_daily_use'); replacement_payload['expires_at']=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat()
        preview=preview_evidence_replacement(write_evidence(base/'replacement.json',replacement_payload),'startup_daily_use',runtime_root=f['handoff_runtime'])
        before=evidence_freshness_status(runtime_root=f['handoff_runtime'])
        wrong=replace_certification_evidence(preview.get('authorization_token',''),confirm='true',runtime_root=f['handoff_runtime'])
        applied=replace_certification_evidence(preview.get('authorization_token',''),confirm=EVIDENCE_REPLACEMENT_CONFIRMATION,runtime_root=f['handoff_runtime'])
        after=evidence_freshness_status(runtime_root=f['handoff_runtime']);ready=create_recertification_readiness_preview(runtime_root=f['handoff_runtime']);reused=replace_certification_evidence(preview.get('authorization_token',''),confirm=EVIDENCE_REPLACEMENT_CONFIRMATION,runtime_root=f['handoff_runtime'])
        rows += [c('replacement-preview-first',preview.get('ok') and 'startup_daily_use' in before.get('expired_scopes',[])),c('replacement-literal-confirmation',not wrong.get('ok')),c('replacement-applied',applied.get('ok') and applied.get('status')=='evidence_replaced'),c('replacement-restores-freshness','startup_daily_use' in after.get('fresh_scopes',[])),c('replacement-token-single-use',not reused.get('ok')),c('ready-to-recertify-after-replacement',ready.get('ready_to_recertify')),c('replacement-does-not-auto-recertify',certification_status(runtime_root=f['handoff_runtime']).get('general_release_certified'))]
        bad=preview_evidence_replacement(base/'missing.json','startup_daily_use',runtime_root=f['handoff_runtime']);stable=evidence_freshness_status(runtime_root=f['handoff_runtime']);rows += [c('failed-replacement-blocked',not bad.get('ok')),c('failed-replacement-preserves-active','startup_daily_use' in stable.get('fresh_scopes',[]))]
        # Policy changes are read-only recertification signals.
        policy={'schema':'eidolon-certification-evidence-freshness-policy-v1','version':'test-new','max_age_days':{'source_package_integrity':1,'startup_daily_use':1,'installation_recovery':1,'promotion_behavior':1},'explicit_expiry_required':False,'scope_implication_allowed':False};atomic_json(d/'freshness_policy.json',policy);policy_preview=create_recertification_readiness_preview(runtime_root=f['handoff_runtime']);rows += [c('policy-change-previewed',policy_preview.get('recertification_required')),c('policy-change-no-auto-decision',certification_status(runtime_root=f['handoff_runtime']).get('general_release_certified'))]
    with tempfile.TemporaryDirectory(prefix='eidolon-v1097-5-scope-') as td:
        base=Path(td);f=prepare_promoted_fixture(base);payload=evidence_payload(f,'native_windows_behavior',environment={'os':'windows','native':True},producer='eidolon-native-windows-verifier');select_certification_evidence(write_evidence(base/'native.json',payload),runtime_root=f['handoff_runtime']);native=create_recertification_readiness_preview('native_windows',runtime_root=f['handoff_runtime']);rows += [c('scope-independent',native.get('certification_scope')=='native_windows' and not native.get('ready_to_recertify') is False or native.get('scope')=='native_windows'),c('native-does-not-imply-general',not native.get('certification_changed'))]
    report={'suite':'v1097.5-evidence-freshness-replacement-recertification-preview','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
