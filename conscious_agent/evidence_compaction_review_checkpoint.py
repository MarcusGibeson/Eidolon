from __future__ import annotations
"""Read-only v1192.5 operator evidence compaction review checkpoint."""
import hashlib, os
from pathlib import Path
from typing import Any
from bounded_evidence_compaction import create_evidence_record, compact_evidence, verify_compaction_equivalence
from checkpoint_registry import inspect_checkpoint_registry
from evidence_compaction_review import create_compaction_review_request, create_compaction_review, review_compaction, public_compaction_review_summary
from package_integrity import package_privacy_summary_for_root
CONTRACT_VERSION = "v1192.5"
_CHECKPOINT_ID = "evidence-compaction-review:v1192.5"
_LIMITATIONS = ("Review is content-free and presentation-only.", "Original evidence is never replaced or deleted.", "No approval is created or consumed and no authority is granted.", "Reliability and stale-compaction hardening remain for v1192.6-v1192.8.")
def _h(value: str) -> str: return hashlib.sha256(value.encode()).hexdigest()
def _tree(root: Path):
    h=hashlib.sha256(); count=0
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {'data','sandbox','.git','.venv','venv','__pycache__','.pytest_cache','dist','build','reports'}]
        for name in sorted(files):
            path=Path(base)/name
            if path.suffix.lower() in {'.pyc','.pyo'}: continue
            try: data=path.read_bytes(); rel=path.relative_to(root).as_posix()
            except OSError: continue
            count+=1; h.update(rel.encode()); h.update(b'\0'); h.update(hashlib.sha256(data).digest())
    return h.hexdigest(), count
def build_evidence_compaction_review_checkpoint(*, source_root: str|Path|None=None, runtime_root: str|Path|None=None) -> dict[str, Any]:
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); del runtime_root
    before,count=_tree(source); checks=[]; req=lambda value: checks.append(bool(value))
    snapshot=_h('v1191.9:snapshot'); context=_h('v1192.5:context'); rows=[]; previous=''
    for i in range(3):
        row=create_evidence_record(evidence_id=f'evidence-review-{i}',sequence=i,previous_evidence_digest=previous,snapshot_digest=snapshot,context_digest=context,artifact_digest=_h(f'a{i}'),receipt_digest=_h(f'r{i}'),domain=('conversation','campaign','learning')[i],evidence_kind=('observation','transition','learning')[i],outcome=('retained','suspended','retained')[i],uncertainty_code=('none','bounded','unresolved')[i],approval_state=('not_required','deferred','review_required')[i],rollback_state=('not_applicable','available','unavailable')[i]); rows.append(row); previous=row['evidence_digest']
    compacted=compact_evidence(rows,snapshot_digest=snapshot,context_digest=context); equiv=verify_compaction_equivalence(rows,compacted,snapshot_digest=snapshot,context_digest=context)
    equivalence_digest=_h(str(equiv['original_digest'])+str(equiv['expanded_digest']))
    request=create_compaction_review_request(request_id='compaction-review-request-1192',compaction_digest=compacted['compaction_digest'],terminal_evidence_digest=compacted['compaction']['terminal_evidence_digest'],snapshot_digest=snapshot,context_digest=context,record_count=3,equivalence_digest=equivalence_digest)
    outcomes={}
    for decision in ('approve','reject','defer'):
        review=create_compaction_review(request_digest=request['request_digest'],decision=decision,review_id=f'compaction-review-{decision}-1192',operator_review_digest=_h(decision))
        result=review_compaction(request=request,review=review,current_snapshot_digest=snapshot,current_context_digest=context,current_compaction_digest=compacted['compaction_digest'],current_terminal_evidence_digest=previous,equivalence_verified=True); outcomes[decision]=result
        req(result['status']=={'approve':'review_approved','reject':'review_rejected','defer':'review_deferred'}[decision]); req(result['original_evidence_preserved'] is True); req(result['replacement_performed'] is False); req(result['deletion_performed'] is False); req(result['authority_granted'] is False)
    blocked={}
    def run(name, rq=request, rv=None, **current):
        if rv is None: rv=create_compaction_review(request_digest=rq['request_digest'],decision='approve',review_id=f'blocked-review-{name}-1192',operator_review_digest=_h(name))
        blocked[name]=review_compaction(request=rq,review=rv,current_snapshot_digest=current.get('snapshot',snapshot),current_context_digest=current.get('context',context),current_compaction_digest=current.get('compaction',compacted['compaction_digest']),current_terminal_evidence_digest=current.get('terminal',previous),equivalence_verified=current.get('equivalent',True))
    run('stale-snapshot', snapshot=_h('stale')); run('stale-context', context=_h('stale')); run('stale-compaction', compaction=_h('stale')); run('stale-terminal', terminal=_h('stale')); run('not-equivalent', equivalent=False)
    bad=dict(request); bad['deletion_requested']=True; run('hidden-deletion', bad)
    bad=dict(request); bad['prompt']='private'; run('private-field', bad)
    bad=dict(request); bad['request_digest']='0'*64; run('tamper', bad)
    for result in blocked.values(): req(result['status']=='blocked'); req(result['replacement_performed'] is False); req(result['deletion_performed'] is False); req(result['authority_granted'] is False)
    summary=public_compaction_review_summary(outcomes['approve']); req(summary['content_free'] is True); req(summary['original_evidence_preserved'] is True)
    registry=inspect_checkpoint_registry(source_root=source); req(any(row.get('checkpoint_id')=='evidence-compaction-review-checkpoint' for row in registry.get('checkpoints',[])))
    privacy=package_privacy_summary_for_root(source); req(privacy.get('ok') is True)
    after,after_count=_tree(source); req(before==after); req(count==after_count)
    return {'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract_version':CONTRACT_VERSION,'checkpoint_id':_CHECKPOINT_ID,'read_only':True,'post_available':False,'content_free':True,'summary':{'record_count':3,'approved_count':1,'rejected_count':1,'deferred_count':1,'blocked_case_count':len(blocked),'original_evidence_preserved':True},'blocked_cases':{k:v['errors'] for k,v in blocked.items()},'limitations':list(_LIMITATIONS),'source_unchanged':before==after,'source_file_count':count,'replacement_performed':False,'deletion_performed':False,'execution_invoked':False,'approval_created':False,'approval_consumed':False,'authority_granted':False}
