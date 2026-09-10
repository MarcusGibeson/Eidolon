from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from unit_contract_test_generation import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1353_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_unit_contract_test_plan(source_manifest_digest=d('s'),contracts=sample_contracts(),runtime_root=td);i=r['unit_contract_test_plan_id'];req(load_unit_contract_test_plan(i,runtime_root=td)['record_digest'],'load');P+=1;c=process_ordinary_chat_development_turn('show unit contract tests',project_state={'unit_contract_test_plan_id':i},runtime_root=td);req(c['active'] and c['ok'],'chat');P+=1;req(c['action_executed'] is False and not c['test_execution_authorized'],'readonly');P+=1;req(all('contract_id' not in x for x in c['unit_contract_test_plan']['contracts']),'content minimized');P+=1
print({'ok':P==4,'passed':P,'total':4,'suite':'v1353.3-5-unit-contract-tests-integration'})
