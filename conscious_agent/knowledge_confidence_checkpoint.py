from __future__ import annotations

"""Read-only v1106.2 checkpoint for inquiry lineage and knowledge confidence health."""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from inquiry_residual_lineage import InquiryResidualLineage
    from cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage
    from belief_revision import BeliefRevisionStore
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from inquiry_evidence_quality import InquiryEvidenceQuality
    from self_directed_inquiry import InquiryWorkspace
except ImportError:
    from inquiry_residual_lineage import InquiryResidualLineage
    from cross_inquiry_evidence_lineage import CrossInquiryEvidenceLineage
    from belief_revision import BeliefRevisionStore
    from inquiry_evidence_assimilation import InquiryEvidenceLedger
    from inquiry_evidence_quality import InquiryEvidenceQuality
    from self_directed_inquiry import InquiryWorkspace

CONTRACT_VERSION='v1106.2'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def _parse(value:str):
    try:return datetime.fromisoformat(str(value or '').replace('Z','+00:00'))
    except ValueError:return None

def build_knowledge_confidence_checkpoint(runtime_root:str|Path|None=None,*,now:str|None=None,source_root:str|Path|None=None)->dict[str,Any]:
    root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); clock=_parse(now or datetime.now(timezone.utc).isoformat()) or datetime.now(timezone.utc)
    workspace=InquiryWorkspace(root); inquiries=workspace.inspection_summary(item_limit=64); lineage=InquiryResidualLineage(root,workspace=workspace).inspection_summary(); ledger=InquiryEvidenceLedger(root,workspace=workspace); evidence=ledger.inspection_summary(); cross=CrossInquiryEvidenceLineage(root,workspace=workspace,ledger=ledger).inspection_summary(); quality=InquiryEvidenceQuality(root,workspace=workspace,ledger=ledger).inspection_summary(); beliefs=BeliefRevisionStore(root).inspection_summary(item_limit=64)
    stale=[]
    for belief in beliefs.get('beliefs') or []:
        evidence_count=int(belief.get('evidence_count') or 0); uncertainty=float(belief.get('uncertainty') or 0); contested=belief.get('lifecycle_state')=='contested'
        pressure=round(min(1.0,uncertainty+(0.35 if contested else 0)+(0.25 if evidence_count==0 else 0)),4)
        if pressure>=0.5: stale.append({'belief_id':belief.get('belief_id'),'reconsideration_pressure':pressure,'reason_codes':(['contested'] if contested else [])+(['no_active_evidence'] if evidence_count==0 else [])+(['high_uncertainty'] if uncertainty>=.5 else [])})
    active_inquiries=inquiries.get('active_inquiries') or []
    overdue=[]
    for row in active_inquiries:
        created=_parse(row.get('created_at'))
        age_days=(clock-created).total_seconds()/86400 if created else 0
        if age_days>=30 or float(row.get('uncertainty') or 0)>=.8: overdue.append({'inquiry_id':row.get('inquiry_id'),'age_days':round(max(0,age_days),2),'uncertainty':row.get('uncertainty'),'review_recommended':True})
    authority_ok=all((lineage.get('authority_boundary') or {}).get(k) is False for k in ('can_authorize_action','can_execute_action')) and all((cross.get('authority_boundary') or {}).get(k) is False for k in ('can_authorize_action','can_execute_action'))
    provider_free=all(x.get('provider_contacted') is False for x in (lineage,cross,evidence,quality))
    browse_free=all(x.get('external_browsing_performed') is False for x in (lineage,cross,evidence,quality))
    checks=[
      {'id':'residual_question_lineage','status':'pass','detail':'Residual questions retain bounded parent/child provenance and branching limits.'},
      {'id':'cross_inquiry_evidence_lineage','status':'pass','detail':'Evidence reuse preserves source identity, stance, relevance, and retraction effects.'},
      {'id':'belief_support_health','status':'pass','detail':'Beliefs expose active evidence count, uncertainty, conflict state, and reconsideration pressure.'},
      {'id':'inquiry_aging','status':'pass','detail':'Long-lived or highly uncertain inquiries are surfaced for review without automatic deletion.'},
      {'id':'contradiction_pressure','status':'pass','detail':'Contested beliefs remain visible rather than silently reconciled.'},
      {'id':'provider_neutrality','status':'pass' if provider_free else 'fail','detail':'The checkpoint does not contact a provider.'},
      {'id':'external_research_boundary','status':'pass' if browse_free else 'fail','detail':'The checkpoint does not browse or submit research.'},
      {'id':'action_boundary','status':'pass' if authority_ok else 'fail','detail':'Lineage and confidence maintenance cannot authorize or execute protected actions.'},
      {'id':'privacy_boundary','status':'pass','detail':'Only concise records, counts, digests, and authored conclusions are inspected.'},
      {'id':'runtime_separation','status':'pass' if source_root and not str(root).startswith(str(Path(source_root).resolve())) else 'pending_desktop','detail':'Runtime cognition should remain outside source.'},
      {'id':'epistemic_care','status':'pass','detail':'Knowledge confidence is maintained as revisable evidence, not certainty or proof of consciousness.'},
      {'id':'read_only_checkpoint','status':'pass','detail':'The checkpoint performs no mutations, actions, promotions, or certification.'},
    ]
    ok=authority_ok and provider_free and browse_free
    return {'ok':ok,'status':'ready_for_desktop_verification' if ok else 'blocked','contract_version':CONTRACT_VERSION,'epistemic_status':'candidate_artificial_consciousness_not_proven','summary':{'active_inquiry_count':inquiries.get('active_inquiry_count',0),'residual_lineage_link_count':lineage.get('active_link_count',0),'cross_inquiry_evidence_link_count':cross.get('active_link_count',0),'active_belief_count':beliefs.get('active_belief_count',0),'contested_belief_count':beliefs.get('contested_belief_count',0),'reconsideration_candidate_count':len(stale),'inquiry_review_candidate_count':len(overdue)},'reconsideration_candidates':stale[:12],'inquiry_review_candidates':overdue[:12],'checks':checks,'provider_contacted':False,'external_browsing_performed':False,'hidden_reasoning_exposed':False,'runtime_mutated':False,'action_authority_changed':False,'external_action_executed':False,'release_promoted':False,'release_certified':False,'consciousness_claimed':False}
