from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1')
os.environ.setdefault('EIDOLON_DATA_DIR', tempfile.mkdtemp(prefix='eidolon-v1190-5-api-data-'))
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.unified_experience_navigation_checkpoint import build_unified_experience_navigation_checkpoint
checks=[]; require=lambda v: checks.append(bool(v))
with tempfile.TemporaryDirectory(prefix='eidolon-v1190-5-suite-') as temp:
    report=build_unified_experience_navigation_checkpoint(source_root=ROOT,runtime_root=Path(temp)/'runtime')
    for key,val in [('ok',True),('contract_version','v1190.5'),('checkpoint_id','unified-experience-navigation:v1190.5'),('read_only',True),('post_available',False),('content_free',True),('source_modified',False),('runtime_mutated',False),('production_source_modified',False),('sandbox_modified',False),('provider_contacted',False),('model_contacted',False),('automatic_continuation',False),('approval_created',False),('approval_consumed',False),('execution_invoked',False),('authority_granted',False),('authority_preserved',True)]: require(report.get(key)==val)
    require(report.get('passed')==report.get('total')); require(report.get('source_signature_before')==report.get('source_signature_after')); require(len(report.get('limitations',[]))==5); require(len(str(report.get('structural_digest','')))==64)
    summary=report.get('summary',{}); require(summary.get('approved_navigation_count')==1); require(summary.get('rejected_navigation_count')==1); require(summary.get('deferred_navigation_count')==1); require(summary.get('blocked_boundary_case_count')==7); require(summary.get('presented_domain')=='approval')
registry=inspect_checkpoint_registry(source_root=ROOT)
row=next((x for x in registry.get('checkpoints',[]) if x.get('checkpoint_id')=='unified-experience-navigation-checkpoint'),None)
require(row is not None); require((row or {}).get('contract_version')=='v1190.5'); require((row or {}).get('builder')=='build_unified_experience_navigation_checkpoint'); require(not registry.get('duplicate_checkpoint_ids')); require(not registry.get('duplicate_builder_targets'))
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'unified-experience-navigation-checkpoint'],cwd=ROOT,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','EIDOLON_DATA_DIR':tempfile.mkdtemp(prefix='eidolon-v1190-5-cli-')})
require(proc.returncode==0)
try: cli=json.loads(proc.stdout.strip().splitlines()[-1]); require(cli.get('ok') is True); require(cli.get('contract_version')=='v1190.5')
except Exception: require(False); require(False)
status,payload=dispatch_api('GET','/api/cognition/unified-experience-navigation-checkpoint'); require(status==200); require(payload.get('ok') is True); require((payload.get('data') or {}).get('contract_version')=='v1190.5')
status_post,_=dispatch_api('POST','/api/cognition/unified-experience-navigation-checkpoint'); require(status_post in {404,405})
html=render_first_use_shell(); require('unified-experience-navigation-checkpoint-panel' in html); require('/api/cognition/unified-experience-navigation-checkpoint' in html); require('v1190.6-v1190.8' in html)
release=(ROOT/'tools/release_verify.py').read_text(encoding="utf-8"); require(release.count('v1190.5-unified-experience-navigation')==1); require(release.count('v1190_3_5_unified_experience_navigation_tests.py')==1)
metadata=(ROOT/'conscious_agent/release_metadata.py').read_text(encoding="utf-8"); require('WORKING_SOURCE_VERSION = "1190.5"' in metadata); require('PREVIOUS_WORKING_SOURCE_VERSION = "1190.2"' in metadata); require('v1190.6-v1190.8 Unified Experience Reliability and Privacy Hardening' in metadata); require('WORKING_SOURCE_VERSION = "1190.2"' in metadata)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
    text=(ROOT/name).read_text(encoding="utf-8"); require('v1190.5' in text); require('v1190.2' in text); require('v1190.3-v1190.5 Operator Navigation and Coordinated Experience Transitions' in text); require('v1190.6-v1190.8' in text); require('v1200' in text)
result={'suite':'v1190.3-5-unified-experience-navigation','passed':sum(checks),'total':len(checks),'ok':all(checks)}
print(json.dumps(result,sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
