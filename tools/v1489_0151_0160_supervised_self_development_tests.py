from __future__ import annotations
import os,sys,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AGENT=ROOT/'conscious_agent';R=Path(tempfile.mkdtemp(prefix='eidolon-v1489-b16-'));SRC=R/'source';SRC.mkdir();(SRC/'agent.py').write_text('VALUE = 1\n');(SRC/'test_agent.py').write_text('assert True\n')
os.environ['EIDOLON_DATA_DIR']=str(R/'runtime');os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True;sys.path.insert(0,str(AGENT))
import supervised_self_development_contract as contract
from supervised_self_development_contract import *
P=F=0
def ck(n,c,d=''):
 global P,F
 if c:P+=1;print('PASS',n)
 else:F+=1;print('FAIL',n,d);raise AssertionError(d or n)
try:
 inv=read_only_inventory(SRC);ck('0151 read-only self inventory',inv['file_count']==2 and not inv['source_mutated'],inv)
 opp=improvement_opportunity(inv);ck('0152 evidence-backed improvement opportunity',opp['evidence_backed'] and opp['opportunity_class']=='bounded_testability_improvement',opp)
 plan=propose_self_change(opp);ck('0153 reversible plan does not authorize modification',plan['reversible'] and not plan['modification_authorized'] and not plan['installation_authorized'],plan)
 denied=create_isolated_workspace(SRC,R/'work',authorized=False);ck('0154 workspace requires explicit authorization',not denied['created'] and denied['reason']=='operator_authorization_required',denied)
 made=create_isolated_workspace(SRC,R/'work',authorized=True);ck('0154 authorized isolated workspace created',made['created'] and not made['authoritative_source_modified'],made)
 nested=R/'data'/'proposal'/'Eidolon';made_nested=create_isolated_workspace(SRC,nested,authorized=True);ck('0154 manifest works beneath data parent',source_manifest(nested)==source_manifest(SRC));ck('0154 inventory works beneath data parent',read_only_inventory(nested)['file_count']==2)
 ignored=SRC/'data'/'large-runtime-tree';ignored.mkdir(parents=True);(ignored/'private.json').write_text('{}')
 walked=[];original_walk=contract.os.walk
 def traced_walk(*args,**kwargs):
  for current,dirs,files in original_walk(*args,**kwargs):walked.append(Path(current).relative_to(SRC).as_posix());yield current,dirs,files
 contract.os.walk=traced_walk
 try:pruned_manifest=source_manifest(SRC)
 finally:contract.os.walk=original_walk
 ck('0154 manifest prunes ignored runtime directories','data/large-runtime-tree' not in walked and 'data/large-runtime-tree/private.json' not in pruned_manifest,walked)
 change=apply_bounded_text_change(R/'work','agent.py','VALUE = 1','VALUE = 2',authorized=True);ck('0155 one bounded isolated change',change['changed'] and (R/'work'/'agent.py').read_text()=='VALUE = 2\n',change)
 ck('0155 authoritative source unchanged',(SRC/'agent.py').read_text()=='VALUE = 1\n')
 # Focused and regression test receipts are inputs to critique, not authority to install.
 crit=critique_result(focused_pass=True,regression_pass=True,known_limitations=['native provider not exercised']);ck('0156 isolated tests can support review',crit['acceptable_for_review'] and not crit['self_install_allowed'],crit)
 ck('0157 self-critique retains limitations',crit['known_limitation_count']==1,crit)
 ev=candidate_evidence(changed_files=['agent.py'],rollback_available=True);ck('0158 candidate and rollback require operator review',ev['rollback_available'] and ev['operator_review_required'] and not ev['self_install_allowed'],ev)
 base=source_manifest(SRC);(SRC/'agent.py').write_text('VALUE = 3\n');now=source_manifest(SRC);race=concurrent_operator_changes(base,now);ck('0159 concurrent operator change detected and protected',race['concurrent_change_detected'] and race['must_reconcile_before_apply'] and not race['overwrite_allowed'],race)
finally:shutil.rmtree(R,ignore_errors=True)
print(f'SUMMARY passed={P} failed={F}');raise SystemExit(1 if F else 0)
