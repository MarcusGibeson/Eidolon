"""Real bounded PDF worker and unverified publication-date reporting."""
import io
import runpy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'conscious_agent'))
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from research_pdf_text import extract_pdf
from governed_public_web_research_adapter import _VisibleTextParser
p = _VisibleTextParser()
p.feed('<h1>A survey</h1><div>October 24, 2022</div><p>' + 'Body. ' * 80 + '</p><div>January 1, 2026</div>')
assert p.publication_dates == ['2022-10-24']

def pdf(pages=1, encrypted=False, text=True):
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=600, height=800)
        if text:
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(b'BT /F1 12 Tf 50 700 Td (The survey was conducted in May 2022 among 750 participants.) Tj ET')
            page[NameObject('/Contents')] = writer._add_object(stream)
    if encrypted:
        writer.encrypt('password')
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

assert '750 participants' in extract_pdf(pdf(), 10)['text']
for body, code in [(b'not a PDF', 'invalid_or_oversize'), (pdf(encrypted=True), 'encrypted'), (pdf(text=False), 'no_readable_text'), (pdf(pages=41), 'page_limit')]:
    try:
        extract_pdf(body, 10)
        raise AssertionError('accepted invalid document')
    except ValueError as e:
        assert code in str(e), str(e)

f = runpy.run_path(str(Path(__file__).with_name('research_inconclusive_review_tests.py')))
r = f['report']
r['source_assessment_summary']['source_reported_publication_dates'] = {'web-a': ['2022-10-24', '<script>']}
message = f['_research_report_message']({}, r)
assert 'source-reported publication date: 2022-10-24' in message
assert 'currentness unverified' in message and '<script>' not in message
print('PDF extraction and date reporting checks passed')

import tempfile
import hashlib
f = runpy.run_path(str(Path(__file__).with_name('research_batch_selection_tests.py')))
class PDFAdapter(f['Adapter']):
    def _fetch(self, url, **kwargs):
        body = pdf()
        return {'body': body, 'public_url': url, 'final_url': url, 'content_type': 'application/pdf',
                'observed_bytes': len(body), 'redirect_count': 0, 'content_digest': hashlib.sha256(body).hexdigest()}

with tempfile.TemporaryDirectory() as td:
    store = f['BoundedResearchSessionStore'](td)
    s = store.create_session('create', objective='Research Brand Deal Tracking for Content Creators demand.')['result']
    auth = store.authorize_session('auth', session_id=s['session_id'], session_digest=s['session_digest'], public_query_confirmed=True)
    adapter = PDFAdapter()
    result = store.execute_session('execute', session_id=s['session_id'], authorization_digest=auth['result']['authorization_digest'], adapter=adapter)
    assert result['ok'], result
    assert result['result']['report']['provider_request_count'] == 1
    assert result['result']['session']['observed_page_count'] > 0
    assert not result['result']['report']['verified_findings']
    assert not adapter._transient_documents
print('Normal authorized PDF workflow passed without promoting evidence')
