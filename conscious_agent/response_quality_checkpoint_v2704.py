from __future__ import annotations
from tempfile import TemporaryDirectory
from conversation_outcome_attribution_v2700 import build_conversation_outcome_attribution
from response_quality_evaluation_v2701 import evaluate_response_quality
from response_quality_history_v2702 import append_response_quality, load_response_quality_history
from response_quality_trend_v2703 import build_response_quality_trend
from response_quality_review_v2704 import build_response_quality_review

def build_checkpoint():
    checks={}
    with TemporaryDirectory() as td:
        for i,kind in enumerate(['confirmed_resolution','confirmed_resolution','correction','correction','correction','correction']):
            a=build_conversation_outcome_attribution(explicit_resolution={'explicit':True,'kind':kind});q=evaluate_response_quality(a);append_response_quality(q,a,operation_id=f'op-{i}',runtime_root=td)
        rows=load_response_quality_history(td)['rows'];t=build_response_quality_trend(rows,window=3);r=build_response_quality_review(evaluate_response_quality(build_conversation_outcome_attribution(explicit_resolution={'explicit':True,'kind':'correction'})),t)
        checks={'history':len(rows)==6,'trend_worsening':t['direction']=='worsening','review':r['review_required'],'no_policy':not r['automatic_policy_change'],'no_repair':not r['automatic_response_repair'],'no_text':not t['raw_conversation_text_stored'],'no_authority':not r['authority_granted']}
    return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
