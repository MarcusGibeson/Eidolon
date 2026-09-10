from __future__ import annotations
import json,os,sys,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
from reliability_checkpoint_reliability import *
from v1279_fixture import prepared_operator_experience_chain
from reliability_checkpoint import build_reliability_campaign_matrix
C=[]
def req(v,l):
 if not v:raise AssertionError(l)
 C.append(l)
h=inspect_reliability_checkpoint_health(source_root=ROOT);req(h['ok'] and all(h['checks'].values()),'health');hand=build_reliability_checkpoint_handoff(source_root=ROOT);req(hand['ok'],'handoff');req(hand['next_bounded_unit']=='v1281 Causal Diagnostic Reasoning','next');req(hand['v1281_started'] is False,'unstarted');req(not hand['native_windows_execution_claimed'],'no_fake_windows');req('force_kill_between_stage_and_receipt' in hand['native_windows_review'],'force_kill')
with tempfile.TemporaryDirectory() as td:
 base=Path(td)
 while len(str(base))<285:base=base/('segment_'+'x'*28)
 base.mkdir(parents=True);s=prepared_operator_experience_chain(base,now=300)['snapshot'];req(build_reliability_campaign_matrix(s)['ok'],'long_path_matrix')
code="import sys;from pathlib import Path;sys.path[:0]=[str(Path(r'%s')),str(Path(r'%s')/'conscious_agent')];import reliability_checkpoint_foundations,reliability_checkpoint,reliability_checkpoint_reliability;print('ok')"%(ROOT,ROOT);p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20);req(p.returncode==0 and 'ok' in p.stdout,'fresh_import')
print(json.dumps({'ok':True,'suite':'v1280.6-8-reliability-checkpoint-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
