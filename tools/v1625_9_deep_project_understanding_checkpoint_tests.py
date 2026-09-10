from __future__ import annotations
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
sys.dont_write_bytecode=True
from deep_project_understanding import *

checks=[]
def req(value,name):
    checks.append(name)
    assert value,name

def tree_digest(root:Path):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def python_fixture(base:Path):
    repo=base/'python_repo'; rt=base/'runtime'
    (repo/'pkg').mkdir(parents=True); (repo/'tests').mkdir(); (repo/'config').mkdir()
    (repo/'pkg/__init__.py').write_text('',encoding='utf-8')
    (repo/'pkg/core.py').write_text('def work(x):\n    return x + 1\n',encoding='utf-8')
    (repo/'pkg/service.py').write_text('from pkg.core import work\ndef serve(x):\n    return work(x)\n',encoding='utf-8')
    (repo/'app.py').write_text('from pkg.service import serve\napp = object()\n# source-declared entry candidate\n',encoding='utf-8')
    (repo/'tests/test_core.py').write_text('from pkg.core import work\ndef test_work():\n    assert work(1)==2\n',encoding='utf-8')
    (repo/'tests/test_service.py').write_text('from pkg.service import serve\ndef test_serve():\n    assert serve(1)==2\n',encoding='utf-8')
    (repo/'pyproject.toml').write_text('[project]\nname="fixture"\n',encoding='utf-8')
    (repo/'config/settings.yaml').write_text('mode: test\n',encoding='utf-8')
    (repo/'README.md').write_text('# fixture\n',encoding='utf-8')
    return repo,rt

def js_fixture(base:Path):
    repo=base/'js_repo'; rt=base/'runtime_js'
    (repo/'src').mkdir(parents=True);(repo/'tests').mkdir()
    (repo/'src/math.js').write_text('export function add(a,b){ return a+b; }\n',encoding='utf-8')
    (repo/'src/index.js').write_text("import {add} from './math.js';\nexport const result=add(1,2);\n",encoding='utf-8')
    (repo/'tests/math.test.js').write_text("import {add} from '../src/math.js';\nif(add(1,2)!==3) throw Error('bad');\n",encoding='utf-8')
    (repo/'package.json').write_text('{"name":"fixture","scripts":{"test":"node tests/math.test.js"}}\n',encoding='utf-8')
    return repo,rt

