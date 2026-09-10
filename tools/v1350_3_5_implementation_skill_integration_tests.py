from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from implementation_skill_benchmark import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1350_implementation_skill_test_support import run_real_scenarios
def main():
 p=0
 def req(v):nonlocal p;assert v;p+=1
 with tempfile.TemporaryDirectory() as td:
  base=Path(td);rows=run_real_scenarios(base);req(len(rows)==6 and all(x['ok'] for x in rows));r=create_implementation_skill_benchmark(scenarios=rows,source_workspace_digest='e'*64,runtime_root=base/'benchmark');row=r['implementation_skill_benchmark'];req(r['ok'] and row['all_required_scenarios_passed']);req(row['passed_scenario_count']==6);req(len(row['scenario_evidence_digest'])==64);chat=process_ordinary_chat_development_turn('show implementation skill checkpoint',project_state={'implementation_skill_benchmark_id':row['implementation_skill_benchmark_id']},runtime_root=base/'benchmark');req(chat.get('active') and chat.get('ok') and not chat.get('action_executed'))
 print({'ok':True,'suite':'v1350.3-5-implementation-skill-integration','passed':p,'total':5})
if __name__=='__main__':main()
