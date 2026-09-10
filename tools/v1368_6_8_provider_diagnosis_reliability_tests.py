from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1368_test_support import *
def main():
 P=0
 req(not diagnose_provider(None)['ok'],'invalid');P+=1
 r=diagnose_provider({'transport_connected':True,'elapsed_ms':101,'timeout_ms':100});req('timeout' in r['provider_diagnosis']['failure_classes'],'elapsed timeout');P+=1
 r=diagnose_provider({'transport_connected':True,'response_schema_valid':False,'quality_acceptable':False});req('model_quality' not in r['provider_diagnosis']['failure_classes'],'quality precondition');P+=1
 r=diagnose_provider({'streaming_expected':False,'streaming_valid':False});req('streaming' not in r['provider_diagnosis']['failure_classes'],'stream optional');P+=1
 r=diagnose_provider({'embedding_expected':False,'embedding_valid':False});req('embedding' not in r['provider_diagnosis']['failure_classes'],'embedding optional');P+=1
 r=diagnose_provider({'timed_out':True,'transport_connected':False});req(r['provider_diagnosis']['failure_classes']==['transport','timeout'],'multi');P+=1
 req(not r['action_executed'],'read only');P+=1
 print({'ok':P==7,'passed':P,'total':7,'suite':'v1368-reliability'})
if __name__=='__main__':main()
