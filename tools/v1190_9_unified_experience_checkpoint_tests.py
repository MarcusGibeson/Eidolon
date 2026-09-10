from __future__ import annotations
import json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1'); os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1190-9-api-data-'))
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.unified_experience_checkpoint import build_unified_experience_checkpoint
checks=[]; require=lambda v: checks.append(bool(v))
with tempfile.TemporaryDirectory(prefix='eidolon-v1190-9-suite-') as temp:
 r=build_unified_experience_checkpoint(source_root=ROOT,runtime_root=Path(temp)/'runtime')
 expected={'ok':True,'contract_version':'v1190.9','checkpoint_id':'unified-experience:v1190.9','read_only':True,'post_available':False,'content_free':True,'source_modified':False,'runtime_mutated':False,'production_source_modified':False,'sandbox_modified':False,'provider_contacted':False,'model_contacted':False,'automatic_refresh':False,'automatic_recovery':False,'automatic_continuation':False,'approval_created':False,'approval_consumed':False,'execution_invoked':False,'subsystem_state_changed':False,'recovery_executed':False,'policy_modified':False,'future_work_selection_modified':False,'authority_granted':False,'authority_preserved':True,'desktop_verification_deferred_until_v1200':True}
 for k,v in expected.items(): require(r.get(k)==v)
 require(r.get('passed')==r.get('total')); require(r.get('source_signature_before')==r.get('source_signature_after')); require(len(r.get('limitations',[]))==5); require(len(str(r.get('structural_digest','')))==64)
 s=r.get('summary',{}); require(s.get('retained_bundle_count')==3); require(s.get('domain_count')==9); require(s.get('approved_navigation_domain_count')==8); require(s.get('inert_navigation_decision_count')==2); require(s.get('reliability_review_case_count')==12); require(s.get('interruption_class_count')==6); require(s.get('presentation_action_count')==4); require(s.get('blocked_boundary_case_count')==9); require(s.get('initial_focus_domain')=='campaign'); require(s.get('reviewed_focus_domain')=='approval')
reg=inspect_checkpoint_registry(source_root=ROOT); row=next((x for x in reg.get('checkpoints',[]) if x.get('checkpoint_id')=='unified-experience-checkpoint'),None); require(row is not None); require((row or {}).get('contract_version')=='v1190.9'); require((row or {}).get('builder')=='build_unified_experience_checkpoint'); require(not reg.get('duplicate_checkpoint_ids')); require(not reg.get('duplicate_builder_targets'))
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'unified-experience-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=240,env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','EIDOLON_DATA_DIR':tempfile.mkdtemp(prefix='eidolon-v1190-9-cli-')}); require(proc.returncode==0)
if proc.returncode==0:
 cli=json.loads(proc.stdout.strip().splitlines()[-1]); require(cli.get('ok') is True); require(cli.get('contract_version')=='v1190.9'); require(cli.get('passed')==cli.get('total'))
status,payload=dispatch_api('GET','/api/cognition/unified-experience-checkpoint'); require(status==200); require(payload.get('ok') is True); require(payload.get('data',{}).get('contract_version')=='v1190.9'); require(payload.get('data',{}).get('post_available') is False)
status_post,_=dispatch_api('POST','/api/cognition/unified-experience-checkpoint'); require(status_post in {404,405})
html=render_first_use_shell(); require('unified-experience-checkpoint-panel' in html); require('/api/cognition/unified-experience-checkpoint' in html); require('refreshUnifiedExperienceCheckpoint' in html); require('v1191.0-v1191.2' in html)
m=re.search(r'<script>(.*?)</script>',html,re.S); require(m is not None)
if m:
 p=Path(tempfile.mkdtemp(prefix='eidolon-v1190-9-js-'))/'dashboard.js'; p.write_text(m.group(1)); node=subprocess.run(['node','--check',str(p)],text=True,capture_output=True,timeout=60); require(node.returncode==0)
release=(ROOT/'tools/release_verify.py').read_text(); require(release.count('v1190.9-unified-experience-checkpoint')==1); require(release.count('tools/v1190_9_unified_experience_checkpoint_tests.py')==1)
meta=(ROOT/'conscious_agent/release_metadata.py').read_text(); require('WORKING_SOURCE_VERSION = "1190.9"' in meta); require('PREVIOUS_WORKING_SOURCE_VERSION = "1190.8"' in meta); require('v1190.9 Unified Experience Checkpoint' in meta); require('v1191.0-v1191.2 Responsiveness and Background-Work Foundations' in meta); require('WORKING_SOURCE_VERSION = "1190.8"' in meta)
for n in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/n).read_text(); require('Current source: v1190.9' in t); require('v1190.9 Unified Experience Checkpoint' in t); require('v1191.0-v1191.2 Responsiveness and Background-Work Foundations' in t); require('v1200' in t)
print(json.dumps({'suite':'v1190.9-unified-experience-checkpoint','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
