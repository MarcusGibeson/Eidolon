from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.tiered_verification_runtime_v2541 import run_tiered_verification

def main():
    checks=[]
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/'conscious_agent').mkdir(); (r/'tools').mkdir()
        (r/'conscious_agent/__init__.py').write_text('',encoding='utf-8')
        (r/'conscious_agent/feature_widget.py').write_text('VALUE=7\n',encoding='utf-8')
        (r/'tools/v2543_feature_widget_tests.py').write_text('from conscious_agent.feature_widget import VALUE\nraise SystemExit(0 if VALUE==7 else 1)\n',encoding='utf-8')
        result=run_tiered_verification(r,['conscious_agent/feature_widget.py'],through_tier=1,timeout_each_tier1=5)
        checks += [result['ok'],result['through_tier']==1,result['stopped_after_tier']==1,len(result['receipts'])==2]
        checks += [result['receipts'][0]['tier']==0,result['receipts'][1]['tier']==1]
        checks += [not result['source_mutation_authorized'],not result['network_authorized'],not result['release_authorized']]
        checks += [len(result['receipt_digest'])==64]
        (r/'conscious_agent/feature_widget.py').write_text('def broken(:\n',encoding='utf-8')
        failed=run_tiered_verification(r,['conscious_agent/feature_widget.py'],through_tier=2,timeout_each_tier1=5,timeout_each_tier2=5)
        checks += [not failed['ok'],failed['stopped_after_tier']==0,len(failed['receipts'])==1]
    try:
        run_tiered_verification('.', ['conscious_agent/tiered_verification_runtime_v2541.py'], through_tier=3)
        checks.append(False)
    except ValueError:
        checks.append(True)
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
