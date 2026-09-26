from __future__ import annotations

"""The private evidence repository of the G-ROUTE3 R7 lifecycle (design §13).

``D/evidence.git`` is a bare repository with one ref, ``refs/heads/evidence``, and a linear, add-only history.
Every git process runs with an environment built from an allowlist (host system and global configuration are
hidden, inherited ``GIT_*`` variables are stripped), a fixed identity and date, no signing, and exact bytes
(``hash-object --no-filters``, ``cat-file blob``). Only the lease holder runs git here, through the ``Fs``
choke point.
"""

from dataclasses import dataclass
import os
import re
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping

REF = "refs/heads/evidence"
MIN_GIT = (2, 38)
IDENTITY = {"GIT_AUTHOR_NAME": "G-ROUTE3 evidence", "GIT_AUTHOR_EMAIL": "g-route3-evidence@localhost",
            "GIT_COMMITTER_NAME": "G-ROUTE3 evidence", "GIT_COMMITTER_EMAIL": "g-route3-evidence@localhost",
            "GIT_AUTHOR_DATE": "1700000000 +0000", "GIT_COMMITTER_DATE": "1700000000 +0000"}
REQUIRED_CONFIG = {"core.fsync": "all", "core.fsyncmethod": "fsync", "gc.auto": "0",
                   "core.logallrefupdates": "always", "core.autocrlf": "false", "core.safecrlf": "false",
                   "core.bare": "true"}


class EvidenceError(RuntimeError):
    """The evidence repository is missing, unreadable, misconfigured, or a commit conflicts (§13.2, §1.3)."""


class AddOnlyConflict(EvidenceError):
    """A path already committed with different bytes: tampering or damage, a declared §1.3 exception."""


@dataclass(frozen=True)
class TreeEntry:
    path: str
    blob: str


