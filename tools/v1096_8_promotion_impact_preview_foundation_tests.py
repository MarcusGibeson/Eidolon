from __future__ import annotations
import json, os, tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent')); sys.path.insert(0,str(ROOT/'tools'))
from v1096_bundle_c_test_support import prepare_staged_fixture, snapshot_files
from release_installation_transaction import INSTALLATION_APPLY_CONFIRMATION, apply_authorized_installation, preview_installation_apply_authorization, transaction_directory
from release_candidate_identity import atomic_json, read_json
from release_promotion_preview import create_promotion_impact_preview, promotion_preview_status, promotion_directory
from api_server import ApiError, handle_api_get

def check(name, ok): return {'name':name,'ok':bool(ok)}

def install(f):
    auth=preview_installation_apply_authorization(runtime_root=f['handoff_runtime'])
    return apply_authorized_installation(str(auth.get('authorization_token') or ''),confirm=INSTALLATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'])

def main():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='eidolon-v1096-8-') as td:
        f=prepare_staged_fixture(Path(td)); installed=install(f); before=snapshot_files(f['target'])
        preview=create_promotion_impact_preview(runtime_root=f['handoff_runtime']); after=snapshot_files(f['target']); status=promotion_preview_status(runtime_root=f['handoff_runtime'])
        rows += [
            check('installed-unpromoted-required', installed.get('ok') and installed.get('status')=='installed_unpromoted'),
            check('promotion-preview-created', preview.get('ok') and preview.get('status')=='promotion_previewed'),
            check('promotion-preview-bound', all(preview.get(k) for k in ('preview_binding_sha256','transaction_identity_sha256','installed_receipt_sha256','candidate_id','archive_sha256','source_manifest_sha256','archive_manifest_sha256','target_inventory_sha256','effects_sha256'))),
            check('metadata-only-effects', preview.get('metadata_effect_count')==3 and preview.get('source_file_effect_count')==0),
            check('target-source-unchanged', before==after and not preview.get('source_files_mutated')),
            check('no-promotion-or-certification', not preview.get('promotion_applied') and not preview.get('certified')),
            check('status-revalidates', status.get('ok') and status.get('status')=='promotion_previewed'),
        ]
        public=json.dumps(preview,sort_keys=True)
        rows.append(check('paths-suppressed', str(f['target']) not in public and str(f['archive']) not in public and preview.get('content_free')))
        txp=read_json(transaction_directory(f['handoff_runtime'])/'active_installed_receipt.json'); txid=txp['transaction_id']
        rp=transaction_directory(f['handoff_runtime'])/'installed_receipts'/f'{txid}.json'; receipt=read_json(rp); receipt['candidate_id']='tampered'; atomic_json(rp,receipt)
        stale=promotion_preview_status(runtime_root=f['handoff_runtime'])
        rows.append(check('receipt-drift-detected', not stale.get('ok') and stale.get('status')=='promotion_preview_stale'))
    with tempfile.TemporaryDirectory(prefix='eidolon-v1096-8-noinstall-') as td:
        f=prepare_staged_fixture(Path(td)); blocked=create_promotion_impact_preview(runtime_root=f['handoff_runtime'])
        rows.append(check('staging-not-promotion', not blocked.get('ok') and blocked.get('status')=='promotion_preview_blocked'))
    with tempfile.TemporaryDirectory(prefix='eidolon-v1096-8-targetdrift-') as td:
        f=prepare_staged_fixture(Path(td)); install(f); create_promotion_impact_preview(runtime_root=f['handoff_runtime']); (f['target']/'README.md').write_text('drift\n',encoding='utf-8'); stale=promotion_preview_status(runtime_root=f['handoff_runtime'])
        rows.append(check('target-drift-detected', not stale.get('ok') and stale.get('status')=='promotion_preview_stale'))
    previous=os.environ.get('EIDOLON_DATA_DIR')
    with tempfile.TemporaryDirectory(prefix='eidolon-v1096-8-api-') as td:
        os.environ['EIDOLON_DATA_DIR']=td
        code,payload=handle_api_get('/api/release-promotion/preview/status')
        rows.append(check('api-read-only-status', code==200 and payload.get('data',{}).get('status')=='not_previewed'))
        try: handle_api_get('/api/release-promotion/preview/create'); rejected=False
        except ApiError as e: rejected=e.status==404
        rows.append(check('mutation-not-get', rejected))
    if previous is None: os.environ.pop('EIDOLON_DATA_DIR',None)
    else: os.environ['EIDOLON_DATA_DIR']=previous
    report={'suite':'v1096.8-promotion-impact-preview-foundation','passed':sum(r['ok'] for r in rows),'failed':sum(not r['ok'] for r in rows),'checks':rows}; report['ok']=report['failed']==0
    print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
