"""Time-isolated text-only PDF reader. No OCR, attachments or active content."""
import io
import json
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 8_000_000


def _memory_limit():
    """Bound the worker, including decompression before stream-size checks."""
    limit = 512 * 1024 * 1024
    if sys.platform != 'win32':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        return None
    import ctypes as c
    from ctypes import wintypes as w
    class Basic(c.Structure):
        _fields_ = [('process_time', c.c_int64), ('job_time', c.c_int64),
                    ('flags', w.DWORD), ('min_ws', c.c_size_t), ('max_ws', c.c_size_t),
                    ('active', w.DWORD), ('affinity', c.c_size_t),
                    ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class Extended(c.Structure):
        _fields_ = [('basic', Basic), ('io', c.c_uint64 * 6),
                    ('process_memory', c.c_size_t), ('job_memory', c.c_size_t),
                    ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]
    k = c.WinDLL('kernel32', use_last_error=True)
    k.CreateJobObjectW.restype = w.HANDLE
    k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
    k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    k.GetCurrentProcess.restype = w.HANDLE
    job = k.CreateJobObjectW(None, None)
    info = Extended()
    info.basic.flags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info.process_memory = limit
    if not job or not k.SetInformationJobObject(job, 9, c.byref(info), c.sizeof(info)) or not k.AssignProcessToJobObject(job, k.GetCurrentProcess()):
        raise ValueError('public_pdf_resource_limit_unavailable')
    return job


def extract_pdf(body, timeout_seconds):
    if len(body) > MAX_BYTES or not body.startswith(b'%PDF-'):
        raise ValueError('public_pdf_invalid_or_oversize')
    try:
        result = subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()), '--worker'],
                                input=body, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=max(.1, min(15, timeout_seconds)),
                                creationflags=0x08000000 if sys.platform == 'win32' else 0)
    except subprocess.TimeoutExpired as error:
        raise ValueError('public_pdf_extraction_timeout') from error
    if result.returncode or len(result.stdout) > 3_100_000:
        raise ValueError('public_pdf_extraction_failed')
    row = json.loads(result.stdout)
    if row.get('error'):
        raise ValueError(row['error'])
    return row


def _worker():
    job = _memory_limit()
    from pypdf import PdfReader
    body = sys.stdin.buffer.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError('public_pdf_oversize')
    reader = PdfReader(io.BytesIO(body), strict=True)
    if reader.is_encrypted:
        raise ValueError('public_pdf_encrypted')
    if len(reader.pages) > 40:
        raise ValueError('public_pdf_page_limit')
    parts = []
    for page in reader.pages:
        contents = page.get_contents()
        if contents and len(contents.get_data()) > 2_000_000:
            raise ValueError('public_pdf_content_limit')
        text = page.extract_text() or ''
        if sum(map(len, parts)) + len(text) > 500_000:
            raise ValueError('public_pdf_text_limit')
        parts.append(text)
    text = '\n'.join(parts)
    if len(text.strip()) < 30:
        raise ValueError('public_pdf_no_readable_text')
    return {'text': text, 'page_count': len(parts)}


if __name__ == '__main__':
    try:
        output = _worker()
    except Exception as error:
        code = str(error)
        output = {'error': code if code.startswith('public_pdf_') else 'public_pdf_extraction_failed'}
    sys.stdout.write(json.dumps(output, ensure_ascii=True))