def blob_id(data: bytes) -> str:
    """The git blob id of exact bytes (what ``hash-object --no-filters`` would write)."""
    import hashlib
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class EvidenceRepo:
    def __init__(self, git_dir: Path, fs) -> None:
        self.git_dir = Path(git_dir)
        self.fs = fs

    # ---- environment and invocation ----
    def env(self) -> dict[str, str]:
        env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
               "GIT_DIR": str(self.git_dir), "GIT_INDEX_FILE": str(self.git_dir / "g-route3-index"),
               "GIT_OPTIONAL_LOCKS": "0", **IDENTITY}
        if os.name == "nt":
            env["COMSPEC"] = os.environ.get("COMSPEC", "")
        return env

    def git(self, *args: str, input_bytes: bytes | None = None, check: bool = True) -> bytes:
        argv = ["git", "-c", f"safe.directory={self.git_dir.resolve().as_posix()}", "-c", "commit.gpgsign=false",
                *args]
        result = self.fs.run_child(argv, env=self.env(), input_bytes=input_bytes, timeout=300)
        if check and result.returncode != 0:
            raise EvidenceError(f"git_failed:{args[0]}:{result.stderr.decode('utf-8', 'replace')[-300:]}")
        return result.stdout

    # ---- setup (§3.1) ----
    @staticmethod
    def check_git_version(fs) -> str:
        env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        out = fs.run_child(["git", "--version"], env=env, timeout=60).stdout.decode("utf-8", "replace")
        match = re.search(r"(\d+)\.(\d+)", out)
        if not match or (int(match.group(1)), int(match.group(2))) < MIN_GIT:
            raise EvidenceError(f"git_too_old:{out.strip()}")
        return out.strip()

    def initialize(self, root_json: bytes) -> str:
        """Create the bare repository, its config and the root commit holding root.json. Used only while
        building ``D.setup-<token>`` under the setup lock."""
        self.fs.run_child(["git", "init", "--bare", "-q", str(self.git_dir)], env=self.env(), timeout=120)
        for key, value in REQUIRED_CONFIG.items():
            self.git("config", key, value)
        blob = self.git("hash-object", "-w", "--no-filters", "--stdin", input_bytes=root_json).decode().strip()
        tree = self.git("mktree", input_bytes=f"100644 blob {blob}\troot.json\n".encode()).decode().strip()
        commit = self.git("commit-tree", tree, "-m", "G-ROUTE3 evidence root").decode().strip()
        self.git("update-ref", REF, commit, "0" * 40)
        return commit

    # ---- health (§13.2) ----
    def check(self) -> str:
        """Refuse unless the repository, its ref, root commit and config are intact. Returns the head."""
        if not self.fs.is_dir(self.git_dir):
            raise EvidenceError("evidence_repository_missing")
        config = {}
        for line in self.git("config", "--local", "--list").decode("utf-8", "replace").splitlines():
            key, _, value = line.partition("=")
            config[key.strip().lower()] = value.strip()
        wrong = [key for key, value in REQUIRED_CONFIG.items() if config.get(key) != value]
        if wrong or config.get("extensions.refstorage") or (self.git_dir / "reftable").exists():
            raise EvidenceError("evidence_repository_config_wrong:" + ",".join(wrong or ["ref_format"]))
        head = self.head()
        if head is None:
            raise EvidenceError("evidence_ref_missing")
        return head

    def remove_stale_locks(self) -> list[str]:
        """Only the lease holder's children run git here, so any lock the holder finds is stale (§13.2)."""
        removed = []
        for directory, _dirs, files in os.walk(self.git_dir):
            for name in files:
                if name.endswith(".lock"):
                    path = Path(directory) / name
                    self.fs.unlink(path)
                    removed.append(str(path))
        return removed

    def head(self) -> str | None:
        out = self.git("rev-parse", "--verify", "-q", REF, check=False).decode().strip()
        return out or None

    # ---- reading ----
    def tree(self, commit: str | None = None) -> dict[str, str]:
        """path -> blob id of every file at the head (or at ``commit``)."""
        ref = commit or REF
        out = self.git("ls-tree", "-r", "-z", "--full-tree", ref)
        entries = {}
        for record in out.split(b"\0"):
            if not record:
                continue
            meta, _, path = record.partition(b"\t")
            mode, kind, blob = meta.decode().split(" ")
            if kind != "blob":
                raise EvidenceError("evidence_tree_has_non_blob")
            entries[path.decode("utf-8", "surrogateescape")] = blob
        return entries

    def read_blob(self, blob: str) -> bytes:
        return self.read_blobs([blob])[blob]

    def read_blobs(self, blobs) -> dict[str, bytes]:
        """Exact bytes of many blobs with one ``cat-file --batch`` process."""
        wanted = list(dict.fromkeys(blobs))
        if not wanted:
            return {}
        out = self.git("cat-file", "--batch", input_bytes=("\n".join(wanted) + "\n").encode("ascii"))
        result, offset = {}, 0
        for blob in wanted:
            end = out.index(b"\n", offset)
            header = out[offset:end].decode("ascii").split(" ")
            if len(header) != 3 or header[0] != blob or header[1] != "blob":
                raise EvidenceError(f"evidence_blob_unreadable:{blob}")
            size = int(header[2])
            data = out[end + 1:end + 1 + size]
            if len(data) != size or blob_id(data) != blob:
                raise EvidenceError(f"evidence_blob_corrupt:{blob}")
            result[blob] = data
            offset = end + 1 + size + 1
        return result

    def write_blobs(self, contents: list[bytes], staging: Path) -> list[str]:
        """Write many exact blobs with one ``hash-object --stdin-paths`` process via staged copies, checking every
        returned id against the id computed here."""
        import os
        if not contents:
            return []
        folder = Path(staging) / f"evidence-{os.getpid()}-{len(contents)}-{blob_id(b''.join(contents))[:12]}"
        folder.mkdir(parents=True, exist_ok=True)
        paths = []
        try:
            for index, data in enumerate(contents):
                path = folder / f"{index:06d}"
                path.write_bytes(data)
                paths.append(str(path))
            out = self.git("hash-object", "-w", "--no-filters", "--stdin-paths",
                           input_bytes=("\n".join(paths) + "\n").encode("utf-8")).decode().split()
        finally:
            for path in paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            try:
                folder.rmdir()
            except OSError:
                pass
        expected = [blob_id(data) for data in contents]
        if out != expected:
            raise EvidenceError("evidence_blob_id_mismatch")
        return out

    def commit_adding(self, path: str) -> str | None:
        """The commit that added ``path`` (the history is add-only and linear)."""
        out = self.git("rev-list", "--reverse", REF, "--", path).decode().split()
        return out[0] if out else None

    def is_ancestor(self, commit: str) -> bool:
        result = self.fs.run_child(["git", "-c", f"safe.directory={self.git_dir.resolve().as_posix()}",
                                    "merge-base", "--is-ancestor", commit, REF], env=self.env(), timeout=120)
        return result.returncode == 0

    # ---- committing (§13.1, §13.2) ----
    def commit(self, additions: Mapping[str, bytes], message: str, *, staging: Path | None = None) -> str:
        """Add-only commit of ``additions`` (tree path -> exact bytes). Returns the new head, or the current head
        when every path is already committed with identical bytes. A path committed with different bytes raises
        AddOnlyConflict. The ref update is compare-and-swap, re-read after a reported failure, retried 5 times."""
        for path in additions:
            if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
                raise EvidenceError(f"evidence_path_invalid:{path}")
        for attempt in range(5):
            old = self.check()
            current = self.tree(old)
            new_paths = {}
            for path, data in sorted(additions.items()):
                existing = current.get(path)
                if existing is None:
                    new_paths[path] = data
                elif existing != blob_id(data):
                    raise AddOnlyConflict(f"add_only_conflict:{path}")
            if not new_paths:
                return old
            index = self.git_dir / "g-route3-index"
            if index.exists():
                self.fs.unlink(index)
            self.git("read-tree", old)
            ordered = list(new_paths.items())
            if staging is not None:
                blobs = self.write_blobs([data for _, data in ordered], staging)
            else:
                blobs = []
                for _, data in ordered:
                    blob = self.git("hash-object", "-w", "--no-filters", "--stdin", input_bytes=data).decode().strip()
                    if blob != blob_id(data):
                        raise EvidenceError("evidence_blob_id_mismatch")
                    blobs.append(blob)
            lines = [f"100644 {blob}\t{path}\n" for (path, _), blob in zip(ordered, blobs)]
            self.git("update-index", "--add", "--index-info", input_bytes="".join(lines).encode("utf-8"))
            tree = self.git("write-tree").decode().strip()
            commit = self.git("commit-tree", tree, "-p", old, "-m", message).decode().strip()
            result = self.fs.run_child(["git", "-c", f"safe.directory={self.git_dir.resolve().as_posix()}",
                                        "update-ref", REF, commit, old], env=self.env(), timeout=120)
            if result.returncode != 0 and self.head() != commit:
                continue
            self.fs.flush_dir(self.git_dir / "refs" / "heads")
            return commit
        raise EvidenceError("evidence_ref_update_failed_after_retries")


def tree_path(*parts: str) -> str:
    return "/".join(str(part).strip("/") for part in parts)


__all__ = ["REF", "EvidenceRepo", "EvidenceError", "AddOnlyConflict", "TreeEntry", "blob_id", "tree_path"]
