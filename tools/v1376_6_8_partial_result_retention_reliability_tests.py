import sys,tempfile,json;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from partial_result_retention import *
from v1376_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 req(not retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='x',artifact_kind='report',artifact_bytes=b'x',remaining_check_codes=['review'],retention_authorized=False,producer_evidence_digest=E,runtime_root=td)['ok'],'authority');P+=1
 req(not retain_partial_result(campaign_record_digest='bad',task_id_digest=T,artifact_id='x',artifact_kind='report',artifact_bytes=b'x',remaining_check_codes=['review'],retention_authorized=True,producer_evidence_digest=E,runtime_root=td)['ok'],'lineage');P+=1
 req(not retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='x',artifact_kind='bad',artifact_bytes=b'x',remaining_check_codes=['review'],retention_authorized=True,producer_evidence_digest=E,runtime_root=td)['ok'],'kind');P+=1
 req(not retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='x',artifact_kind='report',artifact_bytes=b'x',remaining_check_codes=[],retention_authorized=True,producer_evidence_digest=E,runtime_root=td)['ok'],'checks');P+=1
 r=retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='x',artifact_kind='report',artifact_bytes=b'x',remaining_check_codes=['review'],retention_authorized=True,producer_evidence_digest=E,runtime_root=td);x=r['partial_result'];p=Path(td)/'partial_results'/C/D('x')/'artifact.bin';p.write_bytes(b'y');req(not load_partial_result(campaign_record_digest=C,artifact_id='x',expected_record_digest=x['record_digest'],runtime_root=td)['ok'],'blob tamper');P+=1
 req(not load_partial_result(campaign_record_digest=C,artifact_id='missing',expected_record_digest='a'*64,runtime_root=td)['ok'],'missing');P+=1
 req(not retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='large',artifact_kind='report',artifact_bytes=b'xx',remaining_check_codes=['review'],retention_authorized=True,producer_evidence_digest=E,max_bytes=1,runtime_root=td)['ok'],'size');P+=1
print({'ok':P==7,'passed':P,'total':7,'suite':'v1376-reliability'})
