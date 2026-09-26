"""Foreground app samples. Raw logs stay in the state directory, never in the vault."""

import json
import os
import select
import socket
import subprocess
import time
from datetime import date, datetime
from pathlib import Path

from compass.config import state_dir
from compass import vault as vaultmod


def category_for(class_name, cfg):
    folded = (class_name or "").lower()
    for name, patterns in cfg.activity_categories.items():
        for part in str(patterns).split(","):
            part = part.strip().lower()
            if part and part in folded:
                return name
    return "other"


def excluded_class(class_name, cfg):
    folded = (class_name or "").lower()
    if not folded:
        return True
    for part in str(cfg.activity_exclude).split(","):
        part = part.strip().lower()
        if part and part in folded:
            return True
    return False


def log_path(day):
    directory = state_dir() / "activity"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / ("%s.jsonl" % day.isoformat())


def append_sample(cfg, day, class_name, seconds):
    seconds = int(seconds)
    if seconds <= 0 or excluded_class(class_name, cfg):
        return False
    record = {
        "t": datetime.now().replace(microsecond=0).isoformat(),
        "class": class_name,
        "category": category_for(class_name, cfg),
        "seconds": seconds,
    }
    with log_path(day).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return True


def load_samples(day):
    path = log_path(day)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def format_duration(seconds):
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    if hours:
        return "%dh %dm" % (hours, minutes)
    return "%dm" % max(minutes, 1 if seconds else 0)


def rollup_body(rows):
    if not rows:
        return "今天没有记录到前台应用。"
    by_cat = {}
    by_class = {}
    for row in rows:
        by_cat[row.get("category") or "other"] = by_cat.get(row.get("category") or "other", 0) + int(row.get("seconds") or 0)
        by_class[row.get("class") or "unknown"] = by_class.get(row.get("class") or "unknown", 0) + int(row.get("seconds") or 0)
    lines = ["按类别："]
    for name, seconds in sorted(by_cat.items(), key=lambda item: (-item[1], item[0])):
        lines.append("- %s: %s" % (name, format_duration(seconds)))
    lines.append("")
    lines.append("按应用：")
    for name, seconds in sorted(by_class.items(), key=lambda item: (-item[1], item[0]))[:8]:
        lines.append("- %s: %s" % (name, format_duration(seconds)))
    return "\n".join(lines)


def rollup(cfg, day):
    path, _changed = vaultmod.ensure_note(cfg, "daily", day)
    text = path.read_text(encoding="utf-8")
    updated = vaultmod.replace_marked_block(text, "## 今日活动", "activity", rollup_body(load_samples(day)))
    path.write_text(updated, encoding="utf-8")
    return path


def hypr_socket():
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    runtime = os.environ.get("XDG_RUNTIME_DIR") or ("/run/user/%s" % os.getuid())
    root = Path(runtime) / "hypr"
    if signature:
        candidate = root / signature / ".socket2.sock"
        if candidate.exists():
            return candidate
    if not root.is_dir():
        return None
    found = sorted(root.glob("*/.socket2.sock"), key=lambda item: item.stat().st_mtime, reverse=True)
    return found[0] if found else None


def poll_class():
    try:
        result = subprocess.run(
            ["hyprctl", "activewindow", "-j"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        data = json.loads(result.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return ""
    return str(data.get("class") or "")


def session_locked():
    try:
        result = subprocess.run(
            ["hyprctl", "locked"],
            capture_output=True, text=True, timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (result.stdout or "").strip() == "1"


def _class_from_events(chunk, current):
    text = chunk.decode("utf-8", errors="replace")
    for line in text.splitlines():
        if not line.startswith("activewindow>>"):
            continue
        payload = line.split(">>", 1)[1]
        current = payload.split(",", 1)[0].strip()
    return current


def serve(cfg):
    """Count foreground time while the session is unlocked. Window titles are dropped."""
    current = poll_class()
    last = time.monotonic()
    day = date.today()
    sock = None
    sock_path = None
    while True:
        path = hypr_socket()
        if path != sock_path:
            if sock is not None:
                sock.close()
                sock = None
            sock_path = path
        if path is not None and sock is None:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(str(path))
                sock.setblocking(False)
            except OSError:
                if sock is not None:
                    sock.close()
                sock = None
        timeout = max(5, int(cfg.sample_seconds))
        if sock is not None:
            ready, _, _ = select.select([sock], [], [], timeout)
            if ready:
                try:
                    chunk = sock.recv(8192)
                except OSError:
                    chunk = b""
                if not chunk:
                    sock.close()
                    sock = None
                    sock_path = None
                else:
                    # Credit the previous class before switching.
                    pass
                pending = chunk if chunk else b""
            else:
                pending = b""
        else:
            time.sleep(timeout)
            pending = b""
        now_m = time.monotonic()
        elapsed = min(now_m - last, timeout + 5)
        last = now_m
        today = date.today()
        if today != day:
            day = today
        if not session_locked() and current and elapsed >= 1:
            append_sample(cfg, day, current, elapsed)
        if pending:
            current = _class_from_events(pending, current)
        elif sock is None:
            current = poll_class()
