from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from session_budgets import *
b=create_budget({k:1 for k in FIELDS});b=consume_budget(b,{'commands':2});req(b['exhausted'],'exhausted');req('commands' in b['exhausted_fields'],'field');req(not b['project_mutation_authorized'],'authority')
print(json.dumps({'suite':'v1308.6-8-session-budgets','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
