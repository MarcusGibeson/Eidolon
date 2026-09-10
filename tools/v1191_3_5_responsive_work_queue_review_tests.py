from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-neutral-api-'))
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.responsive_work_queue_review_checkpoint import build_responsive_work_queue_review_checkpoint
checks=[];require=lambda v:checks.append(bool(v))
with tempfile.TemporaryDirectory(prefix='eidolon-neutral-runtime-') as temp:
 r=build_responsive_work_queue_review_checkpoint(source_root=ROOT,runtime_root=Path(temp)/'runtime');require(r.get('ok') is True);require(r.get('passed')==r.get('total'));require(r.get('contract_version')=='v1191.5');require(r.get('checkpoint_id')=='responsive-work-queue-review:v1191.5');require(r.get('read_only') is True);require(r.get('post_available') is False);require(r.get('source_unchanged') is True)
 for k in ('execution_invoked','real_work_paused','real_work_cancelled','provider_contacted','model_contacted','thread_started','process_started','approval_created','approval_consumed','authority_granted'):require(r.get(k) is False)
 s=r.get('summary',{});require(s.get('approved_action_count')==6);require(set(s.get('actions',[]))=={'queue','pause','cancel','supersede','complete','present_result'});require(s.get('cancel_presented_state')=='cancelled');require(s.get('result_presented') is True);require(s.get('blocked_case_count',0)>=8)
reg=inspect_checkpoint_registry(source_root=ROOT);d=next((x for x in reg.get('checkpoints',[]) if x.get('checkpoint_id')=='responsive-work-queue-review-checkpoint'),None);require(bool(d));require(d.get('contract_version')=='v1191.5');require(d.get('read_only') is True);require(d.get('post_available') is False)
cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'responsive-work-queue-review-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=120);require(cli.returncode==0);require(json.loads(cli.stdout).get('ok') is True)
status,payload=dispatch_api('GET','/api/cognition/responsive-work-queue-review-checkpoint');require(status==200);require(payload.get('data',{}).get('ok') is True)
status_post,_=dispatch_api('POST','/api/cognition/responsive-work-queue-review-checkpoint');require(status_post in {404,405})
html=render_first_use_shell();require('responsive-work-queue-review-checkpoint-panel' in html);require('/api/cognition/responsive-work-queue-review-checkpoint' in html);require('no real work cancelled' in html)
release=(ROOT/'tools/release_verify.py').read_text();require(release.count('v1191.5-responsive-work-queue-review')==1);require(release.count('tools/v1191_3_5_responsive_work_queue_review_tests.py')==1)
meta=(ROOT/'conscious_agent/release_metadata.py').read_text();require('WORKING_SOURCE_VERSION = "1191.5"' in meta);require('PREVIOUS_WORKING_SOURCE_VERSION = "1191.2"' in meta);require('v1191.6-v1191.8' in meta)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 text=(ROOT/name).read_text();require('Current source: v1191.5' in text);require('v1191.3-v1191.5 Operator Queue Review and Accountable Transitions' in text);require('v1191.6-v1191.8' in text);require('v1200' in text)
result={'suite':'v1191.3-5-responsive-work-queue-review','passed':sum(checks),'total':len(checks),'ok':all(checks)};print(json.dumps(result,sort_keys=True));raise SystemExit(0 if all(checks) else 1)
