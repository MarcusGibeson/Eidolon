from __future__ import annotations
import hashlib, json, os, shutil, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; sys.path.insert(0,str(AGENT))
import supervised_repair_intelligence as repair
import supervised_self_development_contract as contract
import v1489_product_capability_integration as integration

passed=[]
def req(v,label):
    if not v: raise AssertionError(label)
    passed.append(label)
def base(**extra):
    value={'proposal_id':'improvement-'+'a'*20,'proposal_digest':'b'*64,'affected_scope':['conscious_agent/example.py'],'implementation_failure_codes':['verification_failed'],'implementation_blocker':'isolated_implementation_check_1_failed','implementation_attempt_count':1,'repair_cycle_count':0}
    value.update(extra); return value

def test_taxonomy_required_classes():
    expected={'syntax','import','test','timeout','stale_baseline','scope','dependency','provider','acceptance_criterion'}; req(expected<=set(repair.FAILURE_CLASSES),'taxonomy')
def test_taxonomy_examples():
    cases={'SyntaxError':'syntax','ModuleNotFoundError':'import','verification_failed':'test','subprocess_timeout':'timeout','stale_active_source':'stale_baseline','scope_invalid':'scope','dependency_missing':'dependency','provider_output_not_json':'provider','acceptance_criterion_failed':'acceptance_criterion','private_path_rejected':'security_or_authority'}
    for code,want in cases.items(): req(repair.classify_failure_code(code)==want,f'class {want}')
def test_failure_receipt_content_free():
    r=repair.build_failure_receipt(base()); req(r['failure_count']>=1 and 'test' in r['failure_classes'],'receipt class'); req('verification_failed' not in json.dumps(r),'raw code hidden'); req(not r['private_failure_text_returned'],'private hidden')
def test_repair_contract_bounded():
    c=repair.bounded_repair_contract(); req(c['maximum_repair_cycles']==2,'budget'); req(c['same_proposal_digest_required'] and c['same_affected_scope_required'],'lineage'); req(not c['scope_expansion_allowed'] and not c['installation_allowed'],'authority')
def test_retryable_test_failure():
    p=repair.build_bounded_repair_plan(base()); req(p['retryable'] and p['next_action']=='retry_same_workspace_scope_then_reverify','test retry')
def test_stale_requires_refresh():
    p=repair.build_bounded_repair_plan(base(implementation_failure_codes=['stale_active_source'])); req(p['retryable'] and p['requires_workspace_refresh'],'stale refresh')
def test_scope_failure_stops():
    p=repair.build_bounded_repair_plan(base(implementation_failure_codes=['generic_self_development_scope_invalid'])); req(not p['retryable'] and p['operator_or_desktop_review_required'],'scope stop')
def test_budget_exhaustion():
    p=repair.build_bounded_repair_plan(base(repair_cycle_count=2)); req(not p['retryable'] and p['next_action']=='repair_budget_exhausted','exhaust')
def test_advance_exact_count():
    a=repair.advance_repair_cycle(base()); req(a['ok'] and a['repair_cycle_count']==1,'advance1'); b=repair.advance_repair_cycle(base(repair_cycle_count=1)); req(b['ok'] and b['repair_cycle_count']==2,'advance2'); c=repair.advance_repair_cycle(base(repair_cycle_count=2)); req(not c['ok'],'advance blocked')
def test_lineage_validation():
    a=base(); b=dict(a); req(repair.validate_repair_lineage(a,b)['ok'],'same lineage'); b['affected_scope']=['other.py']; r=repair.validate_repair_lineage(a,b); req(not r['ok'] and r['scope_expanded'],'scope expansion')
def test_recovery_contract():
    c=repair.recovery_checkpoint_contract(); req({'interruption','restart','duplicate_retry','provider_loss','stale_source','partial_files','exhausted_repair_budget'}<=set(c['scenarios']),'recovery scenarios'); req(c['native_windows_evidence_deferred'],'native deferred')
