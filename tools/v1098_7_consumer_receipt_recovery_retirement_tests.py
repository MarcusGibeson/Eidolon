from __future__ import annotations
import json,tempfile
from pathlib import Path
from v1098_bundle_c_test_support import *
from release_candidate_identity import atomic_json,read_json,digest_payload
import release_authority_consumer_lifecycle as life

def c(n,x): return {'name':n,'ok':bool(x)}
def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1098-7-') as t:
  rr=Path(t);ident=('release-command-deck','eidolon.consumer.command-deck','1.0','display exact release handoff status');root,receipt=make_receipt(rr,ident);life.release_authority_consumer_receipt_status=lambda *a,**k: current_status(ident,receipt)
  op=read_json(root/'operations'/'operation.json');op['status']='receipt_written';op['operation_sha256']=digest_payload({k:v for k,v in op.items() if k!='operation_sha256'});atomic_json(root/'operations'/'operation.json',op)
  st=life.consumer_receipt_lifecycle_status(*ident,runtime_root=rr);p=life.preview_consumer_receipt_recovery(*ident,operator_tab_id='tab-a',operation_revision=901,runtime_root=rr)
  bad=life.recover_consumer_receipt('true',confirm=life.RECOVERY_CONFIRMATION,consumer_id=ident[0],consumer_schema=ident[1],consumer_version=ident[2],expected_use=ident[3],operator_tab_id='tab-a',operation_revision=901,runtime_root=rr)
  rec=life.recover_consumer_receipt(p['authorization_token'],confirm=life.RECOVERY_CONFIRMATION,consumer_id=ident[0],consumer_schema=ident[1],consumer_version=ident[2],expected_use=ident[3],operator_tab_id='tab-a',operation_revision=901,runtime_root=rr)
  rp=life.preview_consumer_receipt_retirement(*ident,operator_tab_id='tab-a',operation_revision=902,runtime_root=rr)
  wrong=life.create_consumer_receipt_retirement_preview(rp['authorization_token'],confirm='yes',consumer_id=ident[0],consumer_schema=ident[1],consumer_version=ident[2],expected_use=ident[3],operator_tab_id='tab-a',operation_revision=902,runtime_root=rr)
  done=life.create_consumer_receipt_retirement_preview(rp['authorization_token'],confirm=life.RETIREMENT_CONFIRMATION,consumer_id=ident[0],consumer_schema=ident[1],consumer_version=ident[2],expected_use=ident[3],operator_tab_id='tab-a',operation_revision=902,runtime_root=rr)
  reuse=life.create_consumer_receipt_retirement_preview(rp['authorization_token'],confirm=life.RETIREMENT_CONFIRMATION,consumer_id=ident[0],consumer_schema=ident[1],consumer_version=ident[2],expected_use=ident[3],operator_tab_id='tab-a',operation_revision=902,runtime_root=rr)
  rows += [c('interruption-detected',st.get('recovery_available')),c('truthy-token-rejected',not bad.get('ok')),c('exact-recovery',rec.get('ok')),c('retirement-preview-ready',rp.get('ok')),c('literal-confirmation-required',not wrong.get('ok')),c('retirement-preview-created',done.get('ok')),c('retirement-preview-single-use',not reuse.get('ok')),c('receipt-preserved',(root/'receipts'/f"{receipt['consumer_receipt_id']}.json").exists()),c('no-authority',not done.get('authority_granted')),c('content-free',str(rr) not in json.dumps(done))]
 report={'suite':'v1098.7-consumer-receipt-recovery-retirement','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=not report['failed'];print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
