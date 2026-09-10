from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
S='a'*64;D='b'*64;M='c'*64
def rec(i='e1',**kw):
 x={'evidence_id':i,'source_manifest_digest':S,'provenance_ids':[],'claim_digest':D,'verification_method_digest':M,'self_asserted':False,'complete':True,'reproducible':True,'content_free':True};x.update(kw);return x
def req(v,m):
 if not v:raise AssertionError(m)
