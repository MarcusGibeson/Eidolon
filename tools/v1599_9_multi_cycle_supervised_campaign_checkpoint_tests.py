from __future__ import annotations
import json, os, shutil, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'; sys.path.insert(0,str(AGENT))
import supervised_initiative_campaign as campaign

assertions=[]
def req(v,label):
    if not v: raise AssertionError(label)
    assertions.append(label)
def cand(ch,score,deps=()):
    return {'candidate_id':f'discovery-{ch*20}','evidence_digest':ch*64,'value_evidence_digest':('f' if ch!='f' else 'e')*64,'priority_score':score,'acceptance_criteria':['focused_pass','active_source_unchanged'],'dependency_candidate_ids':list(deps),'practical_benefit':'visible improvement','risk_class':'bounded'}
def shortlist():
    rows=[cand('a',.91),cand('b',.72),cand('c',.61)]; return {'ok':True,'shortlist_digest':'d'*64,'shortlist':rows,'selected_candidate_id':rows[0]['candidate_id'],'selected':rows[0]}

def test_planning_contract():
    c=campaign.campaign_planning_contract(); req(c['initiative_count']=={'minimum':3,'maximum':5},'3-5'); req(c['dependency_graph_required'],'deps'); req(not c['campaign_membership_is_execution_authority'],'no authority')
def test_three_item_plan():
    p=campaign.build_campaign_plan(shortlist(),source_digest='1'*64); req(p['ok'] and p['item_count']==3,'plan'); req(len(p['campaign_id'])>20 and len(p['plan_digest'])==64,'identity')
def test_too_few_items_rejected():
    s=shortlist(); s['shortlist']=s['shortlist'][:2]; req(campaign.build_campaign_plan(s,source_digest='1'*64)['status']=='campaign_requires_three_meaningful_initiatives','few')
def test_dependency_cycle_rejected():
    a,b,c=cand('a',.9,['discovery-'+'b'*20]),cand('b',.8,['discovery-'+'a'*20]),cand('c',.7); s={'shortlist':[a,b,c]}; req(campaign.build_campaign_plan(s,source_digest='1'*64)['status']=='campaign_dependency_cycle_rejected','cycle')
def test_pacing_contract():
    c=campaign.pacing_contract(); req(c['one_active_campaign_across_processes'] and c['budgets']['maximum_active_items']==1,'single active'); req(c['quiet_period_supported'],'quiet'); req(c['resume_reuses_campaign_not_execution_authority'],'resume authority')
def test_create_restart_reuse_and_select():
    temp=Path(tempfile.mkdtemp());
    try:
        created=campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp); req(created['status']=='campaign_created','created'); reused=campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp); req(reused['status']=='campaign_reused' and not reused['runtime_mutated'],'restart reuse'); selected=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp); req(selected['ok'] and selected['candidate']['candidate_id']=='discovery-'+'a'*20,'priority selected'); again=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp); req(not again['ok'] and again['status']=='campaign_item_already_active','one active')
    finally: shutil.rmtree(temp,ignore_errors=True)
def test_state_progression_and_next_item():
    temp=Path(tempfile.mkdtemp())
    try:
        campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp); first=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp)['candidate']; rr=campaign.record_campaign_candidate_state(first['candidate_id'],first['evidence_digest'],'review_ready',proposal_id='improvement-'+'1'*20,runtime_root=temp); req(rr['ok'],'review ready'); installed=campaign.record_campaign_candidate_state(first['candidate_id'],first['evidence_digest'],'installed',runtime_root=temp); req(installed['ok'],'installed'); nxt=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp); req(nxt['candidate']['candidate_id']=='discovery-'+'b'*20,'next priority')
    finally: shutil.rmtree(temp,ignore_errors=True)
def test_stale_evidence_not_activated():
    temp=Path(tempfile.mkdtemp())
    try:
        campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp); changed=shortlist(); changed['shortlist']=[dict(x) for x in changed['shortlist']]; changed['shortlist'][0]['evidence_digest']='9'*64; result=campaign.select_next_campaign_candidate(current_shortlist=changed,runtime_root=temp); req(result['ok'] and result['candidate']['candidate_id']=='discovery-'+'b'*20,'stale skipped')
    finally: shutil.rmtree(temp,ignore_errors=True)
def test_exhausted_stale_campaign_is_superseded_by_fresh_shortlist():
    temp=Path(tempfile.mkdtemp())
    try:
        old=shortlist(); created=campaign.create_or_reuse_campaign(old,source_digest='1'*64,runtime_root=temp)['campaign']
        first=campaign.select_next_campaign_candidate(current_shortlist=old,runtime_root=temp)['candidate']; campaign.record_campaign_candidate_state(first['candidate_id'],first['evidence_digest'],'installed',runtime_root=temp)
        second=campaign.select_next_campaign_candidate(current_shortlist=old,runtime_root=temp)['candidate']; campaign.record_campaign_candidate_state(second['candidate_id'],second['evidence_digest'],'installed',runtime_root=temp)
        fresh_rows=[cand('d',.88),cand('e',.77),cand('f',.66)]; fresh={'ok':True,'shortlist_digest':'8'*64,'shortlist':fresh_rows,'selected_candidate_id':fresh_rows[0]['candidate_id'],'selected':fresh_rows[0]}
        replaced=campaign.create_or_reuse_campaign(fresh,source_digest='2'*64,runtime_root=temp)
        req(replaced['status']=='campaign_superseded_stale' and replaced['runtime_mutated'],'stale campaign superseded')
        req(replaced['campaign']['campaign_id']!=created['campaign_id'] and replaced['campaign']['superseded_campaign_id']==created['campaign_id'],'superseded lineage retained')
        selected=campaign.select_next_campaign_candidate(current_shortlist=fresh,runtime_root=temp)
        req(selected['ok'] and selected['candidate']['candidate_id']==fresh_rows[0]['candidate_id'],'fresh campaign selects current candidate')
    finally: shutil.rmtree(temp,ignore_errors=True)
