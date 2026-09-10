from __future__ import annotations
import json,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1097_bundle_a_test_support import prepare_promoted_fixture,evidence_payload,write_evidence
from release_certification_evidence import select_certification_evidence,create_certification_readiness_preview,certification_directory
from release_certification_plan import create_certification_plan,certification_plan_status,preview_certification_authorization,certification_authorization_valid
from release_candidate_identity import read_json,atomic_json
from api_server import ApiError,handle_api_get,handle_api_post

def c(n,o):return {'name':n,'ok':bool(o)}
def populate(base,f,scopes):
 for scope in scopes:select_certification_evidence(write_evidence(base/'evidence'/f'{scope}.json',evidence_payload(f,scope)),runtime_root=f['handoff_runtime'])

def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-2-ready-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);populate(base,f,('source_package_integrity','startup_daily_use','installation_recovery','promotion_behavior'));create_certification_readiness_preview(runtime_root=f['handoff_runtime']);plan=create_certification_plan(runtime_root=f['handoff_runtime']);status=certification_plan_status(runtime_root=f['handoff_runtime']);auth=preview_certification_authorization(runtime_root=f['handoff_runtime']);valid,findings=certification_authorization_valid(auth['authorization_token'],f['handoff_runtime'])
  rows += [c('ready-plan-created',plan.get('ok') and plan.get('proposed_decision')=='certified'),c('exact-evidence-set-bound',plan.get('evidence_count')==4 and plan.get('evidence_set_sha256')),c('release-identities-bound',all(plan.get(k) for k in ('candidate_id','archive_sha256','installed_receipt_sha256','promotion_receipt_sha256','target_inventory_sha256'))),c('plan-status-stable',status.get('ok') and status.get('status')=='certification_planned'),c('authorization-previewed',auth.get('ok') and auth.get('authorization_token') and auth.get('literal_confirmation_required')=='AUTHORIZE EXACT CERTIFICATION DECISION'),c('authorization-valid',valid and not findings),c('no-certification-apply',not auth.get('certification_applied') and not auth.get('certified'))]
  import os
  previous=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=str(f['handoff_runtime'])
  code,payload=handle_api_get('/api/release-certification/plan/status');rows.append(c('api-plan-status',code==200 and payload.get('data',{}).get('plan_id')==plan.get('plan_id')))
  try:handle_api_get('/api/release-certification/authorization-preview');rejected=False
  except ApiError as exc:rejected=exc.status==404
  rows.append(c('authorization-post-only',rejected))
  if previous is None:os.environ.pop('EIDOLON_DATA_DIR',None)
  else:os.environ['EIDOLON_DATA_DIR']=previous
  # Evidence drift invalidates plan and token.
  directory=certification_directory(f['handoff_runtime']);pointer=read_json(directory/'active_readiness.json');record=read_json(directory/'readiness'/f"{pointer['preview_id']}.json");record['satisfied_evidence'][0]['artifact_sha256']='0'*64;atomic_json(directory/'readiness'/f"{pointer['preview_id']}.json",record);stale=certification_plan_status(runtime_root=f['handoff_runtime']);_,stale_findings=certification_authorization_valid(auth['authorization_token'],f['handoff_runtime']);rows += [c('plan-drift-detected',not stale.get('ok') and stale.get('status')=='certification_plan_stale'),c('stale-token-rejected',bool(stale_findings))]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-2-insufficient-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);create_certification_readiness_preview(runtime_root=f['handoff_runtime']);blocked=create_certification_plan('certified',runtime_root=f['handoff_runtime']);insufficient=create_certification_plan(runtime_root=f['handoff_runtime']);rows += [c('missing-evidence-blocks-certified-plan',not blocked.get('ok')),c('insufficient-plan-recordable',insufficient.get('ok') and insufficient.get('proposed_decision')=='insufficient_evidence')]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-2-scope-') as td:
  base=Path(td);f=prepare_promoted_fixture(base);payload=evidence_payload(f,'native_windows_behavior',environment={'os':'windows','native':True},producer='eidolon-native-windows-verifier');select_certification_evidence(write_evidence(base/'native.json',payload),runtime_root=f['handoff_runtime']);create_certification_readiness_preview('native_windows',runtime_root=f['handoff_runtime']);native=create_certification_plan(runtime_root=f['handoff_runtime']);rows += [c('native-plan-scope-exact',native.get('ok') and native.get('certification_scope')=='native_windows' and native.get('evidence_count')==1),c('native-does-not-imply-general',native.get('certification_scope')!='general_release')]
 report={'suite':'v1097.2-certification-plan-binding-exact-authorization','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
