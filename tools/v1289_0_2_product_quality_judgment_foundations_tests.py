from __future__ import annotations
import json,sys
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from product_quality_judgment_foundations import DENIED_AUTHORITY,DIMENSIONS,assess_quality_dimensions,normalize_quality_evidence

C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
def dig(s): return sha256(s.encode()).hexdigest()
def row(d,t='deterministic_test',state='pass',name=None,**kw):
    return {'dimension':d,'evidence_type':t,'state':state,'evidence_digest':dig(name or f'{d}:{t}:{state}'),'scope_digest':dig('scope'),'fresh':kw.pop('fresh',True),**kw}

# Narrow deterministic success is deliberately not enough for product-quality readiness.
only_tests=[row(d,name=f'test:{d}') for d in DIMENSIONS]
a=assess_quality_dimensions(only_tests)
req(a['contract_version']=='v1289.2','contract')
req(set(a['dimensions'])==set(DIMENSIONS),'six_dimensions')
req(all(v['state']=='insufficient' for v in a['dimensions'].values()),'tests_alone_insufficient')
req(all(not v['specialized_evidence_present'] for v in a['dimensions'].values()),'tests_not_specialized')
req(a['evidence_count']==6,'test_evidence_count')

# One relevant specialized passing item can establish each dimension.
special={
 'coherence':'integration_test','usability':'usability_review','accessibility':'accessibility_review',
 'maintainability':'static_analysis','completeness':'requirements_review','operator_readiness':'operator_walkthrough'}
full=[row(d,t,name=f'special:{d}') for d,t in special.items()]
b=assess_quality_dimensions(full)
req(all(v['state']=='pass' for v in b['dimensions'].values()),'specialized_passes')
req(all(v['specialized_evidence_present'] for v in b['dimensions'].values()),'specialized_present')

# Negative evidence dominates a positive item for the same dimension.
neg=full+[row('accessibility','native_validation','fail','accessibility-fail')]
c=assess_quality_dimensions(neg)
req(c['dimensions']['accessibility']['state']=='fail','accessibility_failure_dominates')
req(c['dimensions']['accessibility']['failure_count']==1,'failure_count')

# Known warnings/unknowns stay visible rather than being silently promoted.
warn=[x for x in full if x['dimension']!='usability']+[row('usability','usability_review','warn','usability-warn')]
d=assess_quality_dimensions(warn)
req(d['dimensions']['usability']['state']=='warn','usability_warning_preserved')
unknown=[x for x in full if x['dimension']!='operator_readiness']+[row('operator_readiness','operator_walkthrough','unknown','operator-unknown')]
e=assess_quality_dimensions(unknown)
req(e['dimensions']['operator_readiness']['state']=='unknown','unknown_without_pass_preserved')

# Stale evidence cannot establish a dimension.
stale=[row('accessibility','accessibility_review','pass','stale-a11y',fresh=False)]
f=assess_quality_dimensions(stale)
req(f['dimensions']['accessibility']['state']=='unknown','stale_ignored')
req(f['dimensions']['accessibility']['fresh_evidence_count']==0,'stale_not_fresh_count')

# Exact duplicate evidence is counted once, not amplified.
dup=normalize_quality_evidence([row('coherence','integration_test','pass','dup'),row('coherence','integration_test','pass','dup')])
req(len(dup)==1,'duplicate_suppressed')
req(dup[0]['content_free'] is True,'normalized_content_free')

# Invalid dimensions/types/digests are rejected.
try: normalize_quality_evidence([row('coherence')|{'dimension':'beauty'}]); bad_dim=False
except ValueError: bad_dim=True
req(bad_dim,'bad_dimension_rejected')
try: normalize_quality_evidence([row('coherence')|{'evidence_type':'green_checkmark'}]); bad_type=False
except ValueError: bad_type=True
req(bad_type,'bad_type_rejected')
try: normalize_quality_evidence([row('coherence')|{'evidence_digest':'abc'}]); bad_digest=False
except ValueError: bad_digest=True
req(bad_digest,'bad_digest_rejected')

req(a['read_only'] and a['content_free'],'read_only_content_free')
req(all(a[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1289.0-v1289.2-product-quality-judgment-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