with tempfile.TemporaryDirectory(prefix='eidolon-v1625-9-') as td:
    base=Path(td);repo,rt=python_fixture(base)
    before=tree_digest(repo)
    result=build_deep_repository_model(repo,runtime_root=rt)
    model=result['repository_model']
    req(result['ok'],'model_ok')
    req(result['status']=='deep_repository_model_ready','model_status')
    req(model['contract_version']=='v1625.9','contract')
    req(model['file_count']==9,'file_count')
    req(model['module_count']>=4,'modules')
    req(model['ownership_boundary_count']>=4,'ownership')
    req(model['entry_point_candidate_count']>=1,'entry_point')
    req(model['kind_counts'].get('test')==2,'tests_classified')
    req(model['kind_counts'].get('configuration',0)>=1,'configuration_classified')
    req(model['kind_counts'].get('documentation',0)>=1,'docs_classified')
    req(not model['raw_source_content_exposed'] and not model['source_paths_exposed'],'public_privacy')
    req(not model['live_runtime_verified'] and not model['native_windows_verified'],'native_truth')
    req(not model['provider_contacted'],'no_provider')
    req(not model['action_executed'] and not model['standing_authority_granted'],'no_authority')
    req(tree_digest(repo)==before,'source_immutable_model')

    same=build_deep_repository_model(repo,runtime_root=rt)
    req(same['status']=='deep_repository_model_current','idempotent_current')
    req(assess_repository_model_freshness(repo,runtime_root=rt)['current'],'freshness_current')
    (repo/'pkg/core.py').write_text('def work(x):\n    return x + 2\n',encoding='utf-8')
    fresh=assess_repository_model_freshness(repo,runtime_root=rt)
    req(fresh['status']=='stale','freshness_stale')
    build_deep_repository_model(repo,runtime_root=rt)
    req(assess_repository_model_freshness(repo,runtime_root=rt)['current'],'freshness_rebuilt')

    # Impact reasoning after rebuilt baseline.
    impact_result=build_change_impact_reasoning(repo,['pkg/core.py'],runtime_root=rt)
    impact=impact_result['impact_analysis']
    req(impact_result['ok'],'impact_ok')
    req(impact['known_path_count']==1 and impact['unknown_path_count']==0,'impact_known')
    req(impact['affected_path_count']>=2,'impact_callers')
    req(impact['candidate_test_count']>=1,'impact_tests')
    req(impact['uncertainty_count']==0 and impact['complete'],'impact_complete')
    req(impact['predictions_not_proof'] and not impact['tests_executed'],'impact_truth')
    req(not impact['source_paths_exposed'] and not impact['raw_source_content_exposed'],'impact_privacy')
    req(not impact['action_executed'] and not impact['standing_authority_granted'],'impact_no_authority')

    unknown=build_change_impact_reasoning(repo,['pkg/missing.py'],runtime_root=rt)
    req(not unknown['ok'],'unknown_not_ok')
    req(unknown['status']=='deep_impact_uncertain','unknown_status')
    req(unknown['impact_analysis']['unknown_path_count']==1,'unknown_count')
    req(not unknown['impact_analysis']['complete'],'unknown_incomplete')

    invalid=build_change_impact_reasoning(repo,['../secret.txt'],runtime_root=rt)
    req(not invalid['ok'],'traversal_rejected')
    req(invalid['impact_analysis']['invalid_path_count']==1,'traversal_count')

    ctl=process_deep_project_understanding_control('inspect deep project understanding',project_root=repo,runtime_root=rt)
    req(ctl['active'] and ctl['ok'],'control_inspect')
    impact_ctl=process_deep_project_understanding_control('analyze deep impact: pkg/core.py',project_root=repo,runtime_root=rt)
    req(impact_ctl['active'] and impact_ctl['ok'],'control_impact')
    no_root=process_deep_project_understanding_control('inspect repository model',runtime_root=rt)
    req(no_root['active'] and no_root['status']=='project_root_required','control_root_required')
    compound=process_deep_project_understanding_control('inspect project understanding and install',project_root=repo,runtime_root=rt)
    req(compound['active'] and not compound['ok'] and compound['status']=='read_only_scope_expansion_rejected','compound_rejected')
    req(process_deep_project_understanding_control('tell me a joke')['active'] is False,'ordinary_conversation_ignored')

    # Runtime/private source boundary must be visible as risk but without leaking paths.
    risky=base/'risky'; risky.mkdir();(risky/'main.py').write_text('print(1)\n');(risky/'runtime').mkdir();(risky/'runtime/private.json').write_text('{"x":1}')
    risk=build_deep_repository_model(risky,runtime_root=base/'risk_rt')
    req(not risk['ok'] and risk['status']=='deep_repository_model_boundary_risk','runtime_boundary_detected')
    req(risk['repository_model']['issue_count']>=1,'runtime_issue_public')
    req(not risk['repository_model']['source_paths_exposed'],'runtime_issue_redacted')

    # Portable held-out benchmark spans two project shapes without mutating either.
    js,jsrt=js_fixture(base)
    py_before=tree_digest(repo);js_before=tree_digest(js)
    bench=run_portable_unfamiliar_project_benchmark([
        {'name':'heldout-python','root':repo,'changed_paths':['pkg/core.py'],'expected_minimums':{'file_count':8,'module_count':3,'entry_points':1,'affected_paths':2,'candidate_tests':1}},
        {'name':'heldout-js','root':js,'changed_paths':['src/math.js'],'expected_minimums':{'file_count':4,'module_count':2,'entry_points':1,'affected_paths':1}},
    ],runtime_root=base/'bench_rt')
    b=bench['benchmark']
    req(bench['ok'],'benchmark_ok')
    req(b['project_count']==2,'benchmark_projects')
    req(b['aggregate_score']>=0.75,'benchmark_score')
    req(b['portable_only'] and not b['native_windows_verified'],'benchmark_native_deferred')
    req(not b['operator_trial_completed'],'benchmark_operator_deferred')
    req(not b['source_paths_exposed'] and not b['raw_source_content_exposed'],'benchmark_privacy')
    req(not b['action_executed'] and not b['standing_authority_granted'],'benchmark_authority')
    req(tree_digest(repo)==py_before and tree_digest(js)==js_before,'benchmark_source_immutable')

print(json.dumps({'suite':'v1625.9-deep-project-understanding-checkpoint','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
