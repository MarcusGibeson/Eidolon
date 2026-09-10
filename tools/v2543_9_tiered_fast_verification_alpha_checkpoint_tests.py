from __future__ import annotations
import tempfile
from pathlib import Path
from conscious_agent.tiered_verification_runtime_v2541 import build_tiered_verification_plan, run_tier0, run_tiered_verification

def main():
    root=Path('.').resolve()
    changed=['conscious_agent/cognitive_observability_v2533.py','conscious_agent/dashboard.py']
    checks=[]
    plan=build_tiered_verification_plan(root,changed)
    checks += [plan['ok'], plan['tiers']['0']['target_seconds']==5, plan['tiers']['1']['target_seconds']==30, plan['tiers']['2']['target_seconds']==120]
    checks += [plan['tier1_test_count']<=6, plan['tier2_test_count']<=8]
    checks += [not plan['release_authorized'], not plan['network_authorized'], not plan['source_mutation_authorized']]
    checks += [plan['tiers']['3']['name']=='release-certification', plan['tiers']['3']['bounded_by_existing_verifiers']]
    t0=run_tier0(root,changed)
    checks += [t0['ok'], t0['external_process_spawned'] is False]
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); (r/'conscious_agent').mkdir(); (r/'tools').mkdir()
        (r/'conscious_agent/__init__.py').write_text('',encoding='utf-8')
        (r/'conscious_agent/feature_widget.py').write_text('VALUE=7\n',encoding='utf-8')
        (r/'tools/v2543_feature_widget_tests.py').write_text('from conscious_agent.feature_widget import VALUE\nraise SystemExit(0 if VALUE==7 else 1)\n',encoding='utf-8')
        result=run_tiered_verification(r,['conscious_agent/feature_widget.py'],through_tier=1,timeout_each_tier1=5)
        checks += [result['ok'],result['stopped_after_tier']==1,len(result['receipts'])==2]
        checks += [all(not x.get('release_authorized',True) for x in result['receipts'])]
    passed=sum(bool(x) for x in checks)
    print({'suite':'v2543.9-tiered-fast-verification-alpha-checkpoint','ok':passed==len(checks),'passed':passed,'total':len(checks)})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
