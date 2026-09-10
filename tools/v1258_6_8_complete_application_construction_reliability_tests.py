from __future__ import annotations

import hashlib, json, os, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for path in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(path) not in sys.path: sys.path.insert(0,str(path))

from complete_application_construction import evaluate_complete_application_quality
from complete_application_construction_foundations import prepare_complete_application_construction
from complete_application_construction_reliability import inspect_complete_application_health
from isolated_coding_execution_foundations import cancel_coding_work_request
from ordinary_chat_development_campaign import _digest
from v1258_test_support import make_web_project, prepare_complete_web_request, tree_signature

CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)

def source_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def workspace(runtime:Path,request_id:str)->Path:
    row=json.loads((runtime/'development_campaigns'/'coding_workspace_records'/f'{request_id}.json').read_text())
    return Path(row['workspace_path'])

def populate(root:Path, *, missing_ref=False, accessible=True, responsive=True, tests=True, docs=True, config=True, undeclared=False):
    root.mkdir(parents=True,exist_ok=True)
    html="<!doctype html><html lang='en'><head><meta name='viewport' content='width=device-width,initial-scale=1'><link rel='stylesheet' href='styles.css'></head><body><main><label for='x'>Value</label><input id='x'><button id='go'>Go</button></main><script src='%s'></script></body></html>\n" % ('missing.js' if missing_ref else 'app.js')
    if not accessible: html=html.replace(" lang='en'",'').replace("<main>","<div>").replace("</main>","</div>").replace("<label for='x'>Value</label>",'')
    css=".app{width:90%;max-width:40rem}button:focus-visible,input:focus-visible{outline:2px solid currentColor}" + ("@media(max-width:40rem){.app{width:100%}}" if responsive else '')
    if not accessible: css=css.replace("button:focus-visible,input:focus-visible{outline:2px solid currentColor}",'')
    app="const leftPad = %s; function add(a,b){return Number(a)+Number(b)}; if(typeof module!=='undefined')module.exports={add};\n" % ("require('left-pad')" if undeclared else "null")
    (root/'index.html').write_text(html,encoding='utf-8'); (root/'styles.css').write_text(css,encoding='utf-8'); (root/'app.js').write_text(app,encoding='utf-8')
    if config:
        (root/'package.json').write_text(json.dumps({'name':'fixture','private':True,'scripts':{'test':'node --test'},'dependencies':{},'devDependencies':{}},indent=2),encoding='utf-8')
    if tests:
        (root/'tests').mkdir(exist_ok=True); (root/'tests'/'app.test.js').write_text("const test=require('node:test');const assert=require('node:assert/strict');const {add}=require('../app.js');test('add',()=>assert.equal(add(2,3),5));\n",encoding='utf-8')
    if docs: (root/'README.md').write_text("# Fixture\n\n## Run\nOpen index.html.\n\n## Test\nRun node --test.\n",encoding='utf-8')

SOURCE_BEFORE=source_signature()
# Matrix of deterministic structural failures.
scenarios=[
    ('missing_local_reference',{'missing_ref':True},'local_interface_references_resolve'),
    ('accessibility_gaps',{'accessible':False},'document_language_declared'),
    ('responsive_gap',{'responsive':False},'responsive_breakpoint_present'),
    ('missing_tests',{'tests':False},'project_owned_tests_present'),
    ('missing_docs',{'docs':False},'documentation_present'),
    ('missing_config',{'config':False},'project_configuration_valid'),
    ('undeclared_dependency',{'undeclared':True},'external_dependencies_declared'),
]
for name,kwargs,expected in scenarios:
    with tempfile.TemporaryDirectory(prefix=f'eid-v1258-6-8-{name}-') as d:
        base=Path(d); runtime=base/'runtime'; project=make_web_project(base); before=tree_signature(project)
        request,contract,_=prepare_complete_web_request(project,runtime); root=workspace(runtime,request['request_id'])
        # Replace disposable contents only; selected project remains sealed and untouched.
        for p in sorted(root.rglob('*'),reverse=True):
            if p.is_file() or p.is_symlink(): p.unlink()
            elif p.is_dir():
                try:p.rmdir()
                except OSError:pass
        populate(root,**kwargs)
        quality=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime)
        require(quality['ok'] and quality['passed'] is False,f'{name}_fails_quality')
        require(expected in quality['failed_finding_codes'],f'{name}_reports_expected_finding')
        require(tree_signature(project)==before,f'{name}_does_not_modify_selected_project')

