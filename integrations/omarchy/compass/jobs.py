"""Job table. Prompts live in Prompts/Auto. Writes are enforced here, not by the prompt file."""

from compass import activity, vault


class Job:
    def __init__(self, name, prompt, writes, kind="agent", ensure=None, catchup_hours=6,
                 overnight=False, precheck=None, fn=None):
        self.name = name
        self.prompt = prompt
        self.writes = writes
        self.kind = kind
        self.ensure = ensure
        self.catchup_hours = catchup_hours
        self.overnight = overnight
        self.precheck = precheck
        self.fn = fn


def _capture_pending(cfg, _day):
    path = cfg.vault / cfg.tasks_file
    if not path.is_file():
        return False
    return bool(vault.capture_open_lines(path.read_text(encoding="utf-8")))


def _rollup(cfg, day):
    activity.rollup(cfg, day)


JOBS = {
    "morning-brief": Job(
        "morning-brief",
        "Prompts/Auto/01 Morning Brief.md",
        ["01 Journal/Daily/", "Agent/"],
        ensure="daily",
        catchup_hours=6,
    ),
    "evening-recap": Job(
        "evening-recap",
        "Prompts/Auto/02 Evening Recap.md",
        ["01 Journal/Daily/", "Agent/"],
        ensure="daily",
        catchup_hours=4,
        overnight=True,
    ),
    "triage": Job(
        "triage",
        "Prompts/Auto/03 Task Triage.md",
        ["08 Tasks/", "Agent/"],
        catchup_hours=3,
    ),
    "board-groom": Job(
        "board-groom",
        "Prompts/Auto/04 Board Groom.md",
        ["04 Projects/", "06 Writing/", "Agent/"],
        catchup_hours=6,
    ),
    "weekly-draft": Job(
        "weekly-draft",
        "Prompts/Auto/05 Weekly Draft.md",
        ["01 Journal/Weekly/", "01 Journal/Daily/", "Agent/"],
        ensure="weekly",
        catchup_hours=4,
    ),
    "quarter-prep": Job(
        "quarter-prep",
        "Prompts/Auto/06 Quarter Prep.md",
        ["Agent/"],
        catchup_hours=6,
    ),
    "vault-health": Job(
        "vault-health",
        "Prompts/Auto/07 Vault Health.md",
        ["Agent/"],
        catchup_hours=4,
    ),
    "capture-route": Job(
        "capture-route",
        "Prompts/Auto/08 Capture Route.md",
        ["08 Tasks/", "01 Journal/Daily/", "04 Projects/", "Agent/", "inbox/"],
        ensure="daily",
        precheck=_capture_pending,
    ),
    "activity-rollup": Job(
        "activity-rollup",
        None,
        ["01 Journal/Daily/"],
        kind="deterministic",
        ensure="daily",
        catchup_hours=8,
        overnight=True,
        fn=_rollup,
    ),
}
