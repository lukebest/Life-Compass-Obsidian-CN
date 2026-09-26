"""Bar status file consumed by the luke.compass widget."""

import json
from datetime import date, datetime

from compass.config import state_dir
from compass import vault


def paused_path():
    return state_dir() / "paused"


def is_paused():
    return paused_path().exists()


def write(cfg, today=None, paused=None):
    today = today or date.today()
    if paused is None:
        paused = is_paused()
    summary = vault.summarize_tasks(cfg.vault, cfg, today)
    payload = {
        "due_today": summary["due_today"],
        "overdue": summary["overdue"],
        "top": summary["top"],
        "paused": bool(paused),
        "enabled": bool(cfg.enabled),
        "updated": datetime.now().replace(microsecond=0).isoformat(),
    }
    path = state_dir() / "status.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
