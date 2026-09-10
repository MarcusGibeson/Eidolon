"""Offline peer provenance regressions; never contacts a public provider."""
import json
from pathlib import Path
import runpy
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace as NS
import requests

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'conscious_agent'))
from governed_public_web_research_adapter import _connected_peer_address, PublicWebResearchError

fixtures = runpy.run_path(str(ROOT / 'tools/v2501_1_governed_public_web_research_adapter_tests.py'))
checks = []

def sock(ip):
    return NS(getpeername=lambda: (ip, 443))

def response(primary=None, stream=None):
    return NS(raw=NS(_connection=NS(sock=primary), _fp=NS(fp=NS(raw=NS(_sock=stream)))))

def rejects(value, code):
    try:
        _connected_peer_address(value)
    except PublicWebResearchError as error:
        assert error.code == code, error.code
    else:
        raise AssertionError('peer unexpectedly admitted')
    checks.append(code)

assert _connected_peer_address(response(stream=sock('93.184.216.34'))) == '93.184.216.34'
checks.append('detached_connection_uses_stream_socket')
assert _connected_peer_address(response(sock('93.184.216.34'), sock('93.184.216.34'))) == '93.184.216.34'
checks.append('agreeing_socket_paths')
rejects(response(), 'public_web_connected_peer_unavailable')
rejects(response(stream=sock('127.0.0.1')), 'public_web_connected_peer_rejected')
rejects(response(sock('93.184.216.34'), sock('10.0.0.1')), 'public_web_connected_peer_rejected')
rejects(response(sock('93.184.216.34'), sock('1.1.1.1')), 'public_web_connected_peer_conflict')
rejects(response(stream=sock('not-an-address')), 'public_web_connected_peer_unavailable')

page = fixtures['FakeResponse'](b'<html>Public survey response</html>')
page.raw = response(stream=sock('93.184.216.34')).raw
adapter, _ = fixtures['adapter_for'](page)
assert adapter._fetch('https://docs.example.com/report', max_bytes=4096, timeout_seconds=2)['body'].startswith(b'<html>')
checks.append('normal_fetch_accepts_verified_stream_peer')
page = fixtures['FakeResponse'](b'not admitted')
page.raw = response(stream=sock('1.1.1.1')).raw
adapter, _ = fixtures['adapter_for'](page)
try:
    adapter._fetch('https://docs.example.com/report', max_bytes=4096, timeout_seconds=2)
except fixtures['PublicWebResearchError'] as error:
    assert error.code == 'public_web_connected_peer_dns_mismatch'
else:
    raise AssertionError('DNS mismatch bypassed')
checks.append('fallback_still_requires_dns_match')

# Exercise the installed requests/urllib3 response shape, not just test doubles.
# Loopback is used only by this test harness; production must still reject it.
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Connection', 'close')
        self.send_header('Content-Length', '4')
        self.end_headers()
        self.wfile.write(b'test')

    def log_message(self, *args):
        pass

server = HTTPServer(('127.0.0.1', 0), Handler)
worker = threading.Thread(target=server.serve_forever, daemon=True)
worker.start()
try:
    with requests.Session() as session:
        session.trust_env = False
        with session.get('http://127.0.0.1:%d/' % server.server_port, stream=True, timeout=3) as live:
            assert live.raw._connection.sock is None
            rejects(live, 'public_web_connected_peer_rejected')
            checks.append('real_connection_close_stream_peer_found_and_loopback_rejected')
finally:
    server.shutdown()
    server.server_close()
    worker.join(timeout=3)
print(json.dumps({'ok': True, 'passed': len(checks), 'checks': checks}))
