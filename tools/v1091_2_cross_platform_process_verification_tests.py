from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import post_review_development_verify as verify, release_metadata

def require(value,message):
    if not value: raise AssertionError(message)

def run_suite(script: str) -> dict:
    runtime=Path(tempfile.mkdtemp(prefix='eidolon-spawn-runtime-'))
    env=os.environ.copy(); env['EIDOLON_DATA_DIR']=str(runtime); env['PYTHONPATH']=os.pathsep.join([str(ROOT),str(AGENT),str(TOOLS),env.get('PYTHONPATH','')])
    cp=subprocess.run([sys.executable,str(ROOT/script),'--json'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
    try: payload=json.loads(cp.stdout)
    except Exception as exc: raise AssertionError(f'{script} non-json exit={cp.returncode} stdout={cp.stdout[-1000:]} stderr={cp.stderr[-1000:]}') from exc
    require(cp.returncode==0 and payload.get('ok') is True,f'{script}: {payload}')
    return payload

def test_no_unix_only_fork_remains_in_source_or_tests():
    hits=[]
    for base in (AGENT,TOOLS):
        for path in base.rglob('*.py'):
            if path == Path(__file__).resolve():
                continue
            text=path.read_text(encoding='utf-8')
            if "get_context('fork')" in text or 'get_context("fork")' in text or 'os.fork(' in text:
                hits.append(path.relative_to(ROOT).as_posix())
    require(not hits,f'fork-only paths: {hits}')

def test_repair_reference_race_runs_under_spawn():
    report=run_suite('tools/v1089_2_repair_candidate_reference_tests.py')
    require(report['passed']==report['total'],'repair reference spawn race')

def test_triage_race_runs_under_spawn():
    report=run_suite('tools/v1089_4_finding_triage_review_tests.py')
    require(report['passed']==report['total'],'triage spawn race')

def test_current_bundle_registry_is_ordered_and_unique():
    names=[spec.name for spec in verify.SUITES]
    require(len(names)==len(set(names)),'duplicate suite names')
    expected=['v1091.2-cross-platform-process-verification','v1091.1-active-project-truth','v1091.0-bom-aware-json-metadata-migration','v1090.9-desktop-alpha-repair-candidate-review-checkpoint']
    anchor=names.index('v1091.2-cross-platform-process-verification')
    require(names[anchor:anchor+4]==expected,f'anchored order {names[anchor:anchor+4]}')

def test_historical_profile_counts_do_not_block_future_versions():
    names=[spec.name for spec in verify.SUITES]; anchor=names.index('v1090.9-desktop-alpha-repair-candidate-review-checkpoint'); historical=verify.SUITES[anchor:]
    require(sum('core' in spec.profiles for spec in historical)==102,'historical core drift')
    require(sum('full' in spec.profiles for spec in historical)==119,'historical full drift')
    require(sum('core' in spec.profiles for spec in verify.SUITES) >= 105,'current core registration')
    require(sum('full' in spec.profiles for spec in verify.SUITES) >= 122,'current full registration')

def test_release_metadata_docs_and_source_only_boundary():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,2),'version')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
        text=(ROOT/name).read_text(encoding='utf-8'); require('v1091.2' in text,f'{name} missing')
    relative={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')}
    forbidden={'data/projects.json','data/tasks.json','data/memories.json','.git','.venv','venv'}
    require(not(relative&forbidden),str(relative&forbidden))

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.2-cross-platform-process-verification','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
