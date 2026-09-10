from __future__ import annotations
import hashlib,json
from conscious_agent.supervised_project_development_lineage import *
from conscious_agent.supervised_project_outcome_learning import *
from conscious_agent.supervised_project_reliability_recovery import *
from conscious_agent.supervised_project_reliability_recovery_checkpoint import build_supervised_project_reliability_recovery_checkpoint

def h(x):return hashlib.sha256(x.encode()).hexdigest()
def main():
 checks=[];rows=[];prev=""
 for s in STAGES:
  r=create_project_stage_receipt(stage=s,status="completed",artifact_digest=h(s),previous_receipt_digest=prev,operator_review_digest=h(s+'r'));rows.append(r);prev=r['receipt_digest']
 lineage=integrate_supervised_project_development(rows);p=create_project_result_presentation(lineage=lineage,outcome='repaired',operator_decision_digest=h('d'),result_evidence_digest=h('e'),rollback_available=True);l=create_accountable_outcome_learning(presentation=p,lesson_codes=['retain_repair_pattern'],operator_learning_review_digest=h('lr'))
 def make(**kw):
  args=dict(lineage=lineage,presentation=p,learning=l,expected_source_digest=h('s'),observed_source_digest=h('s'),expected_terminal_digest=lineage['terminal_receipt_digest'],interruption_state='resumed',interruption_receipt_digest=h('i'),rollback_expected_digest=h('r'),rollback_observed_digest=h('r'));args.update(kw);return create_project_reliability_receipt(**args)
 good=make();checks += [good['status']=='recovery_review_ready',good['rollback_verified'],not good['rollback_executed']]
 for bad in [make(observed_source_digest=h('drift')),make(rollback_observed_digest=h('bad')),make(interruption_state='unknown'),make(privacy_findings=['secret']),make(expected_terminal_digest=h('wrong'))]:checks.append(bad['status']=='blocked')
 tl=dict(lineage);tl['stage_count']=1;checks.append(create_project_reliability_receipt(lineage=tl,presentation=p,learning=l,expected_source_digest=h('s'),observed_source_digest=h('s'),expected_terminal_digest=lineage['terminal_receipt_digest'],interruption_state='resumed',interruption_receipt_digest=h('i'),rollback_expected_digest=h('r'),rollback_observed_digest=h('r'))['status']=='blocked')
 for key in ('production_source_modified','sandbox_modified','execution_invoked','rollback_executed','provider_contacted','model_contacted','approval_created','authority_granted','source_application_authorized','installation_authorized','promotion_authorized','certification_authorized','release_authorized','autonomous_action_authorized'):checks.append(good[key] is False)
 checks.append(build_supervised_project_reliability_recovery_checkpoint()['ok'])
 failed=[i for i,v in enumerate(checks) if not v];print(json.dumps({'ok':not failed,'passed':len(checks)-len(failed),'total':len(checks),'failed':failed},sort_keys=True));return 0 if not failed else 1
if __name__=='__main__':raise SystemExit(main())
