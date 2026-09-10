from __future__ import annotations
import json,tempfile
from pathlib import Path
from v1098_bundle_c_test_support import *
import release_authority_consumer_lifecycle as life

def c(n,x): return {'name':n,'ok':bool(x)}
def main():
 rows=[]
 with tempfile.TemporaryDirectory(prefix='eidolon-v1098-9-') as t:
  rr=Path(t);ident=('release-command-deck','eidolon.consumer.command-deck','1.0','display exact release handoff status');_,receipt=make_receipt(rr,ident);life.release_authority_consumer_receipt_status=lambda *a,**k: current_status(ident,receipt)
  s=life.release_authority_handoff_lifecycle_status(*ident,runtime_root=rr);r=life.release_authority_handoff_lifecycle_status(*ident,runtime_root=rr)
  rows += [c('coherent',s.get('ok')),c('deterministic',s==r),c('get-content-free',s.get('content_free')),c('paths-suppressed',str(rr) not in json.dumps(s)),c('no-discovery',not s.get('consumer_discovery_performed')),c('no-newest-inference',not s.get('newest_receipt_inferred')),c('no-authority',not s.get('authority_granted')),c('ordinary-conversation-preserved',not s.get('ordinary_conversation_affected')),c('no-provider-native-model-actions',not s.get('provider_contacted') and not s.get('native_checks_run') and not s.get('models_mutated')),c('no-release-actions',not s.get('installation_changed') and not s.get('promotion_changed') and not s.get('certification_changed') and not s.get('policy_migrated'))]
 report={'suite':'v1098.9-release-authority-handoff-lifecycle-consolidation','passed':sum(x['ok'] for x in rows),'failed':sum(not x['ok'] for x in rows),'checks':rows};report['ok']=not report['failed'];print(json.dumps(report,indent=2));return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
