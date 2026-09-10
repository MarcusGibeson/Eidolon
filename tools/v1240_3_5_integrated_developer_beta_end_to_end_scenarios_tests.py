from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1240-api-')
from integrated_developer_beta import AUTHORITY_FLAGS,canonical_scenario_evidence,evaluate_integrated_scenario,scenario_registry
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from conscious_agent.api_server import handle_api_get
checks=[]
def check(v): checks.append(bool(v))
r=scenario_registry()
for s in r['scenarios']:
    e=canonical_scenario_evidence(s['scenario_id']); out=evaluate_integrated_scenario(s['scenario_id'],e)
    for v in (out.get('ok'),out.get('status')=='scenario_evidence_verified',out.get('scenario_id')==s['scenario_id'],out.get('terminal_expectation')==s['terminal_expectation'],out.get('reason_codes')==[],out.get('content_free') is True,out.get('read_only') is True): check(v)
    for key,expected in AUTHORITY_FLAGS.items(): check(out.get(key) is expected)
for text,status in [('show integrated developer beta scenario registry','integrated_developer_beta_scenario_registry_ready'),('show integrated developer beta benchmark','integrated_developer_beta_contract_ready')]:
    out=process_ordinary_chat_development_turn(text)
    check(out.get('active') is True); row=out.get('integrated_developer_beta') or {}; check(row.get('status')==status); check('No' in out.get('response','') or 'no' in out.get('response',''))
for cmd in ('integrated-developer-beta-scenario-registry','integrated-developer-beta-benchmark'):
    p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),cmd],cwd=ROOT,text=True,capture_output=True,timeout=300,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    check(p.returncode==0)
    try: check(json.loads(p.stdout.strip().splitlines()[-1]).get('ok') is True)
    except Exception: check(False)
for route in ('integrated-developer-beta-scenario-registry','integrated-developer-beta-benchmark'):
    code,payload=handle_api_get('/api/cognition/'+route); check(code==200); check(payload.get('ok') is True); check((payload.get('data') or {}).get('content_free') is True)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
