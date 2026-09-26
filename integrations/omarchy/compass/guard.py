"""Snapshot vault text and undo edits that break autonomous rules."""

import hashlib
import os
from pathlib import Path

from compass.yamlfront import frontmatter

TEXT_SUFFIXES = {
    ".md", ".json", ".js", ".mjs", ".css", ".py", ".qml", ".lua", ".txt",
    ".yml", ".yaml", ".sh", ".jsonc",
}
MAX_BYTES = 4_000_000
SKIP_DIRS = {".git", ".trash", "node_modules", "__pycache__", ".vault-meta"}
APPEND_ONLY = ("01 Journal/", "02 Retreats/", "03 Planning/")
EDITABLE = (
    "08 Tasks/", "04 Projects/", "05 People/", "06 Writing/", "Agent/", "inbox/",
)
# The audit log is written by the runner after enforcement and is not rolled back.
SKIP_SNAPSHOT = ("Agent/Log/",)


def classify(rel):
    rel = rel.replace("\\", "/")
    if rel.startswith(APPEND_ONLY):
        return "append"
    if rel.startswith(EDITABLE):
        return "edit"
    return "deny"


def iter_files(vault):
    vault = Path(vault)
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith(".git")]
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(vault).as_posix()
            if rel.startswith(SKIP_SNAPSHOT):
                continue
            suffix = path.suffix.lower()
            if "/plugins/" in rel and rel.startswith(".obsidian/") and suffix not in {".json", ".css", ".md"}:
                continue
            if suffix not in TEXT_SUFFIXES and not rel.startswith(".obsidian/"):
                continue
            yield rel, path


def _record(path):
    size = path.stat().st_size
    if size > MAX_BYTES:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return {"sha": digest.hexdigest(), "bytes": None}
    data = path.read_bytes()
    return {"sha": hashlib.sha256(data).hexdigest(), "bytes": data}


def snapshot(vault):
    files = {}
    for rel, path in iter_files(vault):
        try:
            files[rel] = _record(path)
        except OSError:
            continue
    return files


def snapshot_paths(vault, rels):
    vault = Path(vault)
    files = {}
    for rel in rels:
        path = vault / rel
        if path.is_file() and not path.is_symlink():
            files[rel] = _record(path)
        else:
            files[rel] = None
    return files


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def preserves_lines(old, new):
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    index = 0
    for line in old_lines:
        found = False
        while index < len(new_lines):
            if new_lines[index] == line:
                found = True
                index += 1
                break
            index += 1
        if not found:
            return False
    return True


def _score_map(text):
    data, _body = frontmatter(text)
    if not isinstance(data, dict):
        return {}
    return {
        key: data.get(key)
        for key in data
        if key.startswith(("dq_", "habit_", "wheel_"))
    }


def scores_unchanged(old, new):
    return _score_map(old) == _score_map(new)


def enforce(vault, before):
    """Restore denied or non-append edits. Return a list of reverted relative paths."""
    vault = Path(vault)
    reverted = []
    seen = set()
    for rel, path in iter_files(vault):
        seen.add(rel)
        current = before.get(rel)
        try:
            data = path.read_bytes()
        except OSError:
            continue
        digest = _sha(data) if len(data) <= MAX_BYTES else None
        if current is None:
            if classify(rel) == "deny":
                path.unlink()
                reverted.append(rel)
            continue
        if digest is not None and digest == current["sha"]:
            continue
        if digest is None and current["bytes"] is None:
            continue
        kind = classify(rel)
        allowed = False
        if kind == "edit":
            allowed = True
        elif kind == "append" and current["bytes"] is not None:
            old = current["bytes"].decode("utf-8", errors="replace")
            new = data.decode("utf-8", errors="replace")
            allowed = preserves_lines(old, new) and scores_unchanged(old, new)
        if not allowed:
            if current["bytes"] is None:
                reverted.append(rel + " (too large to restore)")
                continue
            path.write_bytes(current["bytes"])
            reverted.append(rel)
    for rel, current in before.items():
        if rel in seen or current is None:
            continue
        path = vault / rel
        if not path.exists() and current["bytes"] is not None and classify(rel) != "edit":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(current["bytes"])
            reverted.append(rel)
    return reverted
