from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1367_test_support import *
def main():
 P=0
 for code in CODES:
  r=diagnose_data_state(expected=EXP,observed=defective(code));req(r['ok'] and code in r['data_diagnosis']['finding_codes'],code);P+=1
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1367-foundations'})
if __name__=='__main__':main()
