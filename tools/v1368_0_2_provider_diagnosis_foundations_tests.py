from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1368_test_support import *
def main():
 P=0
 for k,o in CASES.items():
  r=diagnose_provider(o);req(k in r['provider_diagnosis']['failure_classes'],k);P+=1
 print({'ok':P==8,'passed':P,'total':8,'suite':'v1368-foundations'})
if __name__=='__main__':main()
