from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from session_budgets import *
b=create_budget({k:10 for k in FIELDS});b=consume_budget(b,{'commands':3,'files_changed':2});req(b['used']['commands']==3,'commands');req(b['used']['files_changed']==2,'files');req(not b['exhausted'],'within')
print(json.dumps({'suite':'v1308.3-5-session-budgets','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
