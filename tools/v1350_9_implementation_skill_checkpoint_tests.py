from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from implementation_skill_benchmark import *
from v1350_implementation_skill_test_support import run_real_scenarios
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  base=Path(td);rows=run_real_scenarios(base);r=create_implementation_skill_benchmark(scenarios=rows,source_workspace_digest='f'*64,runtime_root=base/'benchmark');row=r['implementation_skill_benchmark'];req(r['ok'] and row['benchmark_status']=='implementation_skill_ready');req(row['passed_scenario_count']==row['required_scenario_count']==6);req(row['all_required_scenarios_passed']);req(not row['raw_project_content_exposed'] and not row['raw_commands_exposed']);req(all(not IMPLEMENTATION_SKILL_DENIED_AUTHORITY[k] for k in ('network_authorized','dependency_installation_authorized','release_authorized','independent_authority_granted')))
 print({'ok':True,'suite':'v1350.9-implementation-skill-checkpoint','passed':p,'total':5})
if __name__=='__main__':main()
