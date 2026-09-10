from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1367_test_support import *
def main():
 P=0
 r=diagnose_data_state(expected=EXP,observed=clean());req(r['status']=='data_state_coherent','clean');P+=1
 req(not diagnose_data_state(expected=None,observed=clean())['ok'],'bad');P+=1
 x=defective('partial_write');x['row_count']=2;r=diagnose_data_state(expected=EXP,observed=x);req(r['data_diagnosis']['finding_codes'].count('partial_write')==1,'dedupe');P+=1
 x=clean();x['content_digest']='d'*64;r=diagnose_data_state(expected=EXP,observed=x);req('content_metadata_boundary_failure' in r['data_diagnosis']['finding_codes'],'digest boundary');P+=1
 x=clean();x['schema_version']=1;r=diagnose_data_state(expected=EXP,observed=x);req('migration_gap' in r['data_diagnosis']['finding_codes'],'version');P+=1
 r=diagnose_data_state(expected=EXP,observed=defective('schema_drift'));req(r['data_diagnosis']['content_free'] and not r['action_executed'],'privacy');P+=1
 req(not r['data_mutation_authorized'],'authority');P+=1
 print({'ok':P==7,'passed':P,'total':7,'suite':'v1367-reliability'})
if __name__=='__main__':main()
