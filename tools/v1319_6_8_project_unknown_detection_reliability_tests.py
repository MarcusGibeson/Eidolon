from __future__ import annotations
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
checks=[]
def req(v,n):checks.append(n);assert v,n
from project_unknown_detection import *
a=make_claim('x','observed',['a']);b=make_claim('x','inferred',['b']);r=reconcile_claims([a,b]);req(r[0]['state']=='contradicted','contradiction');req(r[0]['confidence']<=CAP['contradicted'],'downgrade');req(not r[0]['unknown_is_false'],'unknown_semantics')
print(json.dumps({'suite':'v1319.6-8-project-unknowns','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
