from __future__ import annotations
import json, os, tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.path.insert(0,str(ROOT/'tools'))
from v1096_bundle_c_test_support import prepare_staged_fixture,snapshot_files
from release_installation_transaction import INSTALLATION_APPLY_CONFIRMATION,apply_authorized_installation,preview_installation_apply_authorization
from release_promotion_preview import create_promotion_impact_preview,promotion_directory,current_promotion_state_private
from release_promotion_plan import create_promotion_plan,preview_promotion_authorization
from release_promotion_transaction import *
from release_installed_state import installed_state_status
from release_candidate_identity import atomic_json,read_json,digest_payload
from api_server import ApiError,handle_api_get,handle_api_post

def c(n,o):return {'name':n,'ok':bool(o)}
def prep(base):
 f=prepare_staged_fixture(base); ia=preview_installation_apply_authorization(runtime_root=f['handoff_runtime']); ir=apply_authorized_installation(ia['authorization_token'],confirm=INSTALLATION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']); create_promotion_impact_preview(runtime_root=f['handoff_runtime']); create_promotion_plan(runtime_root=f['handoff_runtime']); pa=preview_promotion_authorization(runtime_root=f['handoff_runtime']); return f,ir,pa

def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-0-') as td:
  f,ir,pa=prep(Path(td)); before=snapshot_files(f['target']); wrong=apply_authorized_promotion(pa['authorization_token'],confirm='true',runtime_root=f['handoff_runtime']); applied=apply_authorized_promotion(pa['authorization_token'],confirm=PROMOTION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']); after=snapshot_files(f['target']); status=promotion_transaction_status(runtime_root=f['handoff_runtime']); installed=installed_state_status(runtime_root=f['handoff_runtime']); reused=apply_authorized_promotion(pa['authorization_token'],confirm=PROMOTION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'])
  rows += [c('literal-confirmation-required',not wrong.get('ok') and wrong.get('status')=='literal_confirmation_required'),c('promotion-applied',applied.get('ok') and applied.get('status')=='promoted_uncertified'),c('exact-receipt-state-bound',all(applied.get(k) for k in ('promotion_transaction_identity_sha256','promotion_receipt_sha256','promotion_state_sha256','installed_receipt_sha256','candidate_id','archive_sha256','target_inventory_sha256'))),c('source-unchanged',before==after and not applied.get('source_files_mutated')),c('status-promoted-uncertified',status.get('ok') and status.get('status')=='promoted_uncertified' and not status.get('certified')),c('installed-state-reconciles-promotion',installed.get('ok') and installed.get('status')=='promoted' and installed.get('promoted') and not installed.get('certified')),c('apply-token-single-use',not reused.get('ok') and reused.get('status')=='authorization_reused')]
  events=(promotion_directory(f['handoff_runtime'])/'events'/f"{applied['promotion_transaction_id']}.jsonl").read_text().splitlines(); seq=[json.loads(x)['sequence'] for x in events]; rows.append(c('append-only-ordered-events',seq==list(range(1,len(seq)+1)) and len(seq)>=4))
  public=json.dumps(applied,sort_keys=True);rows.append(c('paths-private',str(f['target']) not in public and str(f['archive']) not in public and applied.get('content_free')))
  revp=preview_promotion_reversal(runtime_root=f['handoff_runtime']); reversed_state=reverse_promotion(revp['authorization_token'],confirm=PROMOTION_REVERSAL_CONFIRMATION,runtime_root=f['handoff_runtime']); installed2=installed_state_status(runtime_root=f['handoff_runtime']); reversal_status=promotion_transaction_status(runtime_root=f['handoff_runtime']); reused_rev=reverse_promotion(revp['authorization_token'],confirm=PROMOTION_REVERSAL_CONFIRMATION,runtime_root=f['handoff_runtime'])
  rows += [c('reversal-preview-bound',revp.get('ok') and revp.get('status')=='promotion_reversal_previewed'),c('promotion-reversed',reversed_state.get('ok') and reversed_state.get('status')=='reversed_to_installed_unpromoted'),c('reversed-installed-state',installed2.get('ok') and installed2.get('status')=='installed_unpromoted' and not installed2.get('promoted')),c('reversal-status-stable',reversal_status.get('ok') and reversal_status.get('status')=='reversed_to_installed_unpromoted'),c('reversal-token-single-use',not reused_rev.get('ok'))]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-0-interrupt-start-') as td:
  f,_,pa=prep(Path(td)); before=snapshot_files(f['target']); interrupted=apply_authorized_promotion(pa['authorization_token'],confirm=PROMOTION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'],_interrupt_at='after_start'); rp=preview_promotion_resume(runtime_root=f['handoff_runtime']); resumed=resume_promotion_transaction(rp['authorization_token'],confirm=PROMOTION_RESUME_CONFIRMATION,runtime_root=f['handoff_runtime']); rows += [c('interruption-after-start',interrupted.get('status')=='promotion_interrupted'),c('resume-preview',rp.get('ok') and rp.get('status')=='promotion_resume_previewed'),c('resume-completes',resumed.get('ok') and resumed.get('status')=='promoted_uncertified'),c('resume-no-source-mutation',before==snapshot_files(f['target']))]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-0-interrupt-receipt-') as td:
  f,_,pa=prep(Path(td)); interrupted=apply_authorized_promotion(pa['authorization_token'],confirm=PROMOTION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime'],_interrupt_at='after_receipt'); rp=preview_promotion_resume(runtime_root=f['handoff_runtime']); resumed=resume_promotion_transaction(rp['authorization_token'],confirm=PROMOTION_RESUME_CONFIRMATION,runtime_root=f['handoff_runtime']); rows += [c('interruption-after-receipt',interrupted.get('status')=='promotion_interrupted' and interrupted.get('promotion_receipt_sha256')),c('receipt-interruption-resumes',resumed.get('ok') and resumed.get('status')=='promoted_uncertified')]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-0-drift-') as td:
  f,_,pa=prep(Path(td)); (f['target']/'README.md').write_text('drift\n',encoding='utf-8'); blocked=apply_authorized_promotion(pa['authorization_token'],confirm=PROMOTION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']); rows.append(c('target-drift-blocks-apply',not blocked.get('ok') and blocked.get('status')=='authorization_stale_or_mismatched'))
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-0-cert-') as td:
  f,_,pa=prep(Path(td)); apply_authorized_promotion(pa['authorization_token'],confirm=PROMOTION_APPLY_CONFIRMATION,runtime_root=f['handoff_runtime']); pointer,state=current_promotion_state_private(f['handoff_runtime']); state['state']='certified';state['certified']=True;state['state_sha256']=digest_payload({k:v for k,v in state.items() if k!='state_sha256'});atomic_json(promotion_directory(f['handoff_runtime'])/'states'/f"{state['state_id']}.json",state);pointer['state']='certified';pointer['state_sha256']=state['state_sha256'];atomic_json(promotion_directory(f['handoff_runtime'])/'active_promotion_state.json',pointer);blocked=preview_promotion_reversal(runtime_root=f['handoff_runtime']);rows.append(c('certification-blocks-reversal',not blocked.get('ok') and blocked.get('status')=='promotion_reversal_blocked'))
 previous=os.environ.get('EIDOLON_DATA_DIR')
 with tempfile.TemporaryDirectory(prefix='eidolon-v1097-0-api-') as td:
  os.environ['EIDOLON_DATA_DIR']=td; code,payload=handle_api_get('/api/release-promotion/status');rows.append(c('api-get-status',code==200 and payload.get('data',{}).get('status')=='not_promoted'))
  try:handle_api_get('/api/release-promotion/apply');rej=False
  except ApiError as e:rej=e.status==404
  rows.append(c('promotion-mutations-post-only',rej));pc,pp=handle_api_post('/api/release-promotion/apply',{'authorization_token':'bad','confirm':'true'});rows.append(c('post-requires-exact-token-confirmation',pc==409 and not pp.get('data',{}).get('ok')))
 if previous is None:os.environ.pop('EIDOLON_DATA_DIR',None)
 else:os.environ['EIDOLON_DATA_DIR']=previous
 report={'suite':'v1097.0-transactional-promotion-apply-release-coherence','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=report['failed']==0;print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
