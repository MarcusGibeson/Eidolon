from __future__ import annotations
from conscious_agent import dashboard
from conscious_agent.api_server import handle_api_get

def main():
    checks=[]
    html=dashboard.render_cognitive_observability_dashboard()
    checks += [
      "id='mind-kind'" in html,
      "id='mind-auto'" in html,
      "encodeURIComponent(kind)" in html,
      "mind-kind').addEventListener('change'" in html,
      "<details class='activity-line'>" in html,
      "row.transitions" in html,
      "mind-auto').checked" in html,
    ]
    status,payload=handle_api_get('/api/cognition/observability?kind=voice&limit=4')
    checks += [status==200,payload.get('ok') is True]
    data=payload.get('data') if isinstance(payload.get('data'),dict) else payload
    checks += [data.get('filters',{}).get('kind')=='voice',data.get('authority_boundary',{}).get('read_only') is True]
    passed=sum(bool(x) for x in checks)
    print({'passed':passed,'total':len(checks),'checks':[bool(x) for x in checks]})
    raise SystemExit(0 if passed==len(checks) else 1)
if __name__=='__main__': main()
