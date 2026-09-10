from __future__ import annotations
import hashlib,json,sys,tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.background_cognitive_runtime_v2505 import BackgroundCognitiveRuntime
from conscious_agent.memory_consolidation_runtime_v2506 import prepare_memory_consolidation
from conscious_agent.developmental_self_model_v2507 import DevelopmentalSelfModelStore
from conscious_agent.adaptive_plan_health_v2508 import AdaptivePlanHealthStore,evaluate_plan_health
from conscious_agent.long_horizon_planning_intelligence import create_long_horizon_plan
checks=[]
def req(v,n): checks.append(n); assert v,n
def d(x): return hashlib.sha256(x.encode()).hexdigest()
class Clock:
    def __init__(self): self.t=datetime(2026,9,2,16,0,tzinfo=timezone.utc)
    def __call__(self): return self.t.isoformat().replace('+00:00','Z')
    def add(self,s): self.t+=timedelta(seconds=s)
with tempfile.TemporaryDirectory(prefix='eidolon-v2508-9-campaign-') as td:
    root=Path(td); clock=Clock()
    bg=BackgroundCognitiveRuntime(root,clock=clock); bg.configure('cfg',enabled=True,minimum_interval_seconds=5,max_cycles_per_hour=4)
    br=bg.run_structural_tick('bg1',trigger_type='background_memory_review',subject_ref='experience',new_experience=True)
    req(br['status']=='background_structural_cognition_completed','background_completed')
    req(br['outcome_type']=='MEMORY_INTEGRATION_CANDIDATE','background_memory_candidate')
    req(not br['candidate_applied'],'background_unapplied')
    memories=[
        {'id':'e1','type':'experience','content':'A verifier run was too broad','source':'user','confidence':.8},
        {'id':'e2','type':'experience','content':'Another broad verifier run','source':'user','confidence':.8},
        {'id':'l1','type':'lesson','content':'Prefer focused verification','source':'development_outcome_lesson','confidence':.9},
        {'id':'a1','type':'reflection','content':'I repeatedly broaden verification too early','source':'reflection','role':'assistant','confidence':.8},
    ]
    mc=prepare_memory_consolidation('mc1',runtime_root=root,message='verification',memory_records=memories,protected_operator_constraints=['preserve_historical_truth'])
    req(mc['candidate_count']>=2,'memory_candidates')
    req('PROCEDURAL_LESSON_REVIEW' in mc['candidate_types'],'procedural_memory')
    req('AUTOBIOGRAPHICAL_CONTINUITY_REVIEW' in mc['candidate_types'],'autobiographical_memory')
    req(not mc['memory_mutated'],'memory_unmutated')
    sm=DevelopmentalSelfModelStore(root)
    for i in range(3): sm.observe(f'sm{i}',trait_code='verification_scope_bias',domain='software_development',polarity='support',evidence_digest=d(f'sm{i}'),source_kind='development_outcome')
    trait=sm.stage_trait_candidate('trait',trait_code='verification_scope_bias',domain='software_development')
    req(trait['ok'],'trait_candidate')
    req(trait['state']=='supported','trait_supported')
    req(not trait['trait_applied'] and not trait['identity_rewritten'],'trait_unapplied')
    plan=create_long_horizon_plan('Improve verification strategy',[{'milestone_code':'observe','tasks':[{'task_code':'collect'}]},{'milestone_code':'change','depends_on':['observe'],'tasks':[{'task_code':'adjust'}]}],runtime_root=root)
    ph=AdaptivePlanHealthStore(root); ph.record_signal('sig',plan_id=plan['plan_id'],plan_digest=plan['plan_digest'],signal_type='assumption_invalidated',evidence_digest=d('sig'),severity=.9,expected_value_delta=-.5)
    review=evaluate_plan_health(plan,ph.signals_for(plan['plan_id'],plan['plan_digest']))
    req(review['health_state'] in {'attention_required','replan_required'},'plan_adapts')
    req(review['assumptions_should_be_rechecked'],'assumption_recheck')
    req(not review['plan_modified'] and not review['execution_authorized'],'plan_candidate_only')
    req(bg.inspection_summary()['open_cycle_count']==0,'background_closed')
    req(not bg.inspection_summary()['provider_contacted'],'no_provider')
    req(not bg.inspection_summary()['message_sent'],'no_message')
    req(not bg.inspection_summary()['tool_executed'],'no_tool')
    req(not bg.inspection_summary()['source_mutated'],'no_source_mutation')
    req(not sm.inspection_summary()['authority_boundary']['can_rewrite_identity'],'no_identity_authority')
    req(not ph.inspection_summary()['authority_boundary']['can_reprioritize_plan'],'no_plan_authority')
print(json.dumps({'ok':True,'checkpoint_version':'2508.9','contract':'Cognitive Continuity Campaign Checkpoint','passed':len(checks),'total':len(checks),'checks':checks},sort_keys=True))
