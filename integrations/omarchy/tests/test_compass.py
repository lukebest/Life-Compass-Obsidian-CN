#!/usr/bin/env python3
"""Synthetic-vault tests for the Omarchy integration. No network, no live journal."""

import json
import os
import shlex
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compass import activity, guard, nudge, runner, vault
from compass.config import load
from compass.cli import agent_terminal_command
from compass.install import add_widget, insert_bindings, insert_menu, install, remove_menu, uninstall
from compass.scheduler import parse_spec, target_for
from compass.yamlfront import parse_yaml

LIVE = Path(__file__).resolve().parents[3]
DAY = date(2026, 9, 26)


CONFIG = """---
locale: zh-CN
birthdate:
questions:
  - key: dq_goals
    text: 目标
habits:
  - habit_journal
automation:
  enabled: true
  quiet_hours: "23:00-07:00"
  max_nudges_per_day: 8
  task_exclude:
    - 09 Reading/
---
# config
"""


class CompassTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = root / "home"
        self.vault = root / "vault"
        self.state = root / "state"
        self.home.mkdir()
        self.vault.mkdir()
        self._env = {
            "COMPASS_VAULT": os.environ.get("COMPASS_VAULT"),
            "COMPASS_STATE_DIR": os.environ.get("COMPASS_STATE_DIR"),
            "COMPASS_NO_NOTIFY": os.environ.get("COMPASS_NO_NOTIFY"),
            "COMPASS_NO_ROUTE": os.environ.get("COMPASS_NO_ROUTE"),
            "COMPASS_SKIP_SYSTEMCTL": os.environ.get("COMPASS_SKIP_SYSTEMCTL"),
            "COMPASS_SKIP_HYPR": os.environ.get("COMPASS_SKIP_HYPR"),
            "COMPASS_AGENT_CMD": os.environ.get("COMPASS_AGENT_CMD"),
        }
        os.environ["COMPASS_VAULT"] = str(self.vault)
        os.environ["COMPASS_STATE_DIR"] = str(self.state)
        os.environ["COMPASS_NO_NOTIFY"] = "1"
        os.environ["COMPASS_NO_ROUTE"] = "1"
        os.environ["COMPASS_SKIP_SYSTEMCTL"] = "1"
        os.environ["COMPASS_SKIP_HYPR"] = "1"
        os.environ.pop("COMPASS_AGENT_CMD", None)
        self._write("Meta/Compass Config.md", CONFIG)
        self._write("08 Tasks/Tasks.md", """---
tags:
  - tasks
---
# Tasks

## Inbox
- [ ] 逾期的事 📅 2026-09-01
- [ ] 今天的事 📅 2026-09-26 ⏫
```
- [ ] 代码块里的 📅 2020-01-01
```

## Someday
- [ ] 以后再说
""")
        self._write("09 Reading/Plan.md", "- [ ] 阅读计划 📅 2020-01-01\n")
        self._write("03 Planning/Ideal Week.md", """---
example: false
---
| Block | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 08:00 | Deep | Deep | Deep | Deep | Deep | Family time | Rest |
| 12:00 | Lunch | Lunch | Lunch | Lunch | Lunch | Lunch | Lunch |
""")
        self.cfg = load(self.vault)

    def tearDown(self):
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def _write(self, rel, text):
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_live_config_parses(self):
        cfg = load(LIVE)
        self.assertEqual(len(cfg.questions), 6)
        self.assertEqual(cfg.jobs["morning-brief"], "07:30")
        self.assertEqual(cfg.jobs["triage"], "every 3h 09:00-21:00")
        self.assertIn("obsidian", cfg.activity_categories["writing"])
        self.assertTrue(cfg.enabled)
        data = parse_yaml((LIVE / "Meta" / "Compass Config.md").read_text(encoding="utf-8").split("---", 2)[1])
        self.assertEqual(data["questions"][0]["key"], "dq_goals")

    def test_task_summary_skips_fences_and_reading(self):
        summary = vault.summarize_tasks(self.vault, self.cfg, DAY)
        self.assertEqual(summary["overdue"], 1)
        self.assertEqual(summary["due_today"], 1)
        self.assertEqual(summary["top"][0], "逾期的事")
        self.assertIn("今天的事", summary["top"])
        self.assertTrue(all("阅读" not in item and "代码块" not in item for item in summary["top"]))

    def test_ideal_week_skips_lunch_and_matches_weekday(self):
        blocks = vault.read_ideal_week(self.vault)
        self.assertTrue(all(block["label"].lower() != "lunch" for block in blocks))
        near = vault.blocks_near(blocks, datetime(2026, 9, 26, 7, 50))
        self.assertEqual([block["label"] for block in near], ["Family time"])

    def test_ensure_daily_is_idempotent(self):
        path, created = vault.ensure_note(self.cfg, "daily", DAY)
        self.assertTrue(created)
        text = path.read_text(encoding="utf-8")
        self.assertIn("dq_goals:", text)
        self.assertIn("habit_journal: false", text)
        self.assertIn("## AI 简报", text)
        _path, again = vault.ensure_note(self.cfg, "daily", DAY)
        self.assertFalse(again)

    def test_quiet_hours_and_nudge_cap(self):
        self.assertTrue(nudge.in_quiet(datetime(2026, 9, 26, 6, 30), "23:00-07:00"))
        self.assertFalse(nudge.in_quiet(datetime(2026, 9, 26, 7, 0), "23:00-07:00"))
        self.assertTrue(nudge.in_quiet(datetime(2026, 9, 26, 23, 15), "23:00-07:00"))
        self.assertEqual(nudge.plan(self.cfg, datetime(2026, 9, 26, 6, 40), []), [])
        sent = nudge.deliver(self.cfg, datetime(2026, 9, 26, 16, 5))
        keys = [item["key"] for item in sent]
        self.assertIn("overdue", keys)
        self.assertIn("due", keys)
        self.cfg.max_nudges_per_day = 1
        nudge.save_sent(DAY, [])
        first = nudge.deliver(self.cfg, datetime(2026, 9, 26, 8, 0))
        self.assertEqual(len(first), 1)
        second = nudge.deliver(self.cfg, datetime(2026, 9, 26, 8, 0))
        self.assertEqual(second, [])

    def test_scheduler(self):
        morning = parse_spec("07:30")
        now = datetime(2026, 9, 26, 7, 35)
        hit = target_for(morning, now, None, catchup_hours=6)
        self.assertEqual(hit["token"], "2026-09-26")
        self.assertIsNone(target_for(morning, now, {"ok": True, "target": "2026-09-26"}, 6))
        self.assertIsNone(target_for(morning, datetime(2026, 9, 26, 18, 0), None, 6))
        window = parse_spec("every 3h 09:00-21:00")
        self.assertIsNone(target_for(window, datetime(2026, 9, 26, 8, 0), None))
        self.assertIsNotNone(target_for(window, datetime(2026, 9, 26, 9, 10), None))
        quarter = parse_spec("quarter-last-week 20:00")
        qhit = target_for(quarter, datetime(2026, 9, 26, 20, 5), None)
        self.assertEqual(qhit["token"], "Q:2026-Q3")
        self.assertIsNone(target_for(quarter, datetime(2026, 9, 26, 20, 5), {"ok": True, "target": "Q:2026-Q3"}))
        self.assertIsNone(target_for(quarter, datetime(2026, 9, 1, 20, 5), None))
        sunday = parse_spec("Sun 20:00")
        self.assertIsNotNone(target_for(sunday, datetime(2026, 9, 27, 20, 10), None, 4))
        self.assertIsNone(target_for(sunday, datetime(2026, 9, 26, 20, 10), None, 4))
        evening = parse_spec("21:30")
        caught = target_for(evening, datetime(2026, 9, 27, 8, 0), None, catchup_hours=4, overnight=True)
        self.assertEqual(caught["date"], date(2026, 9, 26))

    def test_guard_allows_append_and_reverts_rewrite(self):
        note = self._write("01 Journal/Daily/2026-09-26.md", "# 2026-09-26\n\n## 日记\n\n原来的句子\n")
        before = guard.snapshot(self.vault)
        note.write_text(note.read_text(encoding="utf-8") + "新的一行\n", encoding="utf-8")
        self.assertEqual(guard.enforce(self.vault, before), [])
        self.assertIn("新的一行", note.read_text(encoding="utf-8"))
        before = guard.snapshot(self.vault)
        note.write_text(note.read_text(encoding="utf-8").replace("# 2026-09-26", "# changed"), encoding="utf-8")
        reverted = guard.enforce(self.vault, before)
        self.assertTrue(reverted)
        self.assertIn("# 2026-09-26", note.read_text(encoding="utf-8"))
        tasks = self.vault / "08 Tasks/Tasks.md"
        before = guard.snapshot(self.vault)
        tasks.write_text(tasks.read_text(encoding="utf-8").replace("今天的事", "今天的事 #project/demo"), encoding="utf-8")
        self.assertEqual(guard.enforce(self.vault, before), [])

    def test_runner_appends_and_undoes(self):
        stub = Path(self.tmp.name) / "stub.py"
        stub.write_text(
            "import os\nfrom pathlib import Path\n"
            "vault = Path(os.environ['COMPASS_VAULT'])\n"
            "day = os.environ['COMPASS_JOB_DATE']\n"
            "path = vault / '01 Journal' / 'Daily' / (day + '.md')\n"
            "path.write_text(path.read_text(encoding='utf-8') + '\\n- 三件事：写测试\\n', encoding='utf-8')\n"
            "print('ok')\n",
            encoding="utf-8",
        )
        os.environ["COMPASS_AGENT_CMD"] = "%s %s" % (sys.executable, stub)
        result = runner.run_job(self.cfg, "morning-brief", day=DAY, now=datetime(2026, 9, 26, 7, 35))
        self.assertTrue(result["ok"], result)
        note = self.vault / "01 Journal" / "Daily" / "2026-09-26.md"
        self.assertIn("三件事：写测试", note.read_text(encoding="utf-8"))
        runner.undo(self.cfg, result["id"])
        self.assertNotIn("三件事：写测试", note.read_text(encoding="utf-8"))
        log = (self.vault / "Agent" / "Log" / "2026-09-26.md").read_text(encoding="utf-8")
        self.assertIn(result["id"], log)

    def test_runner_reverts_journal_rewrite(self):
        stub = Path(self.tmp.name) / "bad.py"
        stub.write_text(
            "import os\nfrom pathlib import Path\n"
            "vault = Path(os.environ['COMPASS_VAULT'])\n"
            "day = os.environ['COMPASS_JOB_DATE']\n"
            "path = vault / '01 Journal' / 'Daily' / (day + '.md')\n"
            "text = path.read_text(encoding='utf-8').replace('# ' + day, '# changed')\n"
            "path.write_text(text, encoding='utf-8')\n"
            "print('ok')\n",
            encoding="utf-8",
        )
        os.environ["COMPASS_AGENT_CMD"] = "%s %s" % (sys.executable, stub)
        result = runner.run_job(self.cfg, "morning-brief", day=DAY, now=datetime(2026, 9, 26, 7, 36))
        self.assertFalse(result["ok"])
        note = (self.vault / "01 Journal" / "Daily" / "2026-09-26.md").read_text(encoding="utf-8")
        self.assertIn("# 2026-09-26", note)
        self.assertNotIn("# changed", note)

    def test_activity_rollup_keeps_user_lines_and_skips_titles(self):
        self.assertEqual(activity.category_for("cursor", self.cfg), "code")
        self.assertTrue(activity.excluded_class("hyprlock", self.cfg))
        self.assertFalse(activity.append_sample(self.cfg, DAY, "hyprlock", 30))
        activity.append_sample(self.cfg, DAY, "obsidian", 120)
        row = activity.load_samples(DAY)[0]
        self.assertNotIn("title", row)
        path = activity.rollup(self.cfg, DAY)
        text = path.read_text(encoding="utf-8")
        self.assertIn("writing", text)
        path.write_text(text.replace("<!-- /compass:activity -->", "<!-- /compass:activity -->\n我自己的一行\n"), encoding="utf-8")
        activity.rollup(self.cfg, DAY)
        updated = path.read_text(encoding="utf-8")
        self.assertIn("我自己的一行", updated)
        self.assertEqual(updated.count("<!-- compass:activity -->"), 1)

    def test_capture_lands_in_inbox(self):
        from compass.cli import cmd_capture

        class Args:
            text = "买牛奶"
            no_route = True

        self.assertEqual(cmd_capture(Args()), 0)
        inbox = (self.vault / "08 Tasks/Tasks.md").read_text(encoding="utf-8")
        self.assertIn("买牛奶", inbox)
        self.assertIn("🧭capture:", inbox)
        self.assertTrue(vault.capture_open_lines(inbox))

    def test_tick_dry_run_selects_morning_only(self):
        ran = runner.tick(self.cfg, now=datetime(2026, 9, 26, 7, 35), dry_run=True)
        jobs = [item["job"] for item in ran if "job" in item]
        self.assertEqual(jobs, ["morning-brief"])
        status = json.loads((self.state / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["overdue"], 1)
        self.assertEqual(status["due_today"], 1)

    def test_install_is_idempotent(self):
        (self.home / ".config/omarchy/extensions").mkdir(parents=True)
        (self.home / ".config/hypr").mkdir(parents=True)
        shell = self.home / ".config/omarchy/shell.json"
        shell.write_text(json.dumps({"version": 1, "bar": {"layout": {"center": [{"id": "omarchy.clock"}]}}}), encoding="utf-8")
        bindings = self.home / ".config/hypr/bindings.lua"
        bindings.write_text('-- existing\no.bind("SUPER + A", "Example", "true")\n', encoding="utf-8")
        menu = self.home / ".config/omarchy/extensions/omarchy-menu.jsonc"
        menu.write_text('{\n  // note\n  "about": {"label": "About"}\n}\n', encoding="utf-8")
        notes = install(self.home, self.vault, reload_hypr=False)
        self.assertFalse(any("missing" in note for note in notes))
        linked = self.home / ".local/bin/compass"
        self.assertTrue(linked.is_symlink())
        data = json.loads(shell.read_text(encoding="utf-8"))
        ids = [item["id"] for item in data["bar"]["layout"]["center"]]
        self.assertEqual(ids[0], "luke.compass")
        self.assertIn("omarchy.clock", ids)
        self.assertEqual(bindings.read_text(encoding="utf-8").count("-- >>> compass"), 1)
        once = menu.read_text(encoding="utf-8")
        self.assertEqual(insert_menu(once), once)
        self.assertEqual(insert_bindings(bindings.read_text(encoding="utf-8")), bindings.read_text(encoding="utf-8"))
        stripped = "\n".join(line for line in once.splitlines() if not line.strip().startswith("//"))
        json.loads(stripped)
        unit = (self.home / ".config/systemd/user/compass-tick.service").read_text(encoding="utf-8")
        self.assertIn(" tick", unit)
        self.assertNotIn("@COMPASS@", unit)
        timer = (self.home / ".config/systemd/user/compass-tick.timer").read_text(encoding="utf-8")
        self.assertIn("Persistent=true", timer)
        install(self.home, self.vault, reload_hypr=False)
        self.assertEqual(bindings.read_text(encoding="utf-8").count("SUPER + SHIFT + C"), 1)
        uninstall(self.home, reload_hypr=False)
        self.assertFalse(linked.exists())
        self.assertNotIn("luke.compass", json.loads(shell.read_text(encoding="utf-8"))["bar"]["layout"]["center"][0]["id"])
        self.assertNotIn("-- >>> compass", bindings.read_text(encoding="utf-8"))
        self.assertNotIn("// >>> compass", menu.read_text(encoding="utf-8"))
        self.assertFalse((self.home / ".config/systemd/user/compass-tick.timer").exists())

    def test_agent_launch_keeps_the_binary_as_one_argument(self):
        command = agent_terminal_command("/tmp/vault with space/bin/compass")
        parts = shlex.split(command)
        self.assertEqual(parts[:2], ["omarchy-launch-tui", "--app-id=compass-agent"])
        self.assertEqual(parts[2], "/tmp/vault with space/bin/compass")
        self.assertEqual(parts[3:], ["agent", "--inside"])

    def test_menu_helpers_round_trip(self):
        original = '{\n  "about": {"label": "About"}\n}\n'
        updated = insert_menu(original)
        self.assertEqual(insert_menu(updated), updated)
        removed = remove_menu(updated)
        self.assertNotIn("compass", removed)
        data = {"bar": {"layout": {"center": [{"id": "omarchy.clock"}]}}}
        self.assertTrue(add_widget(data))
        self.assertFalse(add_widget(data))


if __name__ == "__main__":
    unittest.main()
