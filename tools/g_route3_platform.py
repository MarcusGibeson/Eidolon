from __future__ import annotations

"""Operating-system primitives for the G-ROUTE3 R7 lifecycle (design §8, §14, §15).

Everything here is a thin, explicit wrapper over one OS facility:

* no-replace, write-through renames and directory flushes (the §14 publication protocol);
* the OS-held lease lock at a high byte offset (§15);
* the kill-on-close job object every command process joins at startup (§15);
* child-process creation flags that keep console signals away from the sandbox and scorer (§8);
* ``run_pinned``: the one entry wrapper that runs model-output functions at a fixed recursion budget (§8).

The governed run executes on Windows. The POSIX branches follow the design (Linux: OFD locks, subreaper,
process groups) and carry its declared limit: descendants of a SIGKILLed holder may survive.
"""

import errno
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable

WINDOWS = os.name == "nt"
RECURSION_LIMIT = 1000                 # R6's effective default; R6 never changes it (§8)
PINNED_STACK_BYTES = 64 * 1024 * 1024  # 64 MiB (§8)
LEASE_LOCK_OFFSET = 1 << 40            # one byte at 2^40, beyond the informational text (§15)
RETRIES = 20
RETRY_SECONDS = 0.1

if WINDOWS:
    import ctypes
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    MOVEFILE_REPLACE_EXISTING = 0x1
    MOVEFILE_WRITE_THROUGH = 0x8
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_ALL = 0x1 | 0x2 | 0x4
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    LOCKFILE_FAIL_IMMEDIATELY = 0x1
    LOCKFILE_EXCLUSIVE_LOCK = 0x2
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x800
    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
    CREATE_NO_WINDOW = 0x08000000
    ERROR_SHARING_VIOLATION = 32
    ERROR_ACCESS_DENIED = 5
    ERROR_ALREADY_EXISTS = 183
    ERROR_FILE_EXISTS = 80
    ERROR_LOCK_VIOLATION = 33

    class _OVERLAPPED(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_void_p), ("InternalHigh", ctypes.c_void_p),
                    ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class _EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BASIC_LIMIT), ("IoInfo", _IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    _kernel32.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    _kernel32.MoveFileExW.restype = wintypes.BOOL
    _kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                      wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _kernel32.FlushFileBuffers.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.LockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                     wintypes.DWORD, ctypes.POINTER(_OVERLAPPED)]
    _kernel32.LockFileEx.restype = wintypes.BOOL
    _kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    import msvcrt


class AlreadyExists(OSError):
    """A no-replace rename found its target. Under the lease this means damage or tampering (§14)."""


def _winerror(exc: BaseException) -> int | None:
    return getattr(exc, "winerror", None)


def is_transient(exc: BaseException) -> bool:
    """Sharing violations and access-denied are retried (§14 step 2, §4.4)."""
    if WINDOWS:
        return _winerror(exc) in (32, 5, 33)
    return getattr(exc, "errno", None) in (errno.EBUSY, errno.EAGAIN, errno.EACCES)


def rename_noreplace(source: Path, target: Path) -> None:
    """Rename without replacing an existing target, with write-through on Windows. Raises AlreadyExists."""
    if WINDOWS:
        if not _kernel32.MoveFileExW(str(source), str(target), MOVEFILE_WRITE_THROUGH):
            code = ctypes.get_last_error()
            if code in (ERROR_ALREADY_EXISTS, ERROR_FILE_EXISTS):
                raise AlreadyExists(errno.EEXIST, "rename_target_exists", str(target))
            raise ctypes.WinError(code)
        return
    renameat2 = _posix_renameat2()
    if renameat2 is not None:
        renameat2(source, target)
        return
    try:
        os.link(source, target)
    except FileExistsError as exc:
        raise AlreadyExists(errno.EEXIST, "rename_target_exists", str(target)) from exc
    os.unlink(source)


def rename_replace(source: Path, target: Path) -> None:
    """Replacing rename, for projections only (§14, last paragraph)."""
    if WINDOWS:
        if not _kernel32.MoveFileExW(str(source), str(target), MOVEFILE_WRITE_THROUGH | MOVEFILE_REPLACE_EXISTING):
            raise ctypes.WinError(ctypes.get_last_error())
        return
    os.replace(source, target)


def _posix_renameat2():  # pragma: no cover - Linux only
    try:
        libc = __import__("ctypes").CDLL(None, use_errno=True)
        fn = libc.renameat2
    except (OSError, AttributeError):
        return None
    import ctypes as _ct
    AT_FDCWD, RENAME_NOREPLACE = -100, 1

    def call(source: Path, target: Path) -> None:
        if fn(AT_FDCWD, os.fsencode(source), AT_FDCWD, os.fsencode(target), RENAME_NOREPLACE) != 0:
            err = _ct.get_errno()
            if err == errno.EEXIST:
                raise AlreadyExists(errno.EEXIST, "rename_target_exists", str(target))
            raise OSError(err, os.strerror(err), str(source))
    return call


