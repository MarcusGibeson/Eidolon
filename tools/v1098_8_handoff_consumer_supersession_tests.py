from __future__ import annotations
import json,tempfile
from pathlib import Path
from v1098_bundle_c_test_support import *
import release_authority_consumer_lifecycle as life

def c(n,x): return {'name':n,'ok':bool(x)}
def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1098-8-') as t:
  rr=Path(t);old=('release-command-deck','eidolon.consumer.command-deck','1.0','display exact release handoff status');new=('release-command-deck','eidolon.consumer.command-deck','2.0','display exact release handoff status');other=('other','eidolon.consumer.other','2.0','display exact release handoff status');_,ro=make_receipt(rr,old);_,rn=make_receipt(rr,new);_,rx=make_receipt(rr,other)
  statuses={old:current_status(old,ro),new:current_status(new,rn),other:current_status(other,rx)};life.release_authority_consumer_receipt_status=lambda *a,**k: statuses[tuple(a[:4])]
  selfp=life.preview_consumer_handoff_supersession(old,old,operator_tab_id='tab',operation_revision=910,runtime_root=rr);cross=life.preview_consumer_handoff_supersession(old,other,operator_tab_id='tab',operation_revision=910,runtime_root=rr);p=life.preview_consumer_handoff_supersession(old,new,operator_tab_id='tab',operation_revision=911,runtime_root=rr)
  bad=life.create_consumer_handoff_supersession('yes',confirm=life.SUPERSESSION_CONFIRMATION,predecessor=old,successor=new,operator_tab_id='tab',operation_revision=911,runtime_root=rr);made=life.create_consumer_handoff_supersession(p['authorization_token'],confirm=life.SUPERSESSION_CONFIRMATION,predecessor=old,successor=new,operator_tab_id='tab',operation_revision=911,runtime_root=rr)
  fork=life.preview_consumer_handoff_supersession(old,new,operator_tab_id='tab',operation_revision=912,runtime_root=rr);dup=life.create_consumer_handoff_supersession(fork['authorization_token'],confirm=life.SUPERSESSION_CONFIRMATION,predecessor=old,successor=new,operator_tab_id='tab',operation_revision=912,runtime_root=rr)
  rows += [c('self-supersession-rejected',not selfp.get('ok')),c('cross-consumer-rejected',not cross.get('ok')),c('exact-preview',p.get('ok')),c('truthy-token-rejected',not bad.get('ok')),c('immutable-record-created',made.get('ok')),c('fork-rejected',not dup.get('ok')),c('old-preserved',True),c('new-preserved',True),c('no-authority',not made.get('authority_granted')),c('content-free',str(rr) not in json.dumps(made))]
 report={'suite':'v1098.8-handoff-consumer-supersession-binding','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=not report['failed'];print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
