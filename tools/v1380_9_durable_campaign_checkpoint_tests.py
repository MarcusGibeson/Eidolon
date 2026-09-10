import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from durable_campaign_checkpoint import *
from v1380_test_support import *
N=0
r=build_durable_campaign_checkpoint(**kwargs());x=r['durable_campaign_checkpoint'];req(r['ok'],'checkpoint');N+=1
req(x['campaign_completed'] and x['reconciliation_completed'],'complete');N+=1
req(x['compact_project_state_used'] and not x['chat_replay_used'],'continuity');N+=1
req(x['operator_change_preserved'] and not x['duplicate_side_effect_replay'],'safety');N+=1
req(not r['source_mutation_authorized'] and not r['release_authorized'] and not r['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1380-checkpoint'})
