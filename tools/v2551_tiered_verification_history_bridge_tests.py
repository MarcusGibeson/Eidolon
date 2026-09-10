from pathlib import Path
import tempfile
from conscious_agent.tiered_verification_history_bridge_v2551 import *
from conscious_agent.verification_history_v2547 import load_history

def main():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'repo';(root/'pkg').mkdir(parents=True);(root/'pkg/a.py').write_text('x=1\n');(root/'tools').mkdir(); hp=Path(td)/'runtime/history.json'
        out=run_tiered_verification_with_history(root,['pkg/a.py'],history_path=hp,through_tier=0)
        # Tier 0 has no per-test observations, which is intentional.
        checks=[out['ok'],out['observation_count']==0,out['history_path_exposed'] is False,out['raw_output_stored'] is False,out['required_test_waiver_authorized'] is False,out['release_authorized'] is False,load_history(hp)=={}]
    print({'suite':'v2551-tiered-history-bridge','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
