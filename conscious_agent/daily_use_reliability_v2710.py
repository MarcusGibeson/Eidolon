from __future__ import annotations
"""v2710 cross-system daily-use reliability evaluation.

Read-only structural assessment.  It deliberately distinguishes absence of data
from a healthy state and never grants operational authority.
"""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2710.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_daily_use_reliability(snapshot:Mapping[str,Any])->dict[str,Any]:
    now=snapshot.get('now') if isinstance(snapshot.get('now'),Mapping) else {}
    conv=snapshot.get('conversation_health') if isinstance(snapshot.get('conversation_health'),Mapping) else {}
    resp=snapshot.get('response_quality') if isinstance(snapshot.get('response_quality'),Mapping) else {}
    mem=snapshot.get('memory_retrieval') if isinstance(snapshot.get('memory_retrieval'),Mapping) else {}
    mf=mem.get('feedback') if isinstance(mem.get('feedback'),Mapping) else {}
    ctx=snapshot.get('conversation_context') if isinstance(snapshot.get('conversation_context'),Mapping) else {}
    signals=snapshot.get('signals') if isinstance(snapshot.get('signals'),Mapping) else {}
    concerns=[];strengths=[];unknown=[]
    conv_state=str(conv.get('state') or 'no_data');resp_state=str(resp.get('state') or 'no_history');mem_state=str(mf.get('state') or 'no_data');ctx_state=str(ctx.get('state') or 'no_data')
    if conv_state=='degraded': concerns.append('conversation_health_degraded')
    elif conv_state=='attention': concerns.append('conversation_health_attention')
    elif conv_state=='nominal': strengths.append('conversation_health_nominal')
    else: unknown.append('conversation_health')
    if resp_state=='quality_concern': concerns.append('response_quality_concern')
    elif resp_state=='mixed_evidence': concerns.append('response_quality_mixed')
    elif resp_state=='supported_success': strengths.append('explicit_response_success_evidence')
    elif resp_state in {'no_history','unknown'}: unknown.append('response_quality')
    preserve=bool(mf.get('should_preserve_uncertainty'))
    if mem_state in {'weak_context_only','no_useful_memory'}:
        if preserve: strengths.append('memory_uncertainty_restraint_working')
        else: concerns.append('weak_memory_without_uncertainty_restraint')
    elif mem_state in {'grounded_correction','grounded_relevant_memory'}: strengths.append('grounded_memory_available')
    else: unknown.append('memory_retrieval')
    if ctx_state=='budget_constrained': concerns.append('context_budget_pressure')
    elif ctx_state in {'context_supported','current_turn_only'}: strengths.append('context_sufficient')
    elif ctx_state in {'no_data','unknown'}: unknown.append('conversation_context')
    pressure=float(now.get('pressure') or 0.0);recovery=float(now.get('recovery_margin') or 0.0)
    if pressure>=0.80 and recovery<=0.25: concerns.append('cognitive_pressure_without_recovery_margin')
    elif pressure>=0.80: concerns.append('cognitive_pressure_elevated')
    elif now: strengths.append('cognitive_load_bounded')
    else: unknown.append('cognitive_state')
    signal_state=str(signals.get('state') or signals.get('overall') or '')
    if signal_state in {'elevated','notice','degraded','attention'}: concerns.append('cognitive_observability_'+signal_state)
    if len(concerns)>=3 or 'weak_memory_without_uncertainty_restraint' in concerns or 'cognitive_pressure_without_recovery_margin' in concerns: state='degraded'
    elif concerns: state='attention'
    elif len(unknown)>=3 and not strengths: state='insufficient_data'
    else: state='nominal'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'concern_count':len(concerns),'strength_count':len(strengths),'unknown_dimension_count':len(set(unknown)),'concerns':concerns[:12],'strengths':strengths[:12],'unknown_dimensions':sorted(set(unknown))[:12],
         'cross_system_evaluated':True,'read_only':True,'automatic_policy_change':False,'automatic_action':False,'provider_contacted':False,'raw_conversation_text_stored':False,'hidden_reasoning_exposed':False,'authority_granted':False}
    out['reliability_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_daily_use_reliability']
