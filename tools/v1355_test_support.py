from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
SOURCE='a'*64; E='b'*64
BASE=[
 {'property_id':'identifier.safe','oracle':'identifier_validity','generator':'identifier','evidence_digest':E,'cases':24},
 {'property_id':'json.roundtrip','oracle':'json_roundtrip','generator':'json_value','evidence_digest':E,'cases':24},
 {'property_id':'integer.bounds','oracle':'bounded_integer','generator':'bounded_integer','evidence_digest':E,'cases':24},
 {'property_id':'lifecycle.allowed','oracle':'lifecycle_transition','generator':'lifecycle_transition','evidence_digest':E,'cases':24},
]
def req(v,m):
 if not v: raise AssertionError(m)
