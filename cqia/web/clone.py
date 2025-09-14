from __future__ import annotations
import re
import shutil
import subprocess
import time
import os
import stat
from pathlib import Path
from typing import Optional

SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")

def _safe_repo_dir_name(repo_url: str) -> str:
    name = repo_url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    name = SAFE_CHARS.sub("_", name).strip("_") or f"repo_{int(time.time())}"
    return name

def _force_rmtree(path: Path) -> None:
    """
    Robustly delete Windows directories including .git entries with read-only bits.
    """
    def onerror(func, p, excinfo):
        try:
            os.chmod(p, stat.S_IWRITE)
        except Exception:
            pass
        func(p)
    if path.exists():
        shutil.rmtree(path, onerror=onerror)  # handles read-only .git files on Windows

def shallow_clone(repo_url: str, dest_dir: Path, branch: Optional[str] = None, mode: str = "clean") -> Path:
    """
    Shallow clone a repo into dest_dir/<safe_name>.
    mode:
      - 'clean': if target exists, delete it first (robust on Windows).
      - 'unique': if target exists, create a new folder with timestamp suffix.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    base = _safe_repo_dir_name(repo_url)
    target = dest_dir / base

    if target.exists():
        if mode == "unique":
            target = dest_dir / f"{base}-{int(time.time())}"
        else:
            _force_rmtree(target)

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch, "--single-branch"]
    cmd += [repo_url, str(target)]
    subprocess.run(cmd, check=True)
    return target
