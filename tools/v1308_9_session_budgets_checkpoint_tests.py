from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from session_budgets import *
b=create_budget({k:5 for k in FIELDS});req(CONTRACT_VERSION=='v1308.8','contract');req(len(FIELDS)==9,'nine');req(not b['standing_authority_granted'],'standing')
print(json.dumps({'suite':'v1308.9-session-budgets-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