def flush_directory(path: Path) -> None:
    """Make a directory's entries durable (§14 step 3)."""
    if WINDOWS:
        handle = _kernel32.CreateFileW(str(path), GENERIC_WRITE, FILE_SHARE_ALL, None, OPEN_EXISTING,
                                       FILE_FLAG_BACKUP_SEMANTICS, None)
        if handle in (None, INVALID_HANDLE_VALUE):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not _kernel32.FlushFileBuffers(handle):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            _kernel32.CloseHandle(handle)
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_and_flush(path: Path, data: bytes) -> None:
    """Create a new file with exclusive creation, write it and flush it to the device (§14 step 1)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o644)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


class LeaseBusy(RuntimeError):
    """Another process holds the lease (§15)."""


class OsLease:
    """The G-ROUTE3 lease: an exclusive, non-blocking OS lock on one byte at 2^40 of ``D/.lease`` (§15).

    The file is opened without truncation and the lock is taken before anything is written. Only then are the
    leading bytes rewritten with the holder's details, which a refused command can still read. The OS releases
    the lock when the process exits, crashes or is killed, and on reboot. The handle is not inheritable.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._fd: int | None = None

    def acquire(self, holder: dict[str, Any]) -> None:
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o644)
        os.set_inheritable(fd, False)
        try:
            if WINDOWS:
                overlapped = _OVERLAPPED()
                overlapped.Offset = LEASE_LOCK_OFFSET & 0xFFFFFFFF
                overlapped.OffsetHigh = LEASE_LOCK_OFFSET >> 32
                handle = msvcrt.get_osfhandle(fd)
                if not _kernel32.LockFileEx(handle, LOCKFILE_EXCLUSIVE_LOCK | LOCKFILE_FAIL_IMMEDIATELY, 0, 1, 0,
                                            ctypes.byref(overlapped)):
                    raise LeaseBusy("lease_held_by_another_process:" + self.describe_holder())
            else:  # pragma: no cover - POSIX
                import fcntl
                import struct
                cmd = getattr(fcntl, "F_OFD_SETLK", None)
                if cmd is None:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError as exc:
                        raise LeaseBusy("lease_held_by_another_process:" + self.describe_holder()) from exc
                else:
                    lock = struct.pack("hhqqi", fcntl.F_WRLCK, 0, LEASE_LOCK_OFFSET, 1, 0)
                    try:
                        fcntl.fcntl(fd, cmd, lock)
                    except OSError as exc:
                        raise LeaseBusy("lease_held_by_another_process:" + self.describe_holder()) from exc
        except BaseException:
            os.close(fd)
            raise
        self._fd = fd
        text = (repr(sorted(holder.items())) + "\n").encode("utf-8", "replace")[:4096]
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, text.ljust(4096, b" "))
        os.fsync(fd)

    def describe_holder(self) -> str:
        try:
            with open(self.path, "rb") as handle:
                return handle.read(4096).decode("utf-8", "replace").strip()[:300]
        except OSError:
            return "unreadable"

    @property
    def held(self) -> bool:
        return self._fd is not None

    def release(self) -> None:
        if self._fd is not None:
            os.close(self._fd)      # closing the handle releases the lock
            self._fd = None


_JOB_HANDLE = None


