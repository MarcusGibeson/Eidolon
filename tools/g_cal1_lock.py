"""OS-backed per-run serialization. Lock bytes are not experiment evidence."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import tempfile
import time

from g_extract1_contract import IntegrityError


@contextmanager
def run_lock(directory):
    # One stable namespace across objects/processes; never unlink a held lock.
    identity = os.path.normcase(str(Path(directory).resolve())).encode('utf-8')
    root = Path(tempfile.gettempdir()) / 'g-cal1-governed-locks-v1'
    root.mkdir(exist_ok=True)
    path = root / (hashlib.sha256(identity).hexdigest() + '.lock')
    with path.open('a+b') as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b'0')
            stream.flush()
        deadline = time.monotonic() + 120
        while True:
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise IntegrityError('PROVENANCE_MISMATCH', 'run operation lock unavailable')
                time.sleep(0.01)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
