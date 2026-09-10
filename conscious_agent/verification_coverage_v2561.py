from __future__ import annotations
"""v2561 structural verification-coverage confidence for fast verification plans."""
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib, json, re

CONTRACT_VERSION='v2561.0'
GENERIC_STEMS={'dashboard','api_server','main','memory','settings','release_metadata'}
AUTHORITY={'required_test_waiver_authorized':False,'test_suppression_authorized':False,'release_authorized':False,'certification_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()

def assess_verification_coverage(source_root:str|Path, changed_paths:Sequence[str], plan:Mapping[str,Any])->dict[str,Any]:
    root=Path(source_root).resolve(); tests=[str(x) for x in ((plan.get('tiers') or {}).get('1') or {}).get('tests',[])][:12]
    test_text={}
    for rel in tests:
        p=root/rel
        if p.is_file():
            try:test_text[rel]=p.read_text(encoding='utf-8')
            except OSError:test_text[rel]=''
    rows=[]
    for raw in changed_paths:
        rel=str(raw or '').replace('\\','/').strip(); p=Path(rel); stem=p.stem
        if not rel.endswith('.py'): continue
        direct=[]
        for test,text in test_text.items():
            if rel in text or re.search(rf'(?<![A-Za-z0-9_]){re.escape(stem)}(?![A-Za-z0-9_])',text): direct.append(test)
        if direct: level='focused_direct'
        elif stem in GENERIC_STEMS: level='integration_only'
        else: level='uncovered'
        rows.append({'path':rel,'coverage':level,'direct_tests':direct[:6],'generic_surface':stem in GENERIC_STEMS})
    uncovered=sum(r['coverage']=='uncovered' for r in rows); integration=sum(r['coverage']=='integration_only' for r in rows); direct=sum(r['coverage']=='focused_direct' for r in rows)
    if uncovered: confidence='weak'
    elif integration and not direct: confidence='moderate'
    else: confidence='strong'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'confidence':confidence,'changed_python_count':len(rows),'focused_direct_count':direct,'integration_only_count':integration,'uncovered_count':uncovered,'coverage':rows,'selected_tier1_test_count':len(tests),'raw_test_output_stored':False,'tests_removed':0,**AUTHORITY};out['coverage_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','assess_verification_coverage']
