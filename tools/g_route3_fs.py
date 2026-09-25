from __future__ import annotations

"""The single choke point for every filesystem operation and every child process of the R7 lifecycle (§19).

``RealFs`` implements the §14 publication protocol, the §4.4 reading rule and the recovery primitives on the
real disk. The certification campaign wraps it (see ``g_route3_campaign``) to kill the process after or before
any operation, to model power loss over unflushed operations, and to inject sharing violations and damage.
Nothing in the lifecycle touches the disk or starts a process except through an ``Fs``.
"""

import os
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import g_route3_platform as platform


class Unreadable(OSError):
    """A file or directory that stays unreadable after retries: the declared §1.3 exception."""


class NotPublished(OSError):
    """The publication did not happen; the temporary file is left for recovery (§14)."""


class NotDurable(OSError):
    """The entry is published but its directory flush failed; nothing irreversible may follow (§14)."""


AlreadyExists = platform.AlreadyExists


def token() -> str:
    return secrets.token_hex(8)


class RealFs:
    """The disk, reached only through §14 and §4.4. ``hook(kind, detail)`` is called before each primitive."""

    def __init__(self, hook: Callable[[str, str], None] | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.hook = hook or (lambda kind, detail: None)
        self.sleep = sleep

    # ---- primitives (each passes through the hook, so a campaign can act on it) ----
    def _write_temp(self, path: Path, data: bytes) -> None:
        self.hook("write_temp", str(path))
        platform.write_and_flush(path, data)
        self.hook("after_write_temp", str(path))

    def _rename_noreplace(self, source: Path, target: Path) -> None:
        self.hook("rename", f"{source}->{target}")
        platform.rename_noreplace(source, target)
        self.hook("after_rename", f"{source}->{target}")

    def _rename_replace(self, source: Path, target: Path) -> None:
        self.hook("rename_replace", f"{source}->{target}")
        platform.rename_replace(source, target)
        self.hook("after_rename_replace", f"{source}->{target}")

    def _flush_dir(self, path: Path) -> None:
        self.hook("flush_dir", str(path))
        platform.flush_directory(path)
        self.hook("after_flush_dir", str(path))

    def _unlink(self, path: Path) -> None:
        self.hook("unlink", str(path))
        os.unlink(path)
        self.hook("after_unlink", str(path))

    def _mkdir(self, path: Path) -> None:
        self.hook("mkdir", str(path))
        os.mkdir(path)
        self.hook("after_mkdir", str(path))

    def _read(self, path: Path) -> bytes:
        self.hook("read", str(path))
        with open(path, "rb") as handle:
            return handle.read()

    def _listdir(self, path: Path) -> list[str]:
        self.hook("listdir", str(path))
        return os.listdir(path)

    # ---- retry helper (§14 step 2, §4.4) ----
    def _retrying(self, action: Callable[[], Any]) -> Any:
        last: BaseException | None = None
        for _ in range(platform.RETRIES):
            try:
                return action()
            except (FileNotFoundError, platform.AlreadyExists):
                raise
            except OSError as exc:
                if not platform.is_transient(exc):
                    raise
                last = exc
                self.sleep(platform.RETRY_SECONDS)
        assert last is not None
        raise last

    # ---- reading (§4.4) ----
    def read_bytes(self, path: Path) -> bytes | None:
        """The file's bytes; None only on a confirmed not-found. Any other failure after retries is Unreadable."""
        try:
            return self._retrying(lambda: self._read(Path(path)))
        except FileNotFoundError:
            return None
        except IsADirectoryError as exc:
            raise Unreadable(str(exc)) from exc
        except OSError as exc:
            raise Unreadable(f"unreadable:{path}:{exc}") from exc

    def list_names(self, path: Path) -> list[str] | None:
        """Directory entries; None only on a confirmed not-found. A listing error is Unreadable (A-O2)."""
        try:
            return sorted(self._retrying(lambda: self._listdir(Path(path))))
        except FileNotFoundError:
            return None
        except NotADirectoryError as exc:
            raise Unreadable(str(exc)) from exc
        except OSError as exc:
            raise Unreadable(f"unlistable:{path}:{exc}") from exc

    def is_dir(self, path: Path) -> bool:
        return Path(path).is_dir()

    # ---- writing ----
    def flush_dir(self, path: Path) -> None:
        """Flush a directory, retried; a persistent failure raises NotDurable."""
        try:
            self._retrying(lambda: self._flush_dir(Path(path)))
        except OSError as exc:
            raise NotDurable(f"directory_flush_failed:{path}:{exc}") from exc

    def publish(self, path: Path, data: bytes, *, temp_label: str | None = None) -> None:
        """§14: flushed temp, no-replace write-through rename, directory flush. Durable on return.

        Raises AlreadyExists (refuse), NotPublished (temp left for §6) or NotDurable (published, not durable).
        """
        path = Path(path)
        label = temp_label or path.stem
        temp = path.parent / f".tmp-{label}-{token()}"
        try:
            self._write_temp(temp, data)
        except OSError as exc:
            raise NotPublished(f"temp_write_failed:{path}:{exc}") from exc
        try:
            self._retrying(lambda: self._rename_noreplace(temp, path))
        except platform.AlreadyExists:
            raise
        except OSError as exc:
            if not temp.exists() and self.read_bytes(path) == data:
                pass        # the rename happened despite the error
            else:
                raise NotPublished(f"rename_failed:{path}:{exc}") from exc
        self.flush_dir(path.parent)

    def replace_projection(self, path: Path, data: bytes) -> None:
        """Projections only: same protocol, but the old file is replaced."""
        path = Path(path)
        temp = path.parent / f".tmp-projection-{token()}"
        self._write_temp(temp, data)
        self._retrying(lambda: self._rename_replace(temp, path))
        self.flush_dir(path.parent)

    def rename(self, source: Path, target: Path) -> None:
        """A recovery or quarantine rename: no-replace, then flush both directories (§6, §13.4)."""
        source, target = Path(source), Path(target)
        self._retrying(lambda: self._rename_noreplace(source, target))
        self.flush_dir(target.parent)
        if source.parent != target.parent:
            self.flush_dir(source.parent)

    def unlink(self, path: Path) -> None:
        path = Path(path)
        self._retrying(lambda: self._unlink(path))
        self.flush_dir(path.parent)

    def ensure_dir(self, path: Path) -> None:
        """Create a directory and its missing parents, flushing each parent."""
        path = Path(path)
        missing = []
        probe = path
        while not probe.exists():
            missing.append(probe)
            probe = probe.parent
        for directory in reversed(missing):
            try:
                self._mkdir(directory)
            except FileExistsError:
                pass
            self.flush_dir(directory.parent)

    # ---- children (git, worker, scorer) ----
    def run_child(self, argv: Sequence[str], *, env: Mapping[str, str], input_bytes: bytes | None = None,
                  timeout: float | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
        self.hook("child", " ".join(str(part) for part in argv[:4]))
        result = subprocess.run(list(argv), env=dict(env), input=input_bytes, capture_output=True,
                                timeout=timeout, cwd=str(cwd) if cwd else None, **platform.child_creation_kwargs())
        self.hook("after_child", " ".join(str(part) for part in argv[:4]))
        return result


__all__ = ["RealFs", "Unreadable", "NotPublished", "NotDurable", "AlreadyExists", "token"]
