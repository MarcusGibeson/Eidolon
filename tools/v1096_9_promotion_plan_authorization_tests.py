from __future__ import annotations
import json,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.path.insert(0,str(ROOT/'tools'))
from v1096_bundle_c_test_support import prepare_staged_fixture,snapshot_files
from release_installation_transaction import INSTALLATION_APPLY_CONFIRMATION,apply_authorized_installation,preview_installation_apply_authorization
from release_promotion_preview import create_promotion_impact_preview,promotion_directory
from release_promotion_plan import create_promotion_plan,promotion_plan_status,preview_promotion_authorization,promotion_authorization_valid,active_promotion_plan_private
from release_candidate_identity import atomic_json,read_json

def c(n,o):return {'name':n,'ok':bool(o)}
def installed_fixture(base):
 f=prepare_staged_fixture(base); a=preview_installation_apply_authorization(runtime_root=f['handoff_runtime']); r=apply_authorized_installation(a['authorization_token'],confirm=INSTALLATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']); return f,r

def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1096-9-') as td:
  f,installed=installed_fixture(Path(td)); create_promotion_impact_preview(runtime_root=f['handoff_runtime']); before=snapshot_files(f['target']); plan=create_promotion_plan(runtime_root=f['handoff_runtime']); status=promotion_plan_status(runtime_root=f['handoff_runtime']); auth=preview_promotion_authorization(runtime_root=f['handoff_runtime']); _,findings=promotion_authorization_valid(auth.get('authorization_token',''),f['handoff_runtime']); after=snapshot_files(f['target'])
  rows += [c('promotion-plan-created',plan.get('ok') and plan.get('status')=='promotion_planned'),c('plan-exact-bindings',all(plan.get(k) for k in ('plan_binding_sha256','preview_id','transaction_identity_sha256','installed_receipt_sha256','candidate_id','archive_sha256','target_inventory_sha256','metadata_effects_sha256','reversal_plan_sha256'))),c('plan-status-coherent',status.get('ok')),c('authorization-preview-created',auth.get('ok') and auth.get('status')=='promotion_authorized' and auth.get('authorization_token')),c('authorization-valid',not findings),c('source-unchanged',before==after),c('no-apply-certification',not plan.get('promotion_applied') and not plan.get('certified'))]
  token=auth['authorization_token']; bad=token+'x'; _,badf=promotion_authorization_valid(bad,f['handoff_runtime']); rows.append(c('malformed-token-rejected',bool(badf)))
  (f['target']/'README.md').write_text('target drift\n',encoding='utf-8'); stale=promotion_plan_status(runtime_root=f['handoff_runtime']); _,stalef=promotion_authorization_valid(token,f['handoff_runtime']); rows += [c('target-drift-stales-plan',not stale.get('ok') and stale.get('status')=='promotion_plan_stale'),c('stale-token-rejected',bool(stalef))]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1096-9-preserve-') as td:
  f,_=installed_fixture(Path(td)); create_promotion_impact_preview(runtime_root=f['handoff_runtime']); good=create_promotion_plan(runtime_root=f['handoff_runtime']); pointer_before=read_json(promotion_directory(f['handoff_runtime'])/'active_plan.json'); (f['target']/'README.md').write_text('drift\n',encoding='utf-8'); failed=create_promotion_plan(runtime_root=f['handoff_runtime']); pointer_after=read_json(promotion_directory(f['handoff_runtime'])/'active_plan.json'); rows.append(c('failed-plan-preserves-active',not failed.get('ok') and pointer_before==pointer_after and good.get('plan_id')==pointer_after.get('plan_id')))
 with tempfile.TemporaryDirectory(prefix='eidolon-v1096-9-cross-') as a, tempfile.TemporaryDirectory(prefix='eidolon-v1096-9-cross2-') as b:
  f1,_=installed_fixture(Path(a)); create_promotion_impact_preview(runtime_root=f1['handoff_runtime']); create_promotion_plan(runtime_root=f1['handoff_runtime']); token=preview_promotion_authorization(runtime_root=f1['handoff_runtime'])['authorization_token']
  f2,_=installed_fixture(Path(b)); create_promotion_impact_preview(runtime_root=f2['handoff_runtime']); create_promotion_plan(runtime_root=f2['handoff_runtime']); _,cross=promotion_authorization_valid(token,f2['handoff_runtime']); rows.append(c('cross-runtime-token-rejected',bool(cross)))
 report={'suite':'v1096.9-promotion-plan-binding-exact-authorization','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
