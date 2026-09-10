import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from partial_result_retention import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1376_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='report-1',artifact_kind='report',artifact_bytes=b'useful interrupted work',remaining_check_codes=['review'],retention_authorized=True,producer_evidence_digest=E,runtime_root=td);x=r['partial_result'];P+=int(r['ok'])
 l=load_partial_result(campaign_record_digest=C,artifact_id='report-1',expected_record_digest=x['record_digest'],runtime_root=td,include_private_artifact=True);req(l['ok'] and l['private_artifact_bytes']==b'useful interrupted work','survives');P+=1
 d=retain_partial_result(campaign_record_digest=C,task_id_digest=T,artifact_id='report-1',artifact_kind='report',artifact_bytes=b'useful interrupted work',remaining_check_codes=['review'],retention_authorized=True,producer_evidence_digest=E,runtime_root=td);req(d['status']=='partial_result_duplicate','duplicate');P+=1
 c=process_ordinary_chat_development_turn('show partial results',project_state={'partial_result':x});req(c.get('active') and c.get('ok'),'chat');P+=1
 req('private_artifact_bytes' not in c and not c['action_executed'],'public');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1376-integration'})
