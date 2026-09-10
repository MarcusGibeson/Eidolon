import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_improvement_backlog import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1382_test_support import *
N=0
r=build_self_improvement_backlog(self_model_digest=SM,observations=[obs(),obs('failure','bug','scope',9,95,2)]);x=r['self_improvement_backlog'];req(x['deduplicated_count']==1,'dedup');N+=1
c=x['candidates'][0];q=review_self_improvement_candidate(backlog=x,expected_backlog_digest=x['backlog_digest'],candidate_id=c['candidate_id'],disposition='propose',operator_reviewed=True);req(q['ok'],'review');N+=1
req(not q['review']['execution_authorized'],'proposal only');N+=1
chat=process_ordinary_chat_development_turn('show self improvement backlog',project_state={'self_improvement_backlog':x});req(chat.get('active') and chat.get('ok'),'chat');N+=1
req(not chat['action_executed'] and not chat['source_mutation_authorized'],'read only');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1382-integration'})
