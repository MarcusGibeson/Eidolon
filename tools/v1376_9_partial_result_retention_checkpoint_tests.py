import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from partial_result_retention import *
from v1376_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='artifact',artifact_kind='build-artifact',artifact_bytes=b'partial',remaining_check_codes=['verify','reconcile'],retention_authorized=True,producer_evidence_digest=E,runtime_root=td);x=r['partial_result'];req(r['ok'],'checkpoint');P+=1
 req(x['remaining_check_count']==2,'remaining');P+=1
 req(not x['usable_as_verified_evidence'],'unverified');P+=1
 req(x['content_free'] and not x['raw_artifact_public'],'privacy');P+=1
 req(not r['release_authorized'] and not r['independent_authority_granted'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1376-checkpoint'})
