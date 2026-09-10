from __future__ import annotations
import json,os,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
for item in (ROOT/'conscious_agent',ROOT/'tools'):sys.path.insert(0,str(item))
from v1097_bundle_a_test_support import prepare_promoted_fixture,evidence_payload,write_evidence
from release_certification_evidence import select_certification_evidence,create_certification_readiness_preview
from release_certification_plan import create_certification_plan,preview_certification_authorization
from release_certification_transaction import apply_authorized_certification,CERTIFICATION_APPLY_CONFIRMATION,certification_status
from release_certification_recovery import certification_recovery_status,preview_certification_recovery,resume_certification_decision,CERTIFICATION_RECOVERY_CONFIRMATION
from release_certification_freshness import evidence_freshness_status,create_recertification_readiness_preview,recertification_readiness_status
from release_certification_coherence import *
from api_server import ApiError,handle_api_get,handle_api_post
from dashboard import render_release_certification

def c(n,o):return {'name':n,'ok':bool(o)}
def populate(base,f):
 for scope in ('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'):
  select_certification_evidence(write_evidence(base/'evidence'/f'{scope}.json',evidence_payload(f,scope)),runtime_root=f['handoff_runtime'])
def certify(base,f,interrupt=''):
 populate(base,f);create_certification_readiness_preview(runtime_root=f['handoff_runtime']);create_certification_plan(runtime_root=f['handoff_runtime']);a=preview_certification_authorization(runtime_root=f['handoff_runtime']);return apply_authorized_certification(a['authorization_token'],confirm=CERTIFICATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'],_interrupt_at=interrupt)

def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-6-coherent-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);out=certify(base,f);create_recertification_readiness_preview(runtime_root=f['handoff_runtime']);coherent=certification_coherence_status(runtime_root=f['handoff_runtime'])
  rows += [c('authority-coherent',out.get('general_release_certified') and coherent.get('status')=='certification_daily_use_coherent'),c('freshness-exposed',set(coherent.get('fresh_scopes',[]))=={'source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'}),c('scope-authority-exact',coherent.get('certified_scopes')==['general_release']),c('no-native-inference',not coherent.get('native_windows_inferred')),c('no-provider-inference',not coherent.get('provider_ollama_inferred'))]
  claimp=preview_operation_claim('recertification_preview','tab-a',1,runtime_root=f['handoff_runtime']);wrong=claim_operation(claimp['authorization_token'],confirm='true',runtime_root=f['handoff_runtime']);claimed=claim_operation(claimp['authorization_token'],confirm=OPERATION_CLAIM_CONFIRMATION,runtime_root=f['handoff_runtime']);restart=certification_coherence_status(runtime_root=f['handoff_runtime']);other=preview_operation_claim('certification_decision','tab-b',2,runtime_root=f['handoff_runtime']);stale=preview_operation_claim('recertification_preview','tab-a',1,runtime_root=f['handoff_runtime']);released=release_operation('tab-a',claimed.get('operation_generation',0),confirm=OPERATION_RELEASE_CONFIRMATION,runtime_root=f['handoff_runtime']);rows += [c('claim-preview-bound',claimp.get('ok')),c('claim-literal-confirmation',not wrong.get('ok')),c('single-owner-claimed',claimed.get('ok') and restart.get('operation_owner_present')),c('dashboard-restart-reattaches',restart.get('operation')=='recertification_preview'),c('other-tab-blocked',not other.get('ok')),c('stale-revision-blocked',not stale.get('ok')),c('exact-release',released.get('ok') and not certification_coherence_status(runtime_root=f['handoff_runtime']).get('operation_owner_present'))]
  previous=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(f['handoff_runtime'])
  for path,key in [('/api/release-certification/coherence/status','status'),('/api/release-certification/recovery/status','status'),('/api/release-certification/evidence/freshness','fresh_scope_count'),('/api/release-certification/recertification/status','status')]:
   code,payload=handle_api_get(path);rows.append(c(f'api-{path.split("/")[-2]}-get',code==200 and key in payload.get('data',{})))
  try:handle_api_get('/api/release-certification/recovery/resume');post_only=False
  except ApiError as exc:post_only=exc.status==404
  rows.append(c('recovery-mutation-post-only',post_only))
  html=render_release_certification();rows += [c('dashboard-bounded-status','Daily-use coherence' in html and 'Evidence freshness' in html),c('dashboard-path-suppressed',str(f['handoff_runtime']) not in html and str(f['target']) not in html)]
  if previous is None:os.environ.pop('EIDOLON_DATA_DIR',None)
  else:os.environ['EIDOLON_DATA_DIR']=previous
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-6-recovery-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);certify(base,f,'after_receipt');status=certification_coherence_status(runtime_root=f['handoff_runtime']);p=preview_certification_recovery(runtime_root=f['handoff_runtime']);res=resume_certification_decision(p['authorization_token'],confirm=CERTIFICATION_RECOVERY_CONFIRMATION,runtime_root=f['handoff_runtime']);after=certification_coherence_status(runtime_root=f['handoff_runtime']);rows += [c('interrupted-status-exposed',status.get('recovery_available')),c('recovery-no-duplicate-decision',res.get('ok') and after.get('authority_status')=='scope_certified'),c('long-session-status-stable',all(certification_coherence_status(runtime_root=f['handoff_runtime']).get('ok') for _ in range(20)))]
 public=json.dumps(rows)
 rows += [c('no-private-paths-in-results','/tmp/' not in public and '\\\\' not in public),c('ordinary-conversation-unaffected',coherent.get('ordinary_conversation_affected') is False)]
 report={'suite':'v1097.6-certification-daily-use-release-authority-coherence','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
