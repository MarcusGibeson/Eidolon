from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from v1369_test_support import *
def main():
 p=0
 for code,obs in CASES.items():
  r=diagnose_ui(obs);req(r['ok'] and r['ui_diagnosis']['primary_failure_class']==code,code);p+=1
 print({'ok':p==6,'passed':p,'total':6,'suite':'v1369-foundations'})
if __name__=='__main__':main()
