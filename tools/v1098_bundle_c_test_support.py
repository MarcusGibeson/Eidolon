from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from release_candidate_identity import atomic_json,digest_payload
from release_authority_consumer import _consumer_key,_consumer_root

def make_receipt(rr:Path,identity):
 root=_consumer_root(rr,_consumer_key(*identity));rid='receipt-'+digest_payload({'i':identity})[:16]
 receipt={'consumer_receipt_id':rid,'consumer_id':identity[0],'consumer_schema':identity[1],'consumer_version':identity[2],'expected_use':identity[3],'consumer_key_sha256':_consumer_key(*identity),'grants_authority':False,'installation_authorized':False,'promotion_authorized':False,'certification_authorized':False,'policy_migration_authorized':False,'provider_access_authorized':False,'model_access_authorized':False,'native_platform_certification_authorized':False}
 receipt['consumer_receipt_sha256']=digest_payload(receipt)
 atomic_json(root/'receipts'/f'{rid}.json',receipt);atomic_json(root/'active_receipt.json',{'consumer_receipt_id':rid,'consumer_receipt_sha256':receipt['consumer_receipt_sha256']})
 op={'status':'completed','consumer_receipt_id':rid};op['operation_sha256']=digest_payload(op);atomic_json(root/'operations'/'operation.json',op)
 return root,receipt

def current_status(identity,receipt):
 return {'ok':True,'status':'release_authority_consumer_receipt_current','receipt_present':True,'receipt_stale':False,'consumer_id':identity[0],'consumer_schema':identity[1],'consumer_version':identity[2],'expected_use':identity[3],'consumer_receipt_id':receipt['consumer_receipt_id'],'consumer_receipt_sha256':receipt['consumer_receipt_sha256']}
