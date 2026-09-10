import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from partial_result_retention import *
from v1376_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='patch-1',artifact_kind='patch',artifact_bytes=b'private patch',remaining_check_codes=['unit','integration'],retention_authorized=True,producer_evidence_digest=E,runtime_root=td);req(r['ok'],'retain');P+=1
 x=r['partial_result'];req(x['verification_status']=='partial_unverified' and not x['usable_as_verified_evidence'],'status');P+=1
 req(x['artifact_byte_count']==13 and x['remaining_check_count']==2,'counts');P+=1
 req(x['content_free'] and not x['raw_artifact_public'],'privacy');P+=1
 req(not r['project_mutation_authorized'] and not r['application_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1376-foundations'})
