"""Load Meta/Compass Config.md and the automation block."""

import os
from pathlib import Path

from compass.yamlfront import frontmatter

DEFAULT_JOBS = {
    "morning-brief": "07:30",
    "evening-recap": "21:30",
    "triage": "every 3h 09:00-21:00",
    "board-groom": "18:00",
    "weekly-draft": "Sun 20:00",
    "quarter-prep": "quarter-last-week 20:00",
    "vault-health": "Sun 19:00",
    "nudge": "15m",
    "activity-rollup": "23:50",
}

DEFAULT_CATEGORIES = {
    "code": "cursor,code,zed,nvim,vim,emacs,alacritty,ghostty,kitty,foot",
    "writing": "obsidian",
    "browser": "chromium,firefox,brave,chrome",
    "comms": "signal,telegram,discord,slack",
}


class Config:
    def __init__(self, vault, data):
        self.vault = Path(vault)
        self.data = data
        auto = data.get("automation") or {}
        if not isinstance(auto, dict):
            auto = {}
        self.enabled = auto.get("enabled") is not False
        self.quiet_hours = auto.get("quiet_hours") or "23:00-07:00"
        self.max_nudges_per_day = int(auto.get("max_nudges_per_day") or 8)
        jobs = dict(DEFAULT_JOBS)
        custom = auto.get("jobs") or {}
        if isinstance(custom, dict):
            for key, value in custom.items():
                if value:
                    jobs[key] = str(value)
        self.jobs = jobs
        exclude = auto.get("task_exclude") or ["09 Reading/"]
        if isinstance(exclude, str):
            exclude = [part.strip() for part in exclude.split(",") if part.strip()]
        self.task_exclude = [str(item) for item in exclude]
        activity = auto.get("activity") or {}
        if not isinstance(activity, dict):
            activity = {}
        self.activity_exclude = str(activity.get("exclude") or "hyprlock,omarchy-lock,swaylock")
        self.sample_seconds = int(activity.get("sample_seconds") or 30)
        categories = dict(DEFAULT_CATEGORIES)
        custom_cats = activity.get("categories") or {}
        if isinstance(custom_cats, dict):
            for key, value in custom_cats.items():
                if value:
                    categories[key] = str(value)
        self.activity_categories = categories
        self.locale = str(data.get("locale") or "zh-CN")
        self.daily_folder = str(data.get("daily_folder") or "01 Journal/Daily")
        self.weekly_folder = str(data.get("weekly_folder") or "01 Journal/Weekly")
        self.quarterly_folder = str(data.get("quarterly_folder") or "01 Journal/Quarterly")
        self.questions = []
        for item in data.get("questions") or []:
            if isinstance(item, dict) and item.get("key"):
                self.questions.append({"key": str(item["key"]), "text": str(item.get("text") or item["key"])})
            elif isinstance(item, str):
                self.questions.append({"key": item, "text": item})
        if not self.questions:
            self.questions = [{"key": key, "text": key} for key in (
                "dq_goals", "dq_progress", "dq_meaning", "dq_happy", "dq_relationships", "dq_engaged")]
        habits = data.get("habits") or ["habit_journal", "habit_exercise", "habit_reading"]
        self.habits = [str(item) for item in habits]
        done = data.get("board_done_lanes") or "Done,Published,Archive"
        if isinstance(done, list):
            self.done_lanes = [str(item) for item in done]
        else:
            self.done_lanes = [part.strip() for part in str(done).split(",") if part.strip()]
        self.tasks_file = "08 Tasks/Tasks.md"


def find_install_vault():
    """Vault that contains this package: integrations/omarchy/compass/config.py."""
    here = Path(__file__).resolve()
    candidate = here.parents[3]
    marker = candidate / "Meta" / "Compass Config.md"
    if marker.is_file():
        return candidate
    return None


def load(vault=None):
    env = os.environ.get("COMPASS_VAULT")
    if vault is None and env:
        vault = Path(env)
    if vault is None:
        vault = find_install_vault()
    if vault is None:
        raise SystemExit("compass: cannot find the vault. Set COMPASS_VAULT.")
    vault = Path(vault)
    path = vault / "Meta" / "Compass Config.md"
    if not path.is_file():
        raise SystemExit("compass: missing %s" % path)
    data, _body = frontmatter(path.read_text(encoding="utf-8"))
    auto = data.get("automation") if isinstance(data.get("automation"), dict) else {}
    override = (auto or {}).get("vault_path")
    if override:
        vault = Path(str(override)).expanduser()
        if not vault.is_absolute():
            vault = (find_install_vault() or Path.cwd()) / vault
        path = vault / "Meta" / "Compass Config.md"
        if not path.is_file():
            raise SystemExit("compass: automation.vault_path does not contain Compass Config: %s" % vault)
        data, _body = frontmatter(path.read_text(encoding="utf-8"))
    return Config(vault, data)


def state_dir():
    override = os.environ.get("COMPASS_STATE_DIR")
    if override:
        path = Path(override)
    else:
        xdg = os.environ.get("XDG_STATE_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "state"
        path = base / "compass"
    path.mkdir(parents=True, exist_ok=True)
    return path
