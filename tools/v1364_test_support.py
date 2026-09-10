from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
S='a'*64;R='b'*64;E='c'*64
C=[{'candidate_id':'broad','evidence_digest':E,'changed_files':['a.py','b.py'],'test_ids':['unit.a','unit.b'],'regression_risks':['api'],'addresses_root_cause':True,'rollback_defined':True,'predicted_behavior_defined':True},{'candidate_id':'narrow','evidence_digest':'d'*64,'changed_files':['a.py'],'test_ids':['unit.a','integration.a'],'regression_risks':['api'],'addresses_root_cause':True,'rollback_defined':True,'predicted_behavior_defined':True}]
def req(v,m):
 if not v:raise AssertionError(m)
