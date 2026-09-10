from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
S='a'*64;R='b'*64;E='c'*64
C=[{'component_id':'api.handler','evidence_digests':[E,'d'*64],'call_distance':0,'direct_failure_link':True,'state_transition_match':True,'recent_diff':True},{'component_id':'storage.adapter','evidence_digests':[E],'call_distance':2,'direct_failure_link':False,'state_transition_match':True,'recent_diff':False},{'component_id':'environment','evidence_digests':[E],'call_distance':0,'environment_only':True}]
def req(v,m):
 if not v:raise AssertionError(m)
