from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,source_only_manifest
from isolated_self_modification import execute_isolated_self_modification
from intelligent_test_selection_foundations import prepare_intelligent_test_selection
from iterative_self_repair_foundations import prepare_iterative_self_repair
from iterative_self_repair import execute_iterative_self_repair

def fixture(base: Path)->Path:
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir()
    files={
      'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n',
      'conscious_agent/package_integrity.py':'POLICY=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n',
      'conscious_agent/app.py':'def value():\n    return 1\n',
      'tools/test_app.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"conscious_agent"))\nfrom app import value\nassert value()==1\n',
      'tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'assert True\n',
      'tools/v1247_9_privacy_security_secret_management_audit_tests.py':'assert True\n',
    }
    for rel,text in files.items(): q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    return p

def verified_chain(base: Path):
    p=fixture(base);sm=base/'sm';ts=base/'ts';rr=base/'rr'
    b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'a'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'b'*64}])
    prep=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm)
    done=execute_isolated_self_modification(prep['operation_id'],p,runtime_root=sm,authorization_phrase=prep['authorization_phrase'],provider=lambda r:{'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]})
    sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts)
    repair=prepare_iterative_self_repair(sel['selection_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr)
    calls=[]
    def provider(req):
        calls.append(dict(req));return {'strategy_code':'restore_expected_behavior','changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 1\n# reviewed repair\n'}]}
    result=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=provider)
    return {'source':p,'sm':sm,'ts':ts,'rr':rr,'repair':result,'provider_calls':calls,'active_digest':source_only_manifest(p)['source_manifest_digest']}
