import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from durable_campaign_checkpoint import *
from v1380_test_support import *
N=0
r=build_durable_campaign_checkpoint(**kwargs());req(r['ok'],'build');N+=1
x=r['durable_campaign_checkpoint'];req(x['multi_hour_duration_satisfied'] and x['logical_duration_seconds']==14400,'duration');N+=1
req(x['interruption_observed'] and x['restart_observed'] and x['external_change_detected'],'scenario');N+=1
req(x['content_free'] and x['read_only_checkpoint'],'privacy');N+=1
req(not r['work_execution_authorized'] and not r['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1380-foundations'})