def join_kill_on_close_job() -> None:
    """Assign this process to a new kill-on-close job before it creates any child (§15).

    Every later child is born inside the job, so none outlives this process. Breakaway is never permitted.
    Nested jobs work on Windows 8 and later. Refuses if the assignment fails.
    """
    global _JOB_HANDLE
    if _JOB_HANDLE is not None:
        return
    if not WINDOWS:  # pragma: no cover - Linux
        try:
            import ctypes as _ct
            libc = _ct.CDLL(None, use_errno=True)
            PR_SET_CHILD_SUBREAPER = 36
            libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)
        except OSError:
            pass
        _JOB_HANDLE = "posix"
        return
    job = _kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    info = _EXTENDED_LIMIT()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not _kernel32.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                                             ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not _kernel32.AssignProcessToJobObject(job, _kernel32.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    _JOB_HANDLE = job      # kept open for the life of the process; the OS closes it on exit


def child_creation_kwargs() -> dict[str, Any]:
    """Keyword arguments for every child: its own hidden console on Windows, its own session on POSIX (§8)."""
    if WINDOWS:
        return {"creationflags": CREATE_NO_WINDOW, "close_fds": True}
    return {"start_new_session": True, "close_fds": True}


_PIN_LOCK = threading.Lock()


def pin_recursion_limit() -> None:
    """Called once at process start by every G-ROUTE3 process, before any pinned thread exists."""
    sys.setrecursionlimit(RECURSION_LIMIT)


def run_pinned(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """The one shared entry wrapper for every function that handles model output (§8).

    A fresh thread with a 64 MiB stack, the process-wide recursion limit of 1000, entered directly from the
    thread's ``run`` so the entry depth is fixed. The original exception object is re-raised with its class
    intact, so R6's attribution by exception class is preserved.
    """
    if sys.getrecursionlimit() != RECURSION_LIMIT:
        raise RuntimeError("recursion_limit_not_pinned")
    outcome: dict[str, Any] = {}

    def body() -> None:
        try:
            outcome["value"] = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - carried to the caller unchanged
            outcome["error"] = exc

    with _PIN_LOCK:
        previous = threading.stack_size(PINNED_STACK_BYTES)
        try:
            thread = threading.Thread(target=body, name="g-route3-pinned", daemon=True)
            thread.start()
        finally:
            threading.stack_size(previous)
    thread.join()
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


def canonical_sha256(data: bytes) -> str:
    """The guarded-file digest convention (g_route1_contract.canonical_digest): CRLF and CR normalized to LF."""
    import hashlib
    return hashlib.sha256(bytes(data).replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def raw_read(path: Path) -> bytes:
    """Read the disk directly, never through a sealed view: the drift guard must see what is on disk now."""
    with open(path, "rb") as handle:
        return handle.read()


# ---------------------------------------------------------------- load-time hashing of repository modules (A-F2)

_LOADED: dict[str, str] = {}
_HOOK_ROOT: Path | None = None


def install_import_hashing(root: Path) -> None:
    """Hash every repository module's source bytes at the moment they are compiled (never from a later re-read,
    never from a stale .pyc). Call before importing any repository module other than this one."""
    global _HOOK_ROOT
    if _HOOK_ROOT is not None:
        return
    import importlib.machinery as machinery
    _HOOK_ROOT = Path(root).resolve()
    here = Path(__file__).resolve()
    _LOADED[here.relative_to(_HOOK_ROOT).as_posix()] = canonical_sha256(raw_read(here))

    class HashingLoader(machinery.SourceFileLoader):
        def get_code(self, fullname):
            path = Path(self.get_filename(fullname)).resolve()
            try:
                relative = path.relative_to(_HOOK_ROOT).as_posix()
            except ValueError:
                return super().get_code(fullname)
            data = self.get_data(str(path))
            _LOADED[relative] = canonical_sha256(data)
            return compile(data, str(path), "exec", dont_inherit=True)

    details = [(machinery.ExtensionFileLoader, machinery.EXTENSION_SUFFIXES),
               (HashingLoader, machinery.SOURCE_SUFFIXES),
               (machinery.SourcelessFileLoader, machinery.BYTECODE_SUFFIXES)]
    sys.path_hooks.insert(0, machinery.FileFinder.path_hook(*details))
    sys.path_importer_cache.clear()


def record_source(path: Path) -> None:
    """Record a file executed outside the import system (a child's main script), hashed now."""
    if _HOOK_ROOT is not None:
        resolved = Path(path).resolve()
        _LOADED[resolved.relative_to(_HOOK_ROOT).as_posix()] = canonical_sha256(raw_read(resolved))


def loaded_source_digests() -> dict[str, str]:
    """{repository-relative path: canonical sha256} of every repository module compiled in this process."""
    return dict(_LOADED)


# ---------------------------------------------------------------- sealed reads of guarded data files (A-F2, B-O2)

_SEALED: dict[str, bytes] = {}
_SEAL_INSTALLED = False


def seal_reads(files: dict[Path, bytes]) -> None:
    """Serve these exact, already verified bytes for every later ``Path.read_bytes``/``read_text`` of these paths,
    so a change on disk after verification can never reach the computation (it is caught by the raw-read guard)."""
    global _SEAL_INSTALLED
    for path, data in files.items():
        _SEALED[str(Path(path).resolve()).lower()] = bytes(data)
    if _SEAL_INSTALLED:
        return
    import pathlib
    original_bytes, original_text = pathlib.Path.read_bytes, pathlib.Path.read_text

    def read_bytes(self):
        sealed = _SEALED.get(str(self.resolve()).lower())
        return sealed if sealed is not None else original_bytes(self)

    def read_text(self, encoding=None, errors=None, *args, **kwargs):
        sealed = _SEALED.get(str(self.resolve()).lower())
        if sealed is None:
            return original_text(self, encoding, errors, *args, **kwargs)
        import io
        return io.TextIOWrapper(io.BytesIO(sealed), encoding=encoding, errors=errors).read()

    pathlib.Path.read_bytes = read_bytes
    pathlib.Path.read_text = read_text
    _SEAL_INSTALLED = True


def unseal_reads() -> None:
    _SEALED.clear()


__all__ = ["WINDOWS", "RECURSION_LIMIT", "canonical_sha256", "raw_read", "install_import_hashing", "record_source",
           "loaded_source_digests", "seal_reads", "unseal_reads", "PINNED_STACK_BYTES", "LEASE_LOCK_OFFSET", "RETRIES", "RETRY_SECONDS",
           "AlreadyExists", "LeaseBusy", "OsLease", "is_transient", "rename_noreplace", "rename_replace",
           "flush_directory", "write_and_flush", "join_kill_on_close_job", "child_creation_kwargs",
           "pin_recursion_limit", "run_pinned"]
