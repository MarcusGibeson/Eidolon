from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1368_test_support import *
def main():
 P=0
 obs={};
 for o in CASES.values():obs.update(o)
 obs.update({'configured':False,'endpoint_resolved':False,'model_present':False,'transport_connected':False,'streaming_expected':True,'streaming_valid':False,'embedding_expected':True,'embedding_valid':False,'timed_out':True})
 r=diagnose_provider(obs);req(set(r['provider_diagnosis']['failure_classes'])>=set(ORDER[:-1]),'coverage');P+=1
 from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
 c=process_ordinary_chat_development_turn('show provider diagnosis',project_state={'provider_diagnosis':r['provider_diagnosis']});req(c['active'] and c['ok'] and not c['action_executed'],'chat');P+=1
 req(not r['provider_contact_authorized'],'boundary');P+=1
 req(not r['provider_diagnosis']['raw_provider_content_persisted'],'content');P+=1
 req(r['provider_diagnosis']['record_digest'],'digest');P+=1
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1368-checkpoint'})
if __name__=='__main__':main()
