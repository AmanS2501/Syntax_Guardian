from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import fnmatch
from typing import Optional

try:
    import pathspec
    _HAS_PATHSPEC = True
except Exception:
    _HAS_PATHSPEC = False

@dataclass(frozen=True)
class FileMeta:
    path: Path
    bytes: int
    lines: int
    language: str

_DEFAULT_LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

HARD_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    ".venv", "venv", "env",
    "__pycache__",
    "node_modules",
    "dist", "build", ".next", ".turbo",
    ".idea", ".vscode",
    ".cache", ".pytest_cache",
}

def detect_language(path: Path) -> str:
    return _DEFAULT_LANG_MAP.get(path.suffix.lower(), "unknown")

def _compile_gitignore(root: Path, extra_excludes: list[str]) -> Optional[object]:
    if not _HAS_PATHSPEC:
        return None
    lines: list[str] = []
    gi = root / ".gitignore"
    if gi.exists():
        try:
            lines.extend(gi.read_text(encoding="utf-8", errors="ignore").splitlines())
        except Exception:
            pass
    lines.extend(extra_excludes or [])
    try:
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)
    except Exception:
        return None

def _matches_any(path: Path, patterns: list[str]) -> bool:
    s = str(path.as_posix())
    for pat in patterns:
        if fnmatch.fnmatch(s, pat):
            return True
    return False

def walk_repo(
    root: Path,
    include: list[str],
    exclude: list[str],
    max_bytes: int,
    follow_symlinks: bool = False,
) -> list[FileMeta]:
    root = root.resolve()
    spec = _compile_gitignore(root, exclude) if _HAS_PATHSPEC else None
    results: list[FileMeta] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        try:
            dir_rel = Path(dirpath).resolve().relative_to(root)
        except Exception:
            dir_rel = Path(dirpath)

        pruned = []
        for d in list(dirnames):
            if str(d) in HARD_EXCLUDE_DIRS:
                pruned.append(d); continue
            d_rel = (dir_rel / d)
            d_rel_str = d_rel.as_posix()
            if spec and spec.match_file(d_rel_str):
                pruned.append(d); continue
            if _matches_any(d_rel, exclude):
                pruned.append(d); continue
        for d in pruned:
            dirnames.remove(d)

        for fname in filenames:
            fpath = Path(dirpath, fname).resolve()
            try:
                rel = fpath.relative_to(root)
            except Exception:
                rel = fpath

            rel_str = rel.as_posix()
            if spec and spec.match_file(rel_str):
                continue
            if _matches_any(rel, exclude):
                continue
            if not _matches_any(rel, include):
                continue

            try:
                size = fpath.stat().st_size
            except FileNotFoundError:
                continue
            if size > max_bytes:
                continue

            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            language = detect_language(fpath)
            results.append(FileMeta(
                path=rel,
                bytes=int(size),
                lines=int(text.count("\n") + 1),
                language=str(language),
            ))
    return sorted(results, key=lambda fm: str(fm.path))
