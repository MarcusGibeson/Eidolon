from __future__ import annotations
from tempfile import TemporaryDirectory
from response_outcome_followup_signal_v2707 import build_response_outcome_followup_signal
from response_quality_positive_retrospective_v2708 import build_positive_retrospective_quality
from response_quality_history_v2702 import append_positive_retrospective_quality, load_response_quality_history
from response_quality_observability_v2705 import build_response_quality_observability
from response_quality_review_v2704 import build_response_quality_review

def build_checkpoint():
    checks={}
    with TemporaryDirectory() as td:
        prior={'grounding':{'operation_ref_digest':'c'*64}}
        sig=build_response_outcome_followup_signal('That fixed it')
        pos=build_positive_retrospective_quality(prior,sig,evidence_operation_id='later')
        append_positive_retrospective_quality(pos,runtime_root=td)
        obs=build_response_quality_observability(td)
        review=build_response_quality_review({'state':'supported_success'},obs['trend'])
        checks={'positive_bound':pos['evidence_recorded'],'history':len(load_response_quality_history(td)['rows'])==1,'observable':obs['supported_success_count']==1,'silence_rule':not sig['raw_message_stored'],'review_not_forced':not review['automatic_policy_change'],'no_repair':not obs['automatic_response_repair'],'no_authority':not obs['authority_granted']}
    return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
