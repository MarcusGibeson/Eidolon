import hashlib,json
D=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
C='c'*64;G=D('goal');P=D('plan');B=D('budget');STEP=D('step');S=D('source');W=D('workspace');U=D('upstream')
def req(c,m):
 if not c:raise AssertionError(m)
def capsule(**kw):
 from multi_day_continuity import build_continuity_capsule
 x=dict(campaign_id='camp',campaign_record_digest=C,goal_digest=G,plan_digest=P,budget_digest=B,current_step_digest=STEP,source_digest=S,workspace_digest=W,upstream_digest=U,completed_steps=2,total_steps=5,state='paused',last_active_unix=1000)
 x.update(kw);return build_continuity_capsule(**x)
