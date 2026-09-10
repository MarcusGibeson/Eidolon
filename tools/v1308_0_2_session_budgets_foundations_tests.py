from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from session_budgets import *
b=create_budget({k:10 for k in FIELDS});req(len(b['used'])==len(FIELDS),'fields');req(not b['exhausted'],'fresh');req(not b['budget_grants_authority'],'no_authority')
print(json.dumps({'suite':'v1308.0-2-session-budgets','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