def test_pause_resume_cancel_exact_digest():
    temp=Path(tempfile.mkdtemp())
    try:
        created=campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp)['campaign']; cid=created['campaign_id']; dig=created['campaign_digest'][:16]; pause=campaign.control_campaign('pause',cid,dig,runtime_root=temp); req(pause['ok'] and pause['campaign']['state']=='paused','pause'); replay=campaign.control_campaign('pause',pause['campaign']['campaign_id'],pause['campaign']['campaign_digest'][:16],runtime_root=temp); req(replay['ok'] and not replay['runtime_mutated'],'pause idempotent'); resume=campaign.control_campaign('resume',pause['campaign']['campaign_id'],pause['campaign']['campaign_digest'][:16],runtime_root=temp); req(resume['ok'] and resume['campaign']['state']=='active','resume'); stale=campaign.control_campaign('cancel',cid,dig,runtime_root=temp); req(not stale['ok'],'stale digest'); cancel=campaign.control_campaign('cancel',resume['campaign']['campaign_id'],resume['campaign']['campaign_digest'][:16],runtime_root=temp); req(cancel['ok'] and cancel['campaign']['state']=='cancelled','cancel')
    finally: shutil.rmtree(temp,ignore_errors=True)

def test_quiet_period_blocks_and_wakes_selection():
    temp=Path(tempfile.mkdtemp())
    try:
        created=campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp)['campaign']; cid=created['campaign_id']; dig=created['campaign_digest'][:16]
        quiet=campaign.control_campaign('quiet',cid,dig,runtime_root=temp); req(quiet['ok'] and quiet['campaign']['quiet_period'],'quiet entered')
        blocked=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp); req(not blocked['ok'] and blocked['status']=='campaign_quiet_period','quiet blocks selection')
        replay=campaign.control_campaign('quiet',quiet['campaign']['campaign_id'],quiet['campaign']['campaign_digest'][:16],runtime_root=temp); req(replay['ok'] and not replay['runtime_mutated'],'quiet idempotent')
        wake=campaign.control_campaign('wake',quiet['campaign']['campaign_id'],quiet['campaign']['campaign_digest'][:16],runtime_root=temp); req(wake['ok'] and not wake['campaign']['quiet_period'],'wake clears quiet')
        selected=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp); req(selected['ok'],'selection resumes after wake')
    finally: shutil.rmtree(temp,ignore_errors=True)

def test_parser_refuses_compound():
    req(campaign.is_campaign_control('show supervised development campaign'),'show exact'); req(campaign.is_campaign_control('quiet supervised development campaign devcampaign_'+'a'*24+' digest '+'b'*16),'quiet exact'); req(not campaign.is_campaign_control('pause supervised development campaign and install it'),'compound refused')
def test_scope_evidence_mismatch_rejected():
    temp=Path(tempfile.mkdtemp())
    try:
        campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp); first=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp)['candidate']; r=campaign.record_campaign_candidate_state(first['candidate_id'],'0'*64,'installed',runtime_root=temp); req(not r['ok'] and r['status']=='campaign_item_evidence_mismatch','evidence binding')
    finally: shutil.rmtree(temp,ignore_errors=True)
def test_checkpoint_defers_native():
    c=campaign.checkpoint_contract(); req(c['v1600_desktop_gate_required_for_certification'],'gate'); req('windows_cross_process_lock_race' in c['deferred_local_evidence'],'windows defer'); req(not c['automatic_promotion'],'no promote')
def test_campaign_outputs_no_authority():
    temp=Path(tempfile.mkdtemp())
    try:
        pub=campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp)['campaign']; req(not pub['provider_contacted'] and not pub['source_modified'] and not pub['authority_granted'],'public inert'); req(all(v is False for v in pub['authority_boundary'].values()),'all authority false')
    finally: shutil.rmtree(temp,ignore_errors=True)
def test_cycle_budget():
    temp=Path(tempfile.mkdtemp())
    try:
        campaign.create_or_reuse_campaign(shortlist(),source_digest='1'*64,runtime_root=temp); path=temp/'development_campaigns'/'supervised_initiative_campaign.json'; row=json.loads(path.read_text()); row['cycle_count']=campaign.MAX_CYCLES; row=campaign._seal(row); path.write_text(json.dumps(row)); r=campaign.select_next_campaign_candidate(current_shortlist=shortlist(),runtime_root=temp); req(r['status']=='campaign_cycle_budget_exhausted','cycle budget')
    finally: shutil.rmtree(temp,ignore_errors=True)

def main():
    tests=[v for k,v in list(globals().items()) if k.startswith('test_') and callable(v)]; good=0; results=[]
    for fn in tests:
        try: fn(); good+=1; results.append({'name':fn.__name__,'ok':True})
        except Exception as e: results.append({'name':fn.__name__,'ok':False,'error':f'{type(e).__name__}: {e}'})
    print(json.dumps({'suite':'v1599.9-multi-cycle-supervised-campaign-checkpoint','ok':good==len(tests),'passed':good,'total':len(tests),'assertions':len(assertions),'results':results},indent=2)); return 0 if good==len(tests) else 1
if __name__=='__main__': raise SystemExit(main())
