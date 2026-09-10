from __future__ import annotations
import json,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1097_bundle_a_test_support import prepare_promoted_fixture,evidence_payload,write_evidence
from release_certification_evidence import select_certification_evidence,create_certification_readiness_preview,certification_directory
from release_certification_plan import create_certification_plan,preview_certification_authorization
from release_certification_transaction import *
from release_installed_state import installed_state_status
from release_promotion_transaction import preview_promotion_reversal
from api_server import ApiError,handle_api_get

def c(n,o):return {'name':n,'ok':bool(o)}
def populate(base,f,scopes):
 for scope in scopes:select_certification_evidence(write_evidence(base/'evidence'/f'{scope}.json',evidence_payload(f,scope)),runtime_root=f['handoff_runtime'])
def authorize(base,f,decision='auto',scope='general_release'):
 create_certification_readiness_preview(scope,runtime_root=f['handoff_runtime']);create_certification_plan(decision,runtime_root=f['handoff_runtime']);return preview_certification_authorization(runtime_root=f['handoff_runtime'])

def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-3-cert-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);before={p.relative_to(f['target']).as_posix():p.read_bytes() for p in f['target'].rglob('*') if p.is_file()};populate(base,f,('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'));auth=authorize(base,f);wrong=apply_authorized_certification(auth['authorization_token'],confirm='true',runtime_root=f['handoff_runtime']);applied=apply_authorized_certification(auth['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']);status=certification_status(runtime_root=f['handoff_runtime']);installed=installed_state_status(runtime_root=f['handoff_runtime']);reused=apply_authorized_certification(auth['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']);after={p.relative_to(f['target']).as_posix():p.read_bytes() for p in f['target'].rglob('*') if p.is_file()}
  rows += [c('literal-confirmation-required',not wrong.get('ok')),c('general-release-certified',applied.get('ok') and applied.get('status')=='scope_certified' and applied.get('general_release_certified')),c('exact-receipt-state-bound',all(applied.get(k) for k in ('certification_transaction_identity_sha256','certification_receipt_sha256','certification_state_sha256','candidate_id','archive_sha256','installed_receipt_sha256','promotion_receipt_sha256'))),c('authority-status-stable',status.get('ok') and status.get('status')=='scope_certified' and status.get('general_release_certified')),c('installed-state-certified',installed.get('ok') and installed.get('status')=='certified'),c('source-unchanged',before==after and not applied.get('source_files_mutated')),c('apply-token-single-use',not reused.get('ok') and reused.get('status')=='authorization_reused'),c('promotion-reversal-blocked',not preview_promotion_reversal(runtime_root=f['handoff_runtime']).get('ok'))]
  import os
  previous=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(f['handoff_runtime'])
  code,payload=handle_api_get('/api/release-certification/status');rows.append(c('api-certification-status',code==200 and payload.get('data',{}).get('general_release_certified')))
  try:handle_api_get('/api/release-certification/decision/apply');rejected=False
  except ApiError as exc:rejected=exc.status==404
  rows.append(c('decision-mutations-post-only',rejected))
  if previous is None:os.environ.pop('EIDOLON_DATA_DIR',None)
  else:os.environ['EIDOLON_DATA_DIR']=previous
  event_path=certification_directory(f['handoff_runtime'])/'events'/f"{applied['certification_transaction_id']}.jsonl";events=[json.loads(x) for x in event_path.read_text().splitlines()];rows.append(c('append-only-events',[x['sequence'] for x in events]==list(range(1,len(events)+1)) and len(events)>=3))
  revp=preview_certification_revocation('general_release',runtime_root=f['handoff_runtime']);rev=revoke_certification_scope(revp['authorization_token'],confirm=CERTIFICATION_REVOCATION_CONFIRMATION,runtime_root=f['handoff_runtime']);rev_status=certification_status(runtime_root=f['handoff_runtime']);reuse_rev=revoke_certification_scope(revp['authorization_token'],confirm=CERTIFICATION_REVOCATION_CONFIRMATION,runtime_root=f['handoff_runtime']);rows += [c('revocation-preview-bound',revp.get('ok') and revp.get('status')=='certification_revocation_previewed'),c('scope-revoked',rev.get('ok') and rev.get('status')=='certification_revoked'),c('revocation-stable',rev_status.get('ok') and rev_status.get('status')=='certification_revoked'),c('revocation-single-use',not reuse_rev.get('ok'))]
  # Re-select current evidence after revocation, then certify again; history is superseded, not deleted.
  populate(base,f,('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'));auth2=authorize(base,f);again=apply_authorized_certification(auth2['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']);receipt=json.loads((certification_directory(f['handoff_runtime'])/'receipts'/f"{again['certification_transaction_id']}.json").read_text());rows.append(c('supersession-preserves-history',again.get('ok') and bool(receipt.get('supersedes_receipt_sha256')) and event_path.is_file()))
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-3-insufficient-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);auth=authorize(base,f);out=apply_authorized_certification(auth['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']);rows.append(c('insufficient-never-certified',out.get('ok') and out.get('status')=='insufficient_evidence' and not out.get('scope_certified')))
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-3-decline-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);populate(base,f,('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'));auth=authorize(base,f,'declined');out=apply_authorized_certification(auth['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']);rows.append(c('decline-recorded-not-certified',out.get('ok') and out.get('status')=='certification_declined' and not out.get('scope_certified')))
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-3-native-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);payload=evidence_payload(f,'native_windows_behavior',environment={'os':'windows','native':True},producer='eidolon-native-windows-verifier');select_certification_evidence(write_evidence(base/'native.json',payload),runtime_root=f['handoff_runtime']);auth=authorize(base,f,scope='native_windows');out=apply_authorized_certification(auth['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']);rows += [c('native-scope-certified',out.get('ok') and 'native_windows' in out.get('certified_scopes',[])),c('native-does-not-certify-general',not out.get('general_release_certified'))]
 report={'suite':'v1097.3-certification-decision-release-authority-coherence','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
