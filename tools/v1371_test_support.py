import hashlib,tempfile
D=lambda x:hashlib.sha256(str(x).encode()).hexdigest(); S='a'*64
BASE=dict(campaign_id='campaign-1',source_manifest_digest=S,workspace_digest=D('workspace'),standing_grant_digest=D('grant'),standing_session_active=True,goal_digest=D('goal'),plan_digest=D('plan'),budget_digest=D('budget'),current_step_id='step-2',total_steps=5,completed_steps=1,evidence_digests=[D('e1'),D('e2')],state='active',recovery_state='clean',generation=1,prior_record_digest='')
def req(c,m):
 if not c:raise AssertionError(m)
