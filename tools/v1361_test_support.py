from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
S='a'*64;E='b'*64;ENV='c'*64
EVID=[{'kind':'report','evidence_digest':E},{'kind':'failed_check','evidence_digest':'d'*64},{'kind':'screenshot','evidence_digest':'e'*64}]
CANDS=[
 {'candidate_id':'broad','evidence_digest':E,'deterministic':True,'reproduces':True,'steps':[{'kind':'prepare_fixture','target_id':'fixture'},{'kind':'set_environment','target_id':'env'},{'kind':'invoke_interface','target_id':'ui'},{'kind':'perform_action','target_id':'send'},{'kind':'assert_state','target_id':'failed'}]},
 {'candidate_id':'minimal','evidence_digest':'f'*64,'deterministic':True,'reproduces':True,'steps':[{'kind':'prepare_fixture','target_id':'fixture'},{'kind':'perform_action','target_id':'send'},{'kind':'assert_state','target_id':'failed'}]},
]
def req(v,m):
 if not v:raise AssertionError(m)
