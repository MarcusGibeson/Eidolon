from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1367_test_support import *
def main():
 P=0
 bad=clean();
 for code in CODES:
  x=defective(code);bad.update({k:v for k,v in x.items() if x.get(k)!=clean().get(k)})
 r=diagnose_data_state(expected=EXP,observed=bad,repair_observed=clean());req(set(r['data_diagnosis']['finding_codes'])==set(CODES),'all classes');P+=1
 from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
 c=process_ordinary_chat_development_turn('show data diagnosis',project_state={'data_diagnosis':r['data_diagnosis']});req(c['active'] and c['ok'] and not c['action_executed'],'chat');P+=1
 req(r['data_diagnosis']['repair_snapshot_verified'] is True,'repair');P+=1
 req(not r['source_mutation_authorized'],'source');P+=1
 req(r['data_diagnosis']['record_digest'],'digest');P+=1
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1367-checkpoint'})
if __name__=='__main__':main()
