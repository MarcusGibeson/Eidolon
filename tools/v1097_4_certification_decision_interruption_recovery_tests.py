from __future__ import annotations
import json, tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'):
    sys.path.insert(0,str(item))
from v1097_bundle_a_test_support import prepare_promoted_fixture,evidence_payload,write_evidence
from release_certification_evidence import select_certification_evidence,create_certification_readiness_preview,certification_directory
from release_certification_plan import create_certification_plan,preview_certification_authorization
from release_certification_transaction import apply_authorized_certification,CERTIFICATION_APPLY_CONFIRMATION,certification_status
from release_certification_recovery import certification_recovery_status,preview_certification_recovery,resume_certification_decision,CERTIFICATION_RECOVERY_CONFIRMATION
from release_candidate_identity import read_json,atomic_json

def c(name,ok): return {'name':name,'ok':bool(ok)}
def prepare(base,decision='auto'):
    f=prepare_promoted_fixture(base)
    for scope in ('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'):
        select_certification_evidence(write_evidence(base/'evidence'/f'{scope}.json',evidence_payload(f,scope)),runtime_root=f['handoff_runtime'])
    create_certification_readiness_preview(runtime_root=f['handoff_runtime'])
    create_certification_plan(decision,runtime_root=f['handoff_runtime'])
    auth=preview_certification_authorization(runtime_root=f['handoff_runtime'])
    return f,auth

def main():
    rows=[]
    for point in ('before_event_persistence','after_event_persistence','after_receipt','after_scope_state','after_promotion_authority'):
        with tempfile.TemporaryDirectory(prefix=f'eidolon-v1097-4-{point}-') as td:
            base=Path(td);f,auth=prepare(base)
            interrupted=apply_authorized_certification(auth['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'],_interrupt_at=point)
            status=certification_recovery_status(runtime_root=f['handoff_runtime'])
            preview=preview_certification_recovery(runtime_root=f['handoff_runtime'])
            wrong=resume_certification_decision(preview.get('authorization_token',''),confirm='true',runtime_root=f['handoff_runtime'])
            resumed=resume_certification_decision(preview.get('authorization_token',''),confirm=CERTIFICATION_RECOVERY_CONFIRMATION,runtime_root=f['handoff_runtime'])
            stable=certification_status(runtime_root=f['handoff_runtime'])
            replay=resume_certification_decision(preview.get('authorization_token',''),confirm=CERTIFICATION_RECOVERY_CONFIRMATION,runtime_root=f['handoff_runtime'])
            rows += [
                c(f'{point}-interrupted',interrupted.get('status')=='certification_interrupted'),
                c(f'{point}-preview-exact',status.get('recovery_available') and preview.get('status')=='certification_recovery_previewed'),
                c(f'{point}-literal-confirmation',not wrong.get('ok')),
                c(f'{point}-resumed',resumed.get('ok') and stable.get('general_release_certified')),
                c(f'{point}-single-use',not replay.get('ok')),
            ]
    with tempfile.TemporaryDirectory(prefix='eidolon-v1097-4-corrupt-') as td:
        base=Path(td);f,auth=prepare(base)
        interrupted=apply_authorized_certification(auth['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'],_interrupt_at='after_receipt')
        receipt=certification_directory(f['handoff_runtime'])/'receipts'/f"{interrupted['certification_transaction_id']}.json"
        row=read_json(receipt);row['decision']='declined';atomic_json(receipt,row)
        status=certification_recovery_status(runtime_root=f['handoff_runtime'])
        rows += [c('corrupt-receipt-uncertain',not status.get('ok') and status.get('status')=='certification_recovery_uncertain'),c('corrupt-receipt-no-recovery',not preview_certification_recovery(runtime_root=f['handoff_runtime']).get('ok'))]
    with tempfile.TemporaryDirectory(prefix='eidolon-v1097-4-cross-') as td1, tempfile.TemporaryDirectory(prefix='eidolon-v1097-4-cross2-') as td2:
        f1,a1=prepare(Path(td1));apply_authorized_certification(a1['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f1['handoff_runtime'],_interrupt_at='after_event_persistence');token=preview_certification_recovery(runtime_root=f1['handoff_runtime'])['authorization_token']
        f2,a2=prepare(Path(td2));apply_authorized_certification(a2['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f2['handoff_runtime'],_interrupt_at='after_event_persistence')
        cross=resume_certification_decision(token,confirm=CERTIFICATION_RECOVERY_CONFIRMATION,runtime_root=f2['handoff_runtime'])
        malformed=resume_certification_decision('true',confirm=CERTIFICATION_RECOVERY_CONFIRMATION,runtime_root=f1['handoff_runtime'])
        rows += [c('cross-runtime-token-rejected',not cross.get('ok')),c('malformed-token-rejected',not malformed.get('ok'))]
    with tempfile.TemporaryDirectory(prefix='eidolon-v1097-4-complete-') as td:
        f,a=prepare(Path(td));out=apply_authorized_certification(a['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']);status=certification_recovery_status(runtime_root=f['handoff_runtime']);rows += [c('completed-idempotent',out.get('ok') and status.get('status')=='certification_decision_complete'),c('completed-not-recoverable',not status.get('recovery_available') and not preview_certification_recovery(runtime_root=f['handoff_runtime']).get('ok'))]
    report={'suite':'v1097.4-certification-decision-interruption-recovery','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
