from __future__ import annotations
import os
import stat
import zipfile
from pathlib import Path


def write_safe_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo("Eidolon/README.md")
        info.external_attr = 0o100644 << 16
        zf.writestr(info, b"safe\n")


def write_malicious_zip(path: Path, kind: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if kind == "traversal":
            zf.writestr("Eidolon/../outside.txt", b"x")
        elif kind == "absolute":
            zf.writestr("/absolute.txt", b"x")
        elif kind == "drive":
            zf.writestr("Eidolon/C:/secret.txt", b"x")
        elif kind == "backslash":
            zf.writestr("Eidolon\\data\\secret.txt", b"x")
        elif kind == "casefold":
            zf.writestr("Eidolon/A.txt", b"a")
            zf.writestr("Eidolon/a.txt", b"b")
        elif kind == "symlink":
            info = zipfile.ZipInfo("Eidolon/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, b"../outside")
        elif kind == "runtime":
            zf.writestr("Eidolon/data/memories.json", b"{}")
        else:
            raise ValueError(kind)


def try_symlink(target: Path, link: Path, *, directory: bool = False) -> bool:
    try:
        os.symlink(target, link, target_is_directory=directory)
        return True
    except (OSError, NotImplementedError):
        return False
