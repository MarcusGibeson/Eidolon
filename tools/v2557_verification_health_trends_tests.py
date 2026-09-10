from conscious_agent.verification_health_trends_v2557 import build_verification_health_trends
from conscious_agent.verification_history_v2547 import CONTRACT_VERSION

def row(ok=True, timeout=False, elapsed=1.0):
    return {'contract_version': CONTRACT_VERSION, 'ok': ok, 'timed_out': timeout, 'elapsed_seconds': elapsed}

def main():
    hist={'a':[row(True) for _ in range(8)] + [row(False),row(True),row(False),row(True),row(False),row(True),row(False),row(True)],
          'b':[row(True,elapsed=1) for _ in range(8)] + [row(True,elapsed=3) for _ in range(8)]}
    out=build_verification_health_trends(hist,window_size=8)
    checks=[out['ok'],out['direction'] in {'worsening','mixed'},out['deltas']['intermittent_count']>=1,out['deltas']['performance_regression_count']>=1,
            out['raw_test_output_stored'] is False,out['required_tests_waived']==0,not out['test_suppression_authorized'],not out['timeout_change_authorized'],not out['release_authorized'],len(out['trend_digest'])==64]
    print({'suite':'v2557-verification-health-trends','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