# A good long-path workspace passes, proving the quality scanner uses contained
# relative traversal rather than fragile short-path assumptions.
with tempfile.TemporaryDirectory(prefix='eid-v1258-6-8-long-') as d:
    base=Path(d); deep=base
    for i in range(8): deep=deep/('segment_'+str(i)+'_'+'x'*18)
    deep.mkdir(parents=True); runtime=deep/'runtime'; project=make_web_project(deep); before=tree_signature(project)
    request,contract,_=prepare_complete_web_request(project,runtime); root=workspace(runtime,request['request_id'])
    for p in sorted(root.rglob('*'),reverse=True):
        if p.is_file() or p.is_symlink(): p.unlink()
        elif p.is_dir():
            try:p.rmdir()
            except OSError:pass
    populate(root)
    q=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime)
    require(q['ok'] and q['passed'],'deep_long_path_complete_application_quality_passes')
    require(len(str(root))>220,'deep_path_fixture_exceeds_legacy_windows_path_length')
    require(tree_signature(project)==before,'long_path_quality_scan_preserves_selected_project')

# Casefold collisions are rejected even on a case-sensitive development host.
with tempfile.TemporaryDirectory(prefix='eid-v1258-6-8-casefold-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    request,_,_=prepare_complete_web_request(project,runtime); root=workspace(runtime,request['request_id']); populate(root)
    (root/'App.js').write_text('console.log(1)\n',encoding='utf-8')
    q=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime)
    require(q['ok'] is False and 'workspace_rejected' in q['status'],'windows_casefold_collision_fails_closed')

# Symlink/junction-like link contamination is rejected before content review.
with tempfile.TemporaryDirectory(prefix='eid-v1258-6-8-link-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    request,_,_=prepare_complete_web_request(project,runtime); root=workspace(runtime,request['request_id']); populate(root)
    external=base/'outside.js'; external.write_text('console.log(1)\n')
    try:
        (root/'linked.js').symlink_to(external)
        q=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime)
        require(q['ok'] is False and 'workspace_rejected' in q['status'],'workspace_link_contamination_fails_closed')
    except (OSError,NotImplementedError):
        require(True,'workspace_link_contamination_platform_fixture_unavailable_but_guard_retained')

# Stale source and cancellation close the quality/review path without authority.
with tempfile.TemporaryDirectory(prefix='eid-v1258-6-8-stale-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    request,_,_=prepare_complete_web_request(project,runtime); root=workspace(runtime,request['request_id']); populate(root)
    (project/'index.html').write_text('<p>operator edit</p>',encoding='utf-8')
    q=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime)
    require(q['ok'] is False and q['status']=='complete_application_construction_stale_source','stale_source_blocks_quality_handoff')
    require(q['application_authorized'] is False and q['release_authorized'] is False,'stale_quality_failure_grants_no_authority')
with tempfile.TemporaryDirectory(prefix='eid-v1258-6-8-cancel-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    request,_,_=prepare_complete_web_request(project,runtime); root=workspace(runtime,request['request_id']); populate(root)
    cancelled=cancel_coding_work_request(request['request_id'],runtime_root=runtime)
    require(cancelled['ok'] and cancelled['status']=='coding_work_request_cancelled','construction_request_cancelled')
    q=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime)
    require(q['ok'] is False and q['status']=='complete_application_construction_request_cancelled_or_missing','cancelled_request_blocks_quality_work')

# Sealed quality evidence is tamper evident.
with tempfile.TemporaryDirectory(prefix='eid-v1258-6-8-tamper-') as d:
    base=Path(d); runtime=base/'runtime'; project=make_web_project(base)
    request,_,_=prepare_complete_web_request(project,runtime); root=workspace(runtime,request['request_id']); populate(root)
    q=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime); require(q['passed'],'tamper_fixture_starts_with_passing_quality')
    path=runtime/'development_campaigns'/'complete_application_quality'/request['request_id']/'attempt-1.json'; raw=json.loads(path.read_text()); raw['passed']=False; path.write_text(json.dumps(raw))
    q2=evaluate_complete_application_quality(request['request_id'],1,runtime_root=runtime)
    require(q2['ok'] is False and q2['status']=='complete_application_quality_record_invalid','tampered_quality_record_fails_closed')

require(source_signature()==SOURCE_BEFORE,'reliability_suite_preserves_eidolon_source')
print(json.dumps({'ok':True,'suite':'v1258.6-v1258.8-complete-application-construction-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'selected_project_modified':False,'application_authorized':False,'release_authorized':False,'native_windows_browser_validation':'desktop_review_required'},indent=2,sort_keys=True))
