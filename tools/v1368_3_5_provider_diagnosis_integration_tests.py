from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1368_test_support import *
def main():
 P=0
 r=diagnose_provider({'configured':True,'endpoint_resolved':True,'model_present':True,'transport_connected':True,'response_schema_valid':True,'quality_acceptable':True});req(r['status']=='provider_evidence_healthy','healthy');P+=1
 r=diagnose_provider({'configured':False,'endpoint_resolved':False,'model_present':False});req(r['provider_diagnosis']['primary_failure_class']=='configuration','precedence');P+=1
 req(not r['provider_contact_authorized'] and not r['provider_diagnosis']['provider_contact_performed'],'no contact');P+=1
 req(not r['model_management_authorized'],'no management');P+=1
 req(r['provider_diagnosis']['content_free'],'privacy');P+=1
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1368-integration'})
if __name__=='__main__':main()
