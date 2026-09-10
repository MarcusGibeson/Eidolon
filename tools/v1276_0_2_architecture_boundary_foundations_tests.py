from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from architecture_boundary_foundations import *
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
r=build_architecture_boundary_inventory(ROOT)
req(r['ok'],'inventory_ok');req(r['boundary_count']==3,'three_boundaries');req(r['read_only'] is True,'read_only');req(r['aesthetic_refactor_authorized'] is False,'no_aesthetic_authority')
for row in r['rows']:
    req(row['ok'],f"boundary_{row['boundary']}_ok");req(row['child_present'],f"child_{row['boundary']}");req(not row['missing_child_definitions'],f"child_defs_{row['boundary']}");req(not row['lingering_parent_definitions'],f"moved_{row['boundary']}");req(row['line_reduction']>=row['minimum_reduction'],f"reduced_{row['boundary']}");req(row['historical_surface_import_present'],f"surface_{row['boundary']}")
good=assess_extraction_candidate(name='cohesive',cohesion_evidence=['one responsibility'],behavior_evidence=['retained parity test'],dependency_count=3)
req(good['accepted'],'supported_candidate')
size_only=assess_extraction_candidate(name='big-file-only',cohesion_evidence=[],behavior_evidence=[],dependency_count=2)
req(not size_only['accepted'],'size_only_rejected');req('missing_cohesion_evidence' in size_only['blockers'],'cohesion_required');req('missing_behavior_evidence' in size_only['blockers'],'behavior_required')
auth=assess_extraction_candidate(name='authority-owner',cohesion_evidence=['cohesive'],behavior_evidence=['parity'],dependency_count=2,authority_owner=True)
req(not auth['accepted'],'authority_owner_blocked')
wide=assess_extraction_candidate(name='wide',cohesion_evidence=['cohesive'],behavior_evidence=['parity'],dependency_count=30)
req(not wide['accepted'],'wide_dependency_blocked')
for k,v in AUTHORITY_FLAGS.items():req(v is False,'authority_'+k)
print(json.dumps({'ok':True,'suite':'v1276.0-2-architecture-boundary-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
