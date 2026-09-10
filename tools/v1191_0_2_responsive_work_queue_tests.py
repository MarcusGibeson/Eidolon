from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-neutral-api-'))
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.responsive_work_queue_checkpoint import build_responsive_work_queue_checkpoint
checks=[];require=lambda v:checks.append(bool(v))
with tempfile.TemporaryDirectory(prefix='eidolon-neutral-runtime-') as temp:
 r=build_responsive_work_queue_checkpoint(source_root=ROOT,runtime_root=Path(temp)/'runtime')
 require(r.get('ok') is True);require(r.get('passed')==r.get('total'));require(r.get('contract_version')=='v1191.2');require(r.get('checkpoint_id')=='responsive-work-queue:v1191.2');require(r.get('read_only') is True);require(r.get('post_available') is False);require(r.get('source_unchanged') is True)
 for k in ('execution_invoked','cancellation_invoked','provider_contacted','model_contacted','thread_started','process_started','approval_consumed','authority_granted'):require(r.get(k) is False)
 s=r.get('summary',{});require(s.get('item_count')==4);require(s.get('foreground_unblocked') is True);require(s.get('deterministic_order') is True);require(set(s.get('work_classes',[]))=={'foreground_interaction','background_cognition','background_campaign_review','deferred_maintenance'})
 require(len(r.get('blocked_cases',{}))>=8)
reg=inspect_checkpoint_registry(source_root=ROOT);d=next((x for x in reg.get('checkpoints',[]) if x.get('checkpoint_id')=='responsive-work-queue-checkpoint'),None);require(bool(d));require(d.get('contract_version')=='v1191.2');require(d.get('read_only') is True);require(d.get('post_available') is False)
cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'responsive-work-queue-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=120);require(cli.returncode==0);require(json.loads(cli.stdout).get('ok') is True)
status,payload=dispatch_api('GET','/api/cognition/responsive-work-queue-checkpoint');require(status==200);require(payload.get('data',{}).get('ok') is True)
status_post,_=dispatch_api('POST','/api/cognition/responsive-work-queue-checkpoint');require(status_post in {404,405})
html=render_first_use_shell();require('responsive-work-queue-checkpoint-panel' in html);require('/api/cognition/responsive-work-queue-checkpoint' in html);require('no work executed' in html)
release=(ROOT/'tools/release_verify.py').read_text();require(release.count('v1191.2-responsive-work-queue-foundations')==1);require(release.count('tools/v1191_0_2_responsive_work_queue_tests.py')==1)
meta=(ROOT/'conscious_agent/release_metadata.py').read_text();require('WORKING_SOURCE_VERSION = "1191.2"' in meta);require('PREVIOUS_WORKING_SOURCE_VERSION = "1190.9"' in meta);require('v1191.3-v1191.5' in meta)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 text=(ROOT/name).read_text();require('Current source: v1191.2' in text);require('v1191.0-v1191.2 Responsiveness and Background-Work Foundations' in text);require('v1191.3-v1191.5' in text);require('v1200' in text)
result={'suite':'v1191.0-2-responsive-work-queue-foundations','passed':sum(checks),'total':len(checks),'ok':all(checks)};print(json.dumps(result,sort_keys=True));raise SystemExit(0 if all(checks) else 1)
