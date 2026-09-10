from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.knowledge_maintenance_consolidation import build_knowledge_maintenance_consolidation

def run():
 with tempfile.TemporaryDirectory() as td:
  x=build_knowledge_maintenance_consolidation(Path(td)/'cognition')
  checks=[('ready',x['status']=='ready_for_v1106_9_checkpoint'),('twelve_checks',x['check_count']==12),('all_pass',all(c['passed'] for c in x['checks'])),('read_only',x['runtime_mutated'] is False),('provider_free',x['provider_contacted'] is False),('no_browsing',x['external_browsing_performed'] is False),('authority_unchanged',x['action_authority_changed'] is False),('not_promoted',x['release_promoted'] is False),('not_certified',x['release_certified'] is False),('no_consciousness_claim',x['consciousness_claimed'] is False),('reflection_visible','reflections' in x),('outcomes_visible','outcomes' in x)]
  return checks
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');
 r=run();print(json.dumps({'ok':all(v for _,v in r),'passed':sum(v for _,v in r),'total':len(r),'checks':[{'name':n,'passed':v} for n,v in r]}));raise SystemExit(0 if all(v for _,v in r) else 1)