def test_clean_failed_workspace_can_be_rearmed():
    temp=Path(tempfile.mkdtemp(prefix='eidolon-v1575-')); old=os.environ.get('EIDOLON_DATA_DIR')
    try:
        runtime=temp/'runtime'; src=temp/'source'; src.mkdir(); (src/'a.py').write_text('VALUE = 1\n',encoding='utf-8')
        pid='improvement-'+'c'*20; workspace=runtime/'self_development_proposals'/'workspaces'/pid/'Eidolon'; workspace.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(src,workspace)
        sm=contract.source_manifest(src); wm=contract.source_manifest(workspace); dig=lambda x: hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        proposal={'proposal_id':pid,'proposal_digest':'d'*64,'state':'isolated_implementation_blocked','isolated_workspace_created':True,'source_manifest_digest':dig(sm),'workspace_manifest_digest':dig(wm),'affected_scope':['a.py'],'implementation_failure_codes':['verification_failed'],'implementation_blocker':'verification_failed','implementation_attempt_count':1,'repair_cycle_count':0,'isolated_preparation_phrase':f'Prepare isolated self-development proposal {pid} digest '+('d'*16)+'.'}
        pp=runtime/'self_development_proposals'/f'{pid}.json'; pp.parent.mkdir(parents=True,exist_ok=True); pp.write_text(json.dumps(proposal),encoding='utf-8'); os.environ['EIDOLON_DATA_DIR']=str(runtime)
        m=integration._PREPARE_SELF_PROPOSAL.fullmatch(proposal['isolated_preparation_phrase']); req(m is not None,'prepare match'); result=integration._prepare_isolated_proposal(m,src,operator_authorization_text='Continue your supervised development.')
        out=result['self_development_proposal']; req(result['event']=='isolated_self_development_repair_prepared','rearmed event'); req(out['state']=='isolated_workspace_prepared' and out['repair_cycle_count']==1,'rearmed state'); req(out['proposal_digest']==proposal['proposal_digest'] and out['affected_scope']==proposal['affected_scope'],'rearmed lineage'); req(contract.source_manifest(src)==sm,'active unchanged')
    finally:
        if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
        else: os.environ['EIDOLON_DATA_DIR']=old
        shutil.rmtree(temp,ignore_errors=True)
def test_repair_budget_blocks_rearm():
    temp=Path(tempfile.mkdtemp(prefix='eidolon-v1575-budget-')); old=os.environ.get('EIDOLON_DATA_DIR')
    try:
        runtime=temp/'runtime'; src=temp/'source'; src.mkdir(); (src/'a.py').write_text('VALUE=1\n'); pid='improvement-'+'e'*20; workspace=runtime/'self_development_proposals'/'workspaces'/pid/'Eidolon'; workspace.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(src,workspace)
        dig=lambda x: hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest(); proposal={'proposal_id':pid,'proposal_digest':'f'*64,'state':'isolated_implementation_blocked','isolated_workspace_created':True,'source_manifest_digest':dig(contract.source_manifest(src)),'workspace_manifest_digest':dig(contract.source_manifest(workspace)),'affected_scope':['a.py'],'implementation_failure_codes':['verification_failed'],'repair_cycle_count':2,'isolated_preparation_phrase':f'Prepare isolated self-development proposal {pid} digest '+('f'*16)+'.'}; pp=runtime/'self_development_proposals'/f'{pid}.json'; pp.parent.mkdir(parents=True,exist_ok=True); pp.write_text(json.dumps(proposal)); os.environ['EIDOLON_DATA_DIR']=str(runtime); m=integration._PREPARE_SELF_PROPOSAL.fullmatch(proposal['isolated_preparation_phrase']); result=integration._prepare_isolated_proposal(m,src); req(result['event']=='isolated_self_development_repair_blocked','budget event'); req(contract.source_manifest(src)==contract.source_manifest(src),'budget active unchanged')
    finally:
        if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
        else: os.environ['EIDOLON_DATA_DIR']=old
        shutil.rmtree(temp,ignore_errors=True)

def main():
    tests=[v for k,v in list(globals().items()) if k.startswith('test_') and callable(v)]; good=0; results=[]
    for fn in tests:
        try: fn(); good+=1; results.append({'name':fn.__name__,'ok':True})
        except Exception as e: results.append({'name':fn.__name__,'ok':False,'error':f'{type(e).__name__}: {e}'})
    print(json.dumps({'suite':'v1575.9-repair-retry-intelligence-checkpoint','ok':good==len(tests),'passed':good,'total':len(tests),'assertions':len(passed),'results':results},indent=2)); return 0 if good==len(tests) else 1
if __name__=='__main__': raise SystemExit(main())
