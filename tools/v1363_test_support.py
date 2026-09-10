from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
S='a'*64;R='b'*64;L='c'*64;E='d'*64
FACTS=[{'fact_id':'request.large','evidence_digest':E,'triggers_failure':True},{'fact_id':'parser.boundary','evidence_digest':'e'*64,'direct_defect_evidence':True,'necessary_for_failure':True},{'fact_id':'ui.error','evidence_digest':'f'*64,'downstream_of_defect':True},{'fact_id':'slow.disk','evidence_digest':'1'*64,'environment_only':True}]
def req(v,m):
 if not v:raise AssertionError(m)
