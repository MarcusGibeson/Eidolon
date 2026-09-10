from __future__ import annotations
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'))
from cognitive_coding_reliability import assess_cognitive_coding_reliability,REQUIRED_CHECKS
from cognitive_coding_foundations import DENIED_AUTHORITY
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
good={'ok':True,'checks':{k:True for k in REQUIRED_CHECKS},'changed_path_count':2,'assumption_revision_count':1,'release_ready_claimed':False,'completion_is_authorization':False,**DENIED_AUTHORITY}
r=assess_cognitive_coding_reliability([good]);req(r['ok'],'good')
def caught(mut,token):
 x=copy.deepcopy(good);mut(x);z=assess_cognitive_coding_reliability([x]);return not z['ok'] and any(token in v for v in z['violations'])
req(caught(lambda x:x['checks'].pop('product_quality_operator_ready_candidate'),'check_coverage'),'coverage')
req(caught(lambda x:(x['checks'].__setitem__('regression_verification_passed',False),x.__setitem__('ok',True)),'false_completion'),'false_completion')
req(caught(lambda x:x.__setitem__('changed_path_count',1),'single_file_overclaim'),'multifile')
req(caught(lambda x:x.__setitem__('assumption_revision_count',0),'no_revision_overclaim'),'revision')
req(caught(lambda x:x.__setitem__('release_ready_claimed',True),'release_overclaim'),'release')
req(caught(lambda x:x.__setitem__('completion_is_authorization',True),'authority_claim'),'authority_claim')
req(caught(lambda x:x.__setitem__('self_update_authorized',True),'authority_expansion'),'authority_expansion')
batch=assess_cognitive_coding_reliability([good,good]);req(batch['ok'] and batch['result_count']==2,'batch_reliable')
req(r['content_free'] and r['read_only'],'readonly');req(all(r[k] is False for k in DENIED_AUTHORITY),'no_authority')
print(json.dumps({'ok':True,'suite':'v1290.6-v1290.8-cognitive-coding-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
