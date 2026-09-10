from __future__ import annotations
from datetime import datetime, timezone, timedelta
import json, tempfile
from pathlib import Path
from conscious_agent.decision_review_registry import (
    record_decision_review_candidates, inspect_decision_review_registry,
    build_operator_approval_preview,
)


def _boundary(prop='preview the repair in a sandbox', risk='low', rev='high'):
    return {'cases':[{'boundary_id':'b1','state':'candidate_recommendation','candidate_option_id':'o1','candidate_proposition':prop,'evidence_sufficient':True,'prerequisites_complete':True,'risk_level':risk,'reversibility':rev,'operator_approval_required':True}]}


def run():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'cognition'
        rec=record_decision_review_candidates(operation_id='op1',session_id='s1',boundary=_boundary(),runtime_root=root)
        item=rec['review_items'][0]
        checks += [rec['contract_version'] in {'v1154.8','v1154.9'}, bool(item['candidate_digest']), len(item['candidate_digest'])==64, bool(rec['record_digest'])]
        preview=build_operator_approval_preview(operation_id='op1',review_item_id=item['review_item_id'],expected_candidate_digest=item['candidate_digest'],runtime_root=root)
        checks += [preview['status']=='ready_for_operator_review',preview['exact_candidate_bound'],preview['read_only'],not preview['approval_created'],not preview['approval_granted'],not preview['decision_created'],not preview['execution_permitted'],not preview['action_authority']]
        mismatch=build_operator_approval_preview(operation_id='op1',review_item_id=item['review_item_id'],expected_candidate_digest='0'*64,runtime_root=root)
        checks += [mismatch['status']=='candidate_digest_mismatch',not mismatch['approval_created']]
        blocked=record_decision_review_candidates(operation_id='op2',session_id='s1',boundary=_boundary('replace production immediately','high','unknown'),runtime_root=root)
        bi=blocked['review_items'][0]
        bp=build_operator_approval_preview(operation_id='op2',review_item_id=bi['review_item_id'],expected_candidate_digest=bi['candidate_digest'],runtime_root=root)
        checks += [bp['status']=='blocked_for_more_detail',not bp['approval_created']]
        path=root/'decision_review_registry.json'
        state=json.loads(path.read_text())
        state['records'][0]['created_at']=(datetime.now(timezone.utc)-timedelta(days=20)).isoformat().replace('+00:00','Z')
        from conscious_agent.decision_review_registry import _digest
        state['records'][0]['record_digest']=_digest({k:v for k,v in state['records'][0].items() if k!='record_digest'})
        path.write_text(json.dumps(state),encoding='utf-8')
        stale=build_operator_approval_preview(operation_id='op1',review_item_id=item['review_item_id'],expected_candidate_digest=item['candidate_digest'],runtime_root=root)
        inspect=inspect_decision_review_registry(root)
        checks += [stale['status']=='stale_candidate',inspect['stale_count']==1,not inspect['content_exposed'],inspect['authority_preserved']]
        # Pending recovery: move a complete record into pending and retry.
        state=json.loads(path.read_text()); moved=state['records'].pop(); state['pending']=[{'operation_id':'op2','record':moved,'staged_at':'x','content_free':False}]; path.write_text(json.dumps(state),encoding='utf-8')
        recovered=record_decision_review_candidates(operation_id='op2',session_id='s1',boundary=_boundary('replace production immediately','high','unknown'),runtime_root=root)
        state=json.loads(path.read_text())
        checks += [recovered['operation_id']=='op2',len([r for r in state['records'] if r.get('operation_id')=='op2'])==1,len(state['pending'])==0]
        # Malformed stores are reported, never silently treated as healthy empty state.
        path.write_text('{bad json',encoding='utf-8')
        malformed=inspect_decision_review_registry(root)
        checks += [malformed['malformed'],malformed['review_required'],not malformed['content_exposed']]
    print(f'v1154.6-v1154.8 decision-boundary reliability tests: {sum(bool(x) for x in checks)}/{len(checks)}')
    if not all(checks):
        print([i+1 for i,x in enumerate(checks) if not x]); raise SystemExit(1)

if __name__=='__main__': run()
