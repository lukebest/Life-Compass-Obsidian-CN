"""Deterministic readers and skeleton writers for the vault."""

import re
from datetime import date, datetime, timedelta
from pathlib import Path

DUE_RE = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
SCHED_RE = re.compile(r"⏳\s*(\d{4}-\d{2}-\d{2})")
TASK_RE = re.compile(r"^- \[( |x|X)\] (.+)$")
FENCE_RE = re.compile(r"^```")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAY_ALIASES = {
    "mon": 0, "monday": 0, "一": 0, "周一": 0,
    "tue": 1, "tuesday": 1, "二": 1, "周二": 1,
    "wed": 2, "wednesday": 2, "三": 2, "周三": 2,
    "thu": 3, "thursday": 3, "四": 3, "周四": 3,
    "fri": 4, "friday": 4, "五": 4, "周五": 4,
    "sat": 5, "saturday": 5, "六": 5, "周六": 5,
    "sun": 6, "sunday": 6, "日": 6, "周日": 6,
}
SKIP_BLOCKS = {"", "lunch", "rest", "sleep", "free", "午休", "休息", "睡觉", "自由"}


def iso_week(day):
    year, week, _weekday = day.isocalendar()
    return "%d-W%02d" % (year, week)


def iso_quarter(day):
    return "%d-Q%d" % (day.year, (day.month - 1) // 3 + 1)


def quarter_end(day):
    month = ((day.month - 1) // 3 + 1) * 3
    if month == 12:
        return date(day.year, 12, 31)
    return date(day.year, month + 1, 1) - timedelta(days=1)


def in_quarter_last_week(day):
    return (quarter_end(day) - day).days <= 6


def parse_hhmm(text):
    hour, minute = text.split(":")
    return int(hour), int(minute)


def iter_markdown(vault, exclude_prefixes):
    vault = Path(vault)
    skip_dirs = {".git", ".obsidian", ".trash", "node_modules", "__pycache__"}
    for dirpath, dirnames, filenames in os_walk(vault):
        dirnames[:] = [name for name in dirnames if name not in skip_dirs and not name.startswith(".")]
        for name in filenames:
            if not name.endswith(".md"):
                continue
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            rel = path.relative_to(vault).as_posix()
            if any(rel.startswith(prefix) for prefix in exclude_prefixes):
                continue
            yield rel, path


def os_walk(vault):
    import os
    return os.walk(vault)


def parse_task_line(line):
    match = TASK_RE.match(line.strip())
    if not match:
        return None
    done = match.group(1).lower() == "x"
    body = match.group(2).strip()
    due = DUE_RE.search(body)
    scheduled = SCHED_RE.search(body)
    return {
        "done": done,
        "text": body,
        "due": due.group(1) if due else None,
        "scheduled": scheduled.group(1) if scheduled else None,
        "high": "⏫" in body,
        "line": line.strip(),
    }


def iter_tasks(vault, exclude_prefixes):
    for rel, path in iter_markdown(vault, exclude_prefixes):
        fenced = False
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            if FENCE_RE.match(line.strip()):
                fenced = not fenced
                continue
            if fenced:
                continue
            task = parse_task_line(line)
            if task:
                task["file"] = rel
                yield task


def open_tasks(vault, cfg):
    return [task for task in iter_tasks(vault, cfg.task_exclude) if not task["done"]]


def task_label(task):
    text = DUE_RE.sub("", task["text"])
    text = SCHED_RE.sub("", text)
    text = re.sub(r"[⏫🔁➕⏳📅]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 48:
        text = text[:47] + "…"
    return text or task["text"][:48]


def select_top(tasks, today, limit=3):
    today_s = today.isoformat()

    def rank(task):
        due = task["due"]
        overdue = bool(due and due < today_s)
        due_today = (due == today_s) or (task["scheduled"] == today_s)
        bucket = 0 if overdue else 1 if due_today else 2
        return (bucket, 0 if task["high"] else 1, due or "9999-99-99", task_label(task))

    ranked = sorted(tasks, key=rank)
    chosen = []
    for task in ranked:
        due = task["due"]
        if due and due < today_s or due == today_s or task["scheduled"] == today_s or task["high"]:
            chosen.append(task_label(task))
        if len(chosen) >= limit:
            break
    if len(chosen) < limit:
        for task in ranked:
            label = task_label(task)
            if label not in chosen:
                chosen.append(label)
            if len(chosen) >= limit:
                break
    return chosen


def summarize_tasks(vault, cfg, today):
    tasks = open_tasks(vault, cfg)
    today_s = today.isoformat()
    overdue = [task for task in tasks if task["due"] and task["due"] < today_s]
    due_today = [task for task in tasks if task["due"] == today_s or task["scheduled"] == today_s]
    return {
        "overdue": len(overdue),
        "due_today": len(due_today),
        "top": select_top(tasks, today, 3),
        "overdue_labels": [task_label(task) for task in overdue[:5]],
        "due_labels": [task_label(task) for task in due_today[:5]],
    }


def read_ideal_week(vault):
    path = Path(vault) / "03 Planning" / "Ideal Week.md"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    header = None
    blocks = []
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        if len(cells) < 2:
            continue
        try:
            hour, minute = parse_hhmm(cells[0])
        except ValueError:
            continue
        for index, cell in enumerate(cells[1:], start=1):
            if index - 1 >= 7:
                break
            label = cell.strip()
            if label.lower() in SKIP_BLOCKS:
                continue
            blocks.append({"weekday": index - 1, "hour": hour, "minute": minute, "label": label})
    return blocks


def blocks_near(blocks, now, before_min=15, after_min=5):
    found = []
    for block in blocks:
        if block["weekday"] != now.weekday():
            continue
        start = now.replace(hour=block["hour"], minute=block["minute"], second=0, microsecond=0)
        delta = (start - now).total_seconds() / 60
        if -after_min <= delta <= before_min:
            found.append(block)
    return found


def frontmatter_map(text):
    if not text.startswith("---"):
        return {}
    from compass.yamlfront import frontmatter as parse
    data, _body = parse(text)
    return data if isinstance(data, dict) else {}


def habit_status(vault, cfg, day):
    path = Path(vault) / cfg.daily_folder / ("%s.md" % day.isoformat())
    if not path.is_file():
        return []
    data = frontmatter_map(path.read_text(encoding="utf-8"))
    pending = []
    for habit in cfg.habits:
        value = data.get(habit)
        if value is False or value is None or value == "":
            pending.append(habit)
    return pending


def ensure_headings(text, headings):
    missing = [heading for heading in headings if not re.search(r"^" + re.escape(heading) + r"\s*$", text, re.M)]
    if not missing:
        return text, False
    parts = [text.rstrip("\n")]
    for heading in missing:
        parts.append("")
        parts.append(heading)
        parts.append("")
    return "\n".join(parts) + "\n", True


def daily_skeleton(cfg, day):
    lines = ["---", "date: %s" % day.isoformat(), "tags:", "  - daily"]
    for question in cfg.questions:
        lines.append("%s: " % question["key"])
    for habit in cfg.habits:
        lines.append("%s: false" % habit)
    lines.append("---")
    lines.append("")
    week = iso_week(day)
    quarter = iso_quarter(day)
    lines.append("« [[%s/%s|本周]] · [[%s/%s|本季度]] »" % (
        cfg.weekly_folder, week, cfg.quarterly_folder, quarter))
    lines.append("")
    lines.append("# %s" % day.isoformat())
    lines.append("")
    for heading in ("## 今日任务", "## 日记", "## 今日成就", "## 感恩", "## 每日自省", "## AI 简报", "## AI 复盘", "## 今日活动"):
        lines.append(heading)
        lines.append("")
    return "\n".join(lines)


def weekly_skeleton(cfg, day):
    week = iso_week(day)
    quarter = iso_quarter(day)
    lines = [
        "---",
        "week: %s" % week,
        "quarter: %s" % quarter,
        "tags:",
        "  - weekly",
        "---",
        "",
        "# %s" % week,
        "",
        "## 本周意图",
        "",
        "## 每周复盘",
        "",
        "### 哪些事进展顺利",
        "",
        "### 哪些事没有进展顺利",
        "",
    ]
    return "\n".join(lines)


def quarterly_skeleton(cfg, day):
    quarter = iso_quarter(day)
    lines = [
        "---",
        "quarter: %s" % quarter,
        "tags:",
        "  - quarterly",
        "---",
        "",
        "# %s" % quarter,
        "",
        "## 季度意图",
        "",
        "## 季度末备忘",
        "",
    ]
    return "\n".join(lines)


def ensure_note(cfg, kind, day):
    vault = Path(cfg.vault)
    if kind == "daily":
        folder = cfg.daily_folder
        name = "%s.md" % day.isoformat()
        skeleton = daily_skeleton(cfg, day)
        headings = ["## AI 简报", "## AI 复盘", "## 今日活动"]
    elif kind == "weekly":
        folder = cfg.weekly_folder
        name = "%s.md" % iso_week(day)
        skeleton = weekly_skeleton(cfg, day)
        headings = ["## 本周意图", "### 哪些事进展顺利", "### 哪些事没有进展顺利"]
    elif kind == "quarterly":
        folder = cfg.quarterly_folder
        name = "%s.md" % iso_quarter(day)
        skeleton = quarterly_skeleton(cfg, day)
        headings = ["## 季度意图", "## 季度末备忘"]
    else:
        raise SystemExit("compass: unknown note kind %s" % kind)
    path = vault / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(skeleton, encoding="utf-8")
        return path, True
    text = path.read_text(encoding="utf-8")
    updated, changed = ensure_headings(text, headings)
    if changed:
        path.write_text(updated, encoding="utf-8")
    return path, changed


def append_under_heading(path, heading, line):
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if not text.endswith("\n") and text:
        text += "\n"
    lines = text.splitlines()
    level = len(heading) - len(heading.lstrip("#"))
    start = None
    for index, existing in enumerate(lines):
        if existing.strip() == heading:
            start = index
            break
    insert_at = len(lines)
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend([heading, "", line])
    else:
        insert_at = len(lines)
        for index in range(start + 1, len(lines)):
            stripped = lines[index].strip()
            if stripped.startswith("#"):
                this = len(stripped) - len(stripped.lstrip("#"))
                if this <= level:
                    insert_at = index
                    break
        lines.insert(insert_at, line)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def replace_marked_block(text, heading, marker, body):
    """Insert or replace the marker block inside a section, keeping other lines."""
    start_mark = "<!-- compass:%s -->" % marker
    end_mark = "<!-- /compass:%s -->" % marker
    block = "\n".join([start_mark, body.rstrip("\n"), end_mark])
    if start_mark in text and end_mark in text:
        pre, rest = text.split(start_mark, 1)
        _old, post = rest.split(end_mark, 1)
        return pre + block + post
    lines = text.splitlines()
    if not any(line.strip() == heading for line in lines):
        if text and not text.endswith("\n"):
            text += "\n"
        return text + "\n%s\n\n%s\n" % (heading, block)
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.strip() == heading:
            out.append("")
            out.append(block)
            inserted = True
    return "\n".join(out) + ("\n" if text.endswith("\n") or True else "")


def inbox_capture_line(text, day, token):
    created = day.isoformat()
    return "- [ ] %s ➕ %s 🧭capture:%s" % (text.strip(), created, token)


def capture_open_lines(text):
    found = []
    for line in text.splitlines():
        if line.startswith("- [ ]") and "🧭capture:" in line:
            found.append(line)
    return found
