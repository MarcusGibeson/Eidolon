from __future__ import annotations
import json, os, tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'): sys.path.insert(0,str(item))
from v1097_bundle_c_test_support import prepare_certified_fixture
from v1097_bundle_a_test_support import prepare_promoted_fixture
from release_certification_history import create_certification_history_reconciliation_preview
from release_certification_policy import select_certification_policy,create_policy_migration_preview,BUILTIN_POLICY_ID
from release_authority_readiness import create_release_authority_readiness_preview,release_authority_readiness_status,release_authority_readiness_directory
from release_certification_coherence import preview_operation_claim,claim_operation,release_operation,OPERATION_CLAIM_CONFIRMATION,OPERATION_RELEASE_CONFIRMATION
from api_server import handle_api_get,handle_api_post,ApiError
from dashboard import render_release_certification

def c(name,ok): return {'name':name,'ok':bool(ok)}
def prepare(base:Path):
 f=prepare_certified_fixture(base); rr=Path(f['handoff_runtime'])
 assert create_certification_history_reconciliation_preview(runtime_root=rr).get('ok')
 assert select_certification_policy(built_in_policy_id=BUILTIN_POLICY_ID,runtime_root=rr).get('ok')
 assert create_policy_migration_preview(runtime_root=rr).get('ok')
 return f,rr

def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1098-0-') as td:
  base=Path(td); f,rr=prepare(base); target=Path(f['target']); before={p.relative_to(target).as_posix():p.read_bytes() for p in target.rglob('*') if p.is_file()}
  preview=create_release_authority_readiness_preview(runtime_root=rr); status=release_authority_readiness_status(runtime_root=rr)
  rows += [c('readiness-created',preview.get('ok') and preview.get('status')=='release_authority_ready'),c('readiness-current',status.get('ok') and status.get('status')=='release_authority_ready'),c('exact-candidate-bound',status.get('candidate_id') and status.get('source_manifest_sha256') and status.get('archive_manifest_sha256') and status.get('archive_sha256')),c('installation-bound',status.get('installation_transaction_id') and status.get('installed_receipt_sha256') and status.get('installed')),c('promotion-bound',status.get('promotion_transaction_id') and status.get('promotion_receipt_sha256') and status.get('promoted_release_authority')),c('certification-bound',status.get('certification_transaction_id') and status.get('certification_receipt_sha256') and status.get('general_release_certified')),c('history-policy-bound',status.get('history_sha256') and status.get('policy_sha256') and status.get('migration_preview_sha256')),c('runtime-root-bound',status.get('runtime_root_identity_sha256'))]
  rows += [c('scope-separated',status.get('general_release_certified') and not status.get('native_windows_certified') and not status.get('provider_ollama_certified') and not status.get('model_specific_certified')),c('no-authority-inference',not status.get('installation_inferred') and not status.get('promotion_inferred') and not status.get('general_release_certification_inferred') and not status.get('native_windows_inferred') and not status.get('provider_ollama_inferred') and not status.get('model_specific_inferred'))]
  scopes={x['scope']:x for x in status.get('scope_statuses',[])}; rows += [c('scope-rows-complete',set(scopes)=={'general_release','native_windows','provider_ollama','model_specific'}),c('general-only-certified',scopes['general_release']['certified'] and not scopes['native_windows']['certified'])]
  current={p.relative_to(target).as_posix():p.read_bytes() for p in target.rglob('*') if p.is_file()}; rows += [c('target-unchanged',before==current),c('read-only-flags',status.get('read_only') and status.get('preview_first') and not status.get('installation_changed') and not status.get('promotion_changed') and not status.get('certification_changed') and not status.get('policy_migrated'))]
  public=json.dumps(status); rows += [c('paths-suppressed',str(rr) not in public and str(target) not in public and '/tmp/' not in public),c('ordinary-conversation-unaffected',status.get('ordinary_conversation_affected') is False)]
  # Exact stale-authority detection after pointer-bound record tampering.
  pointer=json.loads((release_authority_readiness_directory(rr)/'active_readiness.json').read_text()); recpath=release_authority_readiness_directory(rr)/'previews'/f"{pointer['preview_id']}.json"; rec=json.loads(recpath.read_text()); rec['candidate_id']='eidolon-v0-forged'; recpath.write_text(json.dumps(rec),encoding='utf-8')
  stale=release_authority_readiness_status(runtime_root=rr); rows += [c('tampered-preview-rejected',not stale.get('ok') and stale.get('status')=='release_authority_stale_or_contradictory')]
  # Promoted-but-uncertified state cannot be called release ready.
  with tempfile.TemporaryDirectory(prefix='eidolon-v1098-0-uncertified-') as ud:
   uf=prepare_promoted_fixture(Path(ud)); urr=Path(uf['handoff_runtime']); create_certification_history_reconciliation_preview(runtime_root=urr); select_certification_policy(built_in_policy_id=BUILTIN_POLICY_ID,runtime_root=urr); create_policy_migration_preview(runtime_root=urr)
   unready=create_release_authority_readiness_preview(runtime_root=urr); rows += [c('promotion-not-certification',not unready.get('ok') and not unready.get('general_release_certified'))]
  # Multi-tab owner uses the existing generation/revision-bound authority.
  p=preview_operation_claim('release_authority_readiness_preview','tab-a',11,runtime_root=rr); claimed=claim_operation(p.get('authorization_token',''),confirm=OPERATION_CLAIM_CONFIRMATION,runtime_root=rr); blocked=preview_operation_claim('history_reconciliation','tab-b',12,runtime_root=rr); released=release_operation('tab-a',claimed.get('operation_generation',0),confirm=OPERATION_RELEASE_CONFIRMATION,runtime_root=rr)
  rows += [c('multi-tab-exact-owner',claimed.get('ok')),c('stale-tab-blocked',not blocked.get('ok')),c('owner-release-exact',released.get('ok'))]
  old=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(rr)
  code,payload=handle_api_get('/api/release-authority/readiness/status'); rows.append(c('standalone-api-get',code==200 and payload.get('data',{}).get('status') in {'release_authority_ready','release_authority_stale_or_contradictory'}))
  try: handle_api_get('/api/release-authority/readiness/create'); get_create=False
  except ApiError as e: get_create=e.status==404
  rows.append(c('creation-post-only',get_create))
  code2,payload2=handle_api_post('/api/release-authority/readiness/create',{}); rows.append(c('standalone-api-post',code2 in {200,409} and 'data' in payload2))
  html=render_release_certification(); rows += [c('dashboard-release-readiness','Release authority readiness' in html),c('dashboard-path-suppressed',str(rr) not in html and str(target) not in html)]
  if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
  else: os.environ['EIDOLON_DATA_DIR']=old
 report={'suite':'v1098.0-certification-to-release-authority-boundary','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
