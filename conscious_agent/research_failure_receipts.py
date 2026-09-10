"""Content-minimized source failure diagnostics, not evidence of source truth."""
import hashlib
import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

REASONS = {'public_web_connected_peer_unavailable': 'connection_identity_unavailable',
           'public_web_demand_readable_content_unavailable': 'insufficient_readable_text',
           'public_pdf_extraction_failed': 'pdf_extraction_failed',
           'public_pdf_extraction_timeout': 'pdf_extraction_timeout',
           'public_pdf_no_readable_text': 'pdf_no_readable_text',
           'public_web_content_type_rejected': 'unsupported_content_type'}


def sanitize_failures(rows):
    result = []
    for row in list(rows or [])[:32]:
        if not isinstance(row, dict):
            continue
        digest = str(row.get('failure_code_digest') or '')
        source_digest = str(row.get('source_candidate_digest') or '')
        if not re.fullmatch('[0-9a-f]{64}', digest) or not re.fullmatch('[0-9a-f]{64}', source_digest):
            continue
        url = ''
        try:
            p = urlsplit(str(row.get('public_url') or ''))
            host = p.hostname or ''
            try:
                public = ipaddress.ip_address(host).is_global
            except ValueError:
                public = '.' in host and not host.endswith(('.local', '.localhost'))
            if public and p.scheme in ('http', 'https') and not p.username and not p.password and p.port in (None, 80, 443) and not any(c.isspace() for c in p.path):
                url = urlunsplit((p.scheme, p.netloc, p.path, '', ''))[:2048]
        except ValueError:
            pass
        reason = next((value for code, value in REASONS.items() if hashlib.sha256(code.encode()).hexdigest() == digest), 'source_fetch_failed')
        result.append({'source_candidate_digest': source_digest, 'public_url': url,
                       'failure_code_digest': digest, 'reason': reason})
    return result
