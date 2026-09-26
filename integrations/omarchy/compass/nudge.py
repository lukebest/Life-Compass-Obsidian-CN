"""Rule reminders. No model calls."""

import json
from datetime import datetime

from compass.config import state_dir
from compass import notify, vault


def in_quiet(now, spec):
    start_s, end_s = str(spec).split("-", 1)
    sh, sm = vault.parse_hhmm(start_s)
    eh, em = vault.parse_hhmm(end_s)
    minutes = now.hour * 60 + now.minute
    start = sh * 60 + sm
    end = eh * 60 + em
    if start <= end:
        return start <= minutes < end
    return minutes >= start or minutes < end


def _path(day):
    return state_dir() / "nudges" / ("%s.json" % day.isoformat())


def load_sent(day):
    path = _path(day)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return list(data) if isinstance(data, list) else []


def save_sent(day, keys):
    path = _path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(keys, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def plan(cfg, now, sent):
    if in_quiet(now, cfg.quiet_hours):
        return []
    sent = set(sent)
    items = []
    summary = vault.summarize_tasks(cfg.vault, cfg, now.date())
    if now.hour >= 8 and summary["overdue"] and "overdue" not in sent:
        labels = "、".join(summary["overdue_labels"][:3])
        items.append(("overdue", "逾期任务", "%d 件逾期。%s" % (summary["overdue"], labels)))
    if now.hour == 16 and now.minute < 20 and summary["due_today"] and "due" not in sent:
        labels = "、".join(summary["due_labels"][:3])
        items.append(("due", "今天到期", "%d 件还没完成。%s" % (summary["due_today"], labels)))
    if now.hour == 20 and now.minute < 20 and "habits" not in sent:
        pending = vault.habit_status(cfg.vault, cfg, now.date())
        if pending:
            items.append(("habits", "习惯还没勾", "、".join(pending)))
    if now.weekday() == 6 and now.hour == 18 and now.minute < 20 and "weekly" not in sent:
        items.append(("weekly", "周复盘", "今天适合看一眼本周笔记。"))
    for block in vault.blocks_near(vault.read_ideal_week(cfg.vault), now):
        key = "block-%02d%02d" % (block["hour"], block["minute"])
        if key in sent:
            continue
        items.append((key, "理想一周", "%02d:%02d %s" % (block["hour"], block["minute"], block["label"])))
    return items


def deliver(cfg, now=None, dry_run=False):
    now = now or datetime.now()
    sent = load_sent(now.date())
    delivered = []
    for key, title, body in plan(cfg, now, sent):
        if len(sent) >= cfg.max_nudges_per_day:
            break
        delivered.append({"key": key, "title": title, "body": body})
        sent.append(key)
        if not dry_run:
            notify.send(title, body)
    if delivered and not dry_run:
        save_sent(now.date(), sent)
    return delivered
