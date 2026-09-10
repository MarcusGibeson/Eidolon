from __future__ import annotations
import argparse, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; TOOLS=ROOT/'tools'; sys.path[:0]=[str(AGENT),str(TOOLS)]
import dashboard_startup, release_metadata

def require(value,message):
    if not value: raise AssertionError(message)

def test_importtime_parser_orders_major_dependencies():
    sample='''import time: self [us] | cumulative | imported package\nimport time:       100 |        200 | alpha\nimport time:       900 |       1200 | beta\n'''
    rows=dashboard_startup.parse_importtime_output(sample)
    require([row['module'] for row in rows]==['beta','alpha'],rows)
    require(rows[0]['cumulative_seconds']==0.0012,'seconds conversion')

def test_dashboard_import_probe_uses_external_runtime_and_completes():
    report=dashboard_startup.measure_dashboard_import(ROOT,timeout_seconds=30)
    require(report['ok'],report)
    require(0 <= report['import_seconds'] < dashboard_startup.STARTUP_TARGET_SECONDS,report)

def test_dashboard_server_reaches_real_lightweight_route():
    report=dashboard_startup.measure_dashboard_server(ROOT,route='/api/dashboard-chat/active-session',timeout_seconds=30)
    require(report['ok'] and report['status_code']==200,report)
    require(report['below_target'],report)
    require(isinstance(report.get('response_json'),dict) and report['response_json'].get('ok') is True,report)

def test_full_report_has_phase_breakdown():
    report=dashboard_startup.build_dashboard_startup_report(ROOT,runs=1,profile_imports=False)
    require(report['ok'],report)
    require(len(report['import_runs'])==1 and len(report['server_runs'])==1,'phase runs')
    require(report['all_server_runs_below_target'] is True,report)

def test_probe_tool_is_source_immutable_contract():
    text=(ROOT/'conscious_agent'/'dashboard_startup.py').read_text(encoding='utf-8')
    require('EIDOLON_DATA_DIR' in text and 'PYTHONDONTWRITEBYTECODE' in text,'external runtime')
    require('ROOT_DIR' not in text and 'DATA_DIR.mkdir' not in text,'startup probe imported runtime paths')

def test_release_metadata_and_docs():
    require(tuple(int(x) for x in release_metadata.RUNTIME_VERSION.split('.')) >= (1091,3),'version')
    for name in ('README.md','archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md'):
        require('v1091.3' in (ROOT/name).read_text(encoding='utf-8'),f'{name} missing')

TESTS=[(n.removeprefix('test_'),f) for n,f in list(globals().items()) if n.startswith('test_')]
def main():
    argparse.ArgumentParser().add_argument('--json',action='store_true'); checks=[]; passed=0
    for name,fn in TESTS:
        try: fn()
        except Exception as exc: checks.append({'name':name,'status':'fail','message':f'{type(exc).__name__}: {exc}'})
        else: passed+=1; checks.append({'name':name,'status':'pass','message':''})
    report={'suite':'v1091.3-cold-dashboard-startup-measurement','ok':passed==len(TESTS),'status':'pass' if passed==len(TESTS) else 'fail','passed':passed,'total':len(TESTS),'checks':checks}; print(json.dumps(report,indent=2)); return 0 if report['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
