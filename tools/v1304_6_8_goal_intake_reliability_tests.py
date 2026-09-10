from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from goal_intake import *
for bad in ('','bogus'):
 try:intake_goal(source_kind=bad,request_text='x')
 except ValueError:req(True,'bad_'+(bad or 'empty'))
 else:req(False,'bad')
try:intake_goal(source_kind='direct_command',request_text='')
except ValueError:req(True,'empty_text')
else:req(False,'empty_text')
print(json.dumps({'suite':'v1304.6-8-goal-intake','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
