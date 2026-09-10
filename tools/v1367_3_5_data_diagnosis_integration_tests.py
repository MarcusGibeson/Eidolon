from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1367_test_support import *
def main():
 P=0
 for code in CODES:
  r=diagnose_data_state(expected=EXP,observed=defective(code),repair_observed=clean());v=r['data_diagnosis'];req(v['repair_snapshot_verified'] is True and not v['runtime_data_modified'],code);P+=1
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1367-integration'})
if __name__=='__main__':main()
