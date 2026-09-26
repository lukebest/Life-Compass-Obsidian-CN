"""Decide which configured jobs are due."""

import re
from datetime import datetime, timedelta

from compass.vault import in_quarter_last_week, iso_quarter

WEEKDAY = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}


def parse_clock(text):
    hour, minute = text.split(":")
    return int(hour), int(minute)


def parse_spec(spec):
    spec = spec.strip()
    if re.fullmatch(r"\d+m", spec):
        return ("interval", int(spec[:-1]))
    match = re.fullmatch(r"every (\d+)h (\d{2}:\d{2})-(\d{2}:\d{2})", spec)
    if match:
        return ("window", int(match.group(1)), match.group(2), match.group(3))
    match = re.fullmatch(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{2}:\d{2})", spec)
    if match:
        return ("weekday", WEEKDAY[match.group(1)], match.group(2))
    match = re.fullmatch(r"quarter-last-week (\d{2}:\d{2})", spec)
    if match:
        return ("quarter-last-week", match.group(1))
    match = re.fullmatch(r"(\d{2}:\d{2})", spec)
    if match:
        return ("daily", match.group(1))
    raise ValueError("unsupported schedule: %s" % spec)


def _at(day, clock):
    hour, minute = parse_clock(clock)
    return datetime(day.year, day.month, day.day, hour, minute)


def _done_for(last, token):
    if not last:
        return False
    return last.get("ok") and last.get("target") == token


def _retry_wait(last, now):
    if not last or last.get("ok"):
        return False
    retry = last.get("retry_after")
    if not retry:
        return False
    try:
        return now < datetime.fromisoformat(retry)
    except ValueError:
        return False


def _hit(day):
    return {"date": day, "token": day.isoformat()}


def target_for(spec, now, last, catchup_hours=6, overnight=False):
    """Return {date, token} when the job should run, else None."""
    kind = spec[0]
    if kind == "interval":
        return None
    if _retry_wait(last, now):
        return None
    if kind == "daily":
        scheduled = _at(now.date(), spec[1])
        if scheduled <= now <= scheduled + timedelta(hours=catchup_hours) and not _done_for(last, now.date().isoformat()):
            return _hit(now.date())
        if overnight and now.hour < 12:
            yesterday = now.date() - timedelta(days=1)
            if not _done_for(last, yesterday.isoformat()):
                late = _at(yesterday, spec[1])
                if now - late <= timedelta(hours=18):
                    return _hit(yesterday)
        return None
    if kind == "weekday":
        if now.weekday() != spec[1]:
            return None
        scheduled = _at(now.date(), spec[2])
        if scheduled <= now <= scheduled + timedelta(hours=catchup_hours) and not _done_for(last, now.date().isoformat()):
            return _hit(now.date())
        return None
    if kind == "window":
        start = _at(now.date(), spec[2])
        end = _at(now.date(), spec[3])
        if not (start <= now <= end):
            return None
        slot = start
        current = None
        while slot <= now:
            current = slot
            slot += timedelta(hours=spec[1])
        if current is None:
            return None
        token = current.isoformat(timespec="minutes")
        if _done_for(last, token):
            return None
        return {"date": now.date(), "token": token}
    if kind == "quarter-last-week":
        if not in_quarter_last_week(now.date()):
            return None
        scheduled = _at(now.date(), spec[1])
        if now < scheduled:
            return None
        token = "Q:" + iso_quarter(now.date())
        if _done_for(last, token):
            return None
        return {"date": now.date(), "token": token}
    return None
