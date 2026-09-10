import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from durable_campaign_checkpoint import *
from v1380_test_support import *
N=0
k=kwargs();k['campaign_record_digest']='bad';req(not build_durable_campaign_checkpoint(**k)['ok'],'lineage');N+=1
k=kwargs();k.update(external_change_at_unix=5000,reconciled_at_unix=6000,completed_at_unix=7000);req(build_durable_campaign_checkpoint(**k)['status']=='multi_hour_campaign_evidence_required','duration');N+=1
k=kwargs();k['restarted_at_unix']=3500;req(not build_durable_campaign_checkpoint(**k)['ok'],'timeline');N+=1
k=kwargs();k['operator_change_preserved']=False;req(not build_durable_campaign_checkpoint(**k)['ok'],'preserve');N+=1
k=kwargs();k['duplicate_side_effect_replay']=True;req(not build_durable_campaign_checkpoint(**k)['ok'],'duplicate');N+=1
r=build_durable_campaign_checkpoint(**kwargs());x=r['durable_campaign_checkpoint'];t=dict(x);t['campaign_completed']=False;req(not validate_durable_campaign_checkpoint(t,expected_checkpoint_digest=x['checkpoint_digest'])['ok'],'tamper');N+=1
req(not validate_durable_campaign_checkpoint(x,expected_checkpoint_digest='a'*64)['ok'],'stale digest');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1380-reliability'})
