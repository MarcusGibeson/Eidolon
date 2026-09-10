from __future__ import annotations
import json,os,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'):sys.path.insert(0,str(item))
from v1097_bundle_c_test_support import prepare_certified_fixture
from release_certification_history import create_certification_history_reconciliation_preview
from release_certification_policy import select_certification_policy,create_policy_migration_preview,BUILTIN_POLICY_ID
from release_certification_authority import certification_authority_coherence_status
from release_certification_coherence import preview_operation_claim,claim_operation,release_operation,OPERATION_CLAIM_CONFIRMATION,OPERATION_RELEASE_CONFIRMATION
from api_server import handle_api_get,handle_api_post,ApiError
from dashboard import render_release_certification

def c(n,o):return {'name':n,'ok':bool(o)}
def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-9-') as td:
  base=Path(td);f=prepare_certified_fixture(base);rr=Path(f['handoff_runtime']);create_certification_history_reconciliation_preview(runtime_root=rr);select_certification_policy(built_in_policy_id=BUILTIN_POLICY_ID,runtime_root=rr);create_policy_migration_preview(runtime_root=rr)
  status=certification_authority_coherence_status(runtime_root=rr);rows += [c('consolidated-coherent',status.get('ok') and status.get('status')=='certification_authority_coherent'),c('history-integrated',status.get('history_status')=='certification_history_coherent'),c('policy-integrated',status.get('policy_status')=='certification_policy_selected'),c('scope-exact',status.get('general_release_certified') and not status.get('native_windows_certified') and not status.get('provider_ollama_certified')),c('no-native-inference',not status.get('native_windows_inferred')),c('no-provider-inference',not status.get('provider_ollama_inferred'))]
  p=preview_operation_claim('policy_migration_preview','tab-a',7,runtime_root=rr);claimed=claim_operation(p['authorization_token'],confirm=OPERATION_CLAIM_CONFIRMATION,runtime_root=rr);blocked=preview_operation_claim('history_reconciliation','tab-b',8,runtime_root=rr);released=release_operation('tab-a',claimed.get('operation_generation',0),confirm=OPERATION_RELEASE_CONFIRMATION,runtime_root=rr);rows += [c('multi-tab-exact-owner',claimed.get('ok')),c('other-tab-blocked',not blocked.get('ok')),c('exact-owner-release',released.get('ok'))]
  old=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(rr)
  for path,key in [('/api/release-certification/history/status','history_sha256'),('/api/release-certification/policy/status','policy_sha256'),('/api/release-certification/policy/migration/status','scope_impacts'),('/api/release-certification/authority/status','general_release_certified')]:
   code,payload=handle_api_get(path);rows.append(c('api-'+path.split('/')[-2],code==200 and key in payload.get('data',{})))
  try:handle_api_get('/api/release-certification/history/create');post=False
  except ApiError as e:post=e.status==404
  rows.append(c('mutations-post-only',post))
  html=render_release_certification();rows += [c('dashboard-bounded','Authority history' in html and 'Certification policy' in html and 'Consolidated authority' in html),c('dashboard-path-suppressed',str(rr) not in html and str(f['target']) not in html)]
  if old is None:os.environ.pop('EIDOLON_DATA_DIR',None)
  else:os.environ['EIDOLON_DATA_DIR']=old
  public=json.dumps(status);rows += [c('public-path-suppressed',str(rr) not in public and '/tmp/' not in public),c('ordinary-conversation-unaffected',status.get('ordinary_conversation_affected') is False),c('no-auto-recertification',status.get('certified_scopes')==['general_release'])]
 report={'suite':'v1097.9-certification-authority-consolidation-checkpoint','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
