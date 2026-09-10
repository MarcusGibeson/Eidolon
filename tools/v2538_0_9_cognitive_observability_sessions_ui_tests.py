from __future__ import annotations
from conscious_agent.api_server import handle_api_get
from conscious_agent import dashboard

def main():
    checks=[]
    status,payload=handle_api_get('/api/cognition/observability/sessions?limit=4')
    checks += [status==200,payload.get('ok') is True]
    data=payload.get('data') if isinstance(payload.get('data'),dict) else payload
    checks += [data.get('authority_boundary',{}).get('read_only') is True,data.get('authority_boundary',{}).get('hidden_reasoning_exposed') is False]
    html=dashboard.render_cognitive_observability_dashboard()
    checks += ['mind-session-count' in html,'mind-sessions' in html,'/api/cognition/observability/sessions' in html,'Correlated activity groups' in html]
    checks += ['voice_text' not in str(data.get('sessions') or [])]
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
