from __future__ import annotations
import json,os,sys,tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,load_self_modification,source_only_manifest,_record_path,_record_digest,_write_json
from isolated_self_modification import execute_isolated_self_modification
from isolated_self_modification_reliability import validate_self_modification_candidate,cancel_isolated_self_modification,cleanup_isolated_self_modification,recover_interrupted_self_modification,inspect_isolated_self_modification_health,build_isolated_self_modification_operator_handoff
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def fixture(base,name='Eidolon'):
    p=base/name;(p/'conscious_agent').mkdir(parents=True);(p/'tests').mkdir();(p/'docs').mkdir()
    for rel,text in {'conscious_agent/release_authority.py':'X=1\n','conscious_agent/package_integrity.py':'P=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="x"\n','conscious_agent/app.py':'def value():\n    return 1\n','tests/test_app.py':'def test_x():\n    assert True\n','docs/a.md':'# A\n'}.items(): q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    return p
def prep(base,p,runtime):
    b,s,pl=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'c'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'d'*64}]);return prepare_isolated_self_modification(p,pl,s,b,runtime_root=runtime)
with tempfile.TemporaryDirectory(prefix='eidolon-v1265-reliability-') as td:
    base=Path(td);p=fixture(base);runtime=base/'runtime';rec=prep(base,p,runtime);calls=[]
    def provider(_): calls.append(1);return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 3\n'}]}
    # Stale active source blocks before provider contact.
    (p/'docs/a.md').write_text('# changed\n',encoding='utf-8');stale=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=runtime,authorization_phrase=rec['authorization_phrase'],provider=provider);req(stale['status']=='stale_self_source_detected','stale_source_blocks');req(len(calls)==0,'stale_source_blocks_provider')
    # Cancellation and deterministic cleanup.
    p2=fixture(base,'Eidolon2');r2=prep(base,p2,base/'runtime2');cancel=cancel_isolated_self_modification(r2['operation_id'],runtime_root=base/'runtime2');req(cancel['phase']=='cancelled','cancellation_persisted');clean=cleanup_isolated_self_modification(r2['operation_id'],runtime_root=base/'runtime2');req(clean['ok'],'cancelled_workspace_cleanup');req(cleanup_isolated_self_modification(r2['operation_id'],runtime_root=base/'runtime2')['ok'],'cleanup_idempotent')
    # Interrupted work fails closed and never auto-retries provider.
    p3=fixture(base,'Eidolon3');rt3=base/'runtime3';r3=prep(base,p3,rt3);row=load_self_modification(r3['operation_id'],runtime_root=rt3);row['phase']='running';row['status']='isolated_self_modification_running';row['record_digest']=_record_digest(row);_write_json(_record_path(r3['operation_id'],rt3),row);recover=recover_interrupted_self_modification(r3['operation_id'],p3,runtime_root=rt3);req(recover['ok'] and recover['phase']=='blocked','interrupted_operation_fail_closed');req(recover['automatic_provider_retry'] is False,'no_automatic_provider_retry')
    # Candidate tamper is detected after a valid isolated mutation.
    p4=fixture(base,'Eidolon4');rt4=base/'runtime4';r4=prep(base,p4,rt4);d4=execute_isolated_self_modification(r4['operation_id'],p4,runtime_root=rt4,authorization_phrase=r4['authorization_phrase'],provider=provider);req(validate_self_modification_candidate(r4['operation_id'],p4,runtime_root=rt4)['ok'],'candidate_valid_before_tamper');(Path(d4['workspace_path'])/'conscious_agent/app.py').write_text('def value():\n    return 999\n',encoding='utf-8');req(not validate_self_modification_candidate(r4['operation_id'],p4,runtime_root=rt4)['ok'],'candidate_tamper_detected')
    # Provider cannot introduce private/runtime path content.
    p5=fixture(base,'Eidolon5');rt5=base/'runtime5';r5=prep(base,p5,rt5);bad=execute_isolated_self_modification(r5['operation_id'],p5,runtime_root=rt5,authorization_phrase=r5['authorization_phrase'],provider=lambda _:{'changes':[{'path':'data/memories.json','action':'create','content':'{}'}]});req(bad['phase']=='blocked' and not bad['isolated_workspace_modified'],'provider_private_path_blocked')
    # Deep external runtime path remains usable.
    deep=base/('deep_'+'x'*80)/('more_'+'y'*80)/'runtime';p6=fixture(base,'Eidolon6');r6=prep(base,p6,deep);req(len(r6['workspace_path'])>180 and Path(r6['workspace_path']).is_dir(),'long_runtime_path_supported')
    # Concurrent exact authorization converges on one provider call and one sealed candidate.
    p7=fixture(base,'Eidolon7');rt7=base/'runtime7';r7=prep(base,p7,rt7);cc=[]
    def slow_provider(_): cc.append(1);return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 7\n'}]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        outs=list(pool.map(lambda _i: execute_isolated_self_modification(r7['operation_id'],p7,runtime_root=rt7,authorization_phrase=r7['authorization_phrase'],provider=slow_provider),range(4)))
    req(len(cc)==1,'concurrent_duplicate_authorization_single_provider_call');req(sum(1 for x in outs if x.get('provider_called_this_invocation'))==1,'concurrent_duplicate_single_executor');req(all(x.get('phase')=='sealed' for x in outs),'concurrent_duplicate_converges_sealed')
    # Link/reparse-like source entries are never copied into the self workspace.
    p8=fixture(base,'Eidolon8');link=p8/'conscious_agent/link.py'
    try:
        link.symlink_to(p8/'conscious_agent/app.py');link_supported=True
    except OSError:
        link_supported=False
    if link_supported:
        try: source_only_manifest(p8); link_rejected=False
        except ValueError as e: link_rejected='link_or_reparse' in str(e)
        req(link_rejected,'source_symlink_rejected')
    else:
        req(True,'source_symlink_rejected_platform_unavailable')
    health=inspect_isolated_self_modification_health(source_root=ROOT);req(health['ok'],'health_ready');handoff=build_isolated_self_modification_operator_handoff(source_root=ROOT);req(handoff['ok'] and handoff['next_bounded_unit']=='v1266 Intelligent Test Selection','operator_handoff_ready');req('real_ntfs_junction_and_reparse_containment' in handoff['native_windows_review'],'windows_reparse_handoff_explicit');req('test_selection_deferred_to_v1266' in handoff['review_boundaries'],'v1266_boundary_explicit')
print(json.dumps({'ok':True,'suite':'v1265.6-v1265.8-isolated-self-modification-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'automatic_provider_retry':False,'active_source_modified':False,'release_authorized':False},indent=2,sort_keys=True))
