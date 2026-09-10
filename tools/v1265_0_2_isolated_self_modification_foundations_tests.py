from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
import isolated_self_modification_foundations as foundations
from isolated_self_modification_foundations import SELF_MODIFICATION_DENIED_AUTHORITY,prepare_isolated_self_modification,source_only_manifest,source_only_manifest_from_content_digests,validate_self_modification_foundation,check_self_source_freshness
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def tree_sig(root):
    rows=[]
    paths=[]
    for current,dirs,files in os.walk(root,topdown=True,followlinks=False):
        dirs[:]=sorted(name for name in dirs if name.casefold() not in {'data','.git','.venv','venv','__pycache__'})
        paths.extend(Path(current)/name for name in files)
    for p in sorted(paths):
        if p.is_file() and not p.is_symlink(): rows.append((p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tests').mkdir();(p/'docs').mkdir();(p/'data').mkdir()
    (p/'conscious_agent/release_authority.py').write_text('WORKING_SOURCE_VERSION="fixture"\n',encoding='utf-8');(p/'conscious_agent/package_integrity.py').write_text('POLICY=True\n',encoding='utf-8');(p/'README_NEXT_STEPS.md').write_text('next\n',encoding='utf-8');(p/'pyproject.toml').write_text('[project]\nname="demo"\n',encoding='utf-8');(p/'conscious_agent/app.py').write_text('def value():\n    return 1\n',encoding='utf-8');(p/'tests/test_app.py').write_text('def test_value():\n    assert True\n',encoding='utf-8');(p/'docs/architecture.md').write_text('# Architecture\n',encoding='utf-8');(p/'data/private.json').write_text('{"memory":"never copy"}\n',encoding='utf-8')
    return p
def repair_plan(p):
    return generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'1'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'2'*64}])
before_root=tree_sig(ROOT)
with tempfile.TemporaryDirectory(prefix='eidolon-v1265-foundations-') as td:
    base=Path(td);p=fixture(base);runtime=base/'runtime';before=tree_sig(p)
    walked=[];original_walk=foundations.os.walk
    def traced_walk(*args,**kwargs):
        for current,dirs,files in original_walk(*args,**kwargs):walked.append(Path(current).relative_to(p).as_posix());yield current,dirs,files
    foundations.os.walk=traced_walk
    try: manifest=source_only_manifest(p)
    finally: foundations.os.walk=original_walk
    req('data' not in walked,'private_runtime_tree_pruned_before_traversal')
    verified={row['relative_path']:row['content_digest'] for row in manifest['files']}
    rebound=source_only_manifest_from_content_digests(p,verified);req(rebound==manifest,'preverified_content_map_rebinds_to_strict_manifest')
    missing=dict(verified);missing.pop(next(iter(missing)))
    try:source_only_manifest_from_content_digests(p,missing);mismatch_raised=False
    except ValueError as e:mismatch_raised='preverified_' in str(e)
    req(mismatch_raised,'preverified_content_map_path_mismatch_rejected')
    req(manifest['file_count']>=7,'source_inventory_present');req(all(not x['relative_path'].startswith('data/') for x in manifest['files']),'private_data_excluded_from_manifest')
    b,s,plan=repair_plan(p);req(plan['category']=='reliability_candidate','repair_plan_selected')
    rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=runtime);req(rec['status']=='isolated_self_modification_authorization_required','foundation_prepared');req(rec['mutation_candidate'],'mutation_candidate_exact')
    req(validate_self_modification_foundation(rec)['ok'],'foundation_record_valid');req(Path(rec['workspace_path']).is_dir(),'clean_workspace_materialized');req(not (Path(rec['workspace_path'])/'data').exists(),'private_runtime_not_copied')
    req(source_only_manifest(Path(rec['workspace_path']))['source_manifest_digest']==manifest['source_manifest_digest'],'clean_copy_manifest_exact');req(tree_sig(p)==before,'active_source_immutable_during_prepare');req(check_self_source_freshness(rec['operation_id'],p,runtime_root=runtime)['ok'],'source_freshness_current')
    restored=prepare_isolated_self_modification(p,plan,s,b,runtime_root=runtime);req(restored['operation_id']==rec['operation_id'] and restored['operation_status']=='restored','duplicate_prepare_idempotent');req(restored['workspace_path']==rec['workspace_path'],'duplicate_reuses_workspace')
    for k,v in SELF_MODIFICATION_DENIED_AUTHORITY.items(): req(rec[k] is v,f'{k}_denied')
    # A read-only evidence-acquisition plan must not become self-mutation work.
    bb,ss,pp=generate_priority_and_alternative_plan(p);readonly=prepare_isolated_self_modification(p,pp,ss,bb,runtime_root=base/'runtime2');req(readonly['status']=='self_modification_not_applicable_read_only_plan' and not readonly['mutation_candidate'],'evidence_plan_not_promoted_to_mutation')
    # Casefold ambiguity fails before workspace materialization.
    (p/'conscious_agent/App.py').write_text('x=1\n',encoding='utf-8')
    try: source_only_manifest(p); raised=False
    except ValueError as e: raised='casefold' in str(e)
    same_entry=os.path.samefile(p/'conscious_agent/App.py',p/'conscious_agent/app.py')
    req(not raised if same_entry else raised,'casefold_collision_rejected_when_filesystem_can_represent_it')
req(tree_sig(ROOT)==before_root,'foundation_suite_preserves_repository')
print(json.dumps({'ok':True,'suite':'v1265.0-v1265.2-isolated-self-modification-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'active_source_modified':False,'private_runtime_copied':False,'release_authorized':False},indent=2,sort_keys=True))
