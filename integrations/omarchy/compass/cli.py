"""Command line for Compass on Omarchy."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from compass import activity, install, notify, runner, status, vault
from compass.config import load


def _parse_day(text):
    if not text:
        return datetime.now().date()
    return datetime.strptime(text, "%Y-%m-%d").date()


def _capture_text():
    preset = os.environ.get("COMPASS_CAPTURE_TEXT")
    if preset is not None:
        return preset.strip()
    try:
        result = subprocess.run(
            ["omarchy", "menu", "input", "捕获到 Compass", "--width", "520"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return (result.stdout or "").strip()


def _spawn_route():
    if os.environ.get("COMPASS_NO_ROUTE") == "1":
        return
    bin_path = Path(__file__).resolve().parents[1] / "bin" / "compass"
    subprocess.Popen(
        [sys.executable, str(bin_path), "run", "capture-route"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def cmd_status(_args):
    cfg = load()
    payload = status.write(cfg)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_tick(args):
    cfg = load()
    ran = runner.tick(cfg, now=datetime.now(), dry_run=args.dry_run)
    print(json.dumps(ran, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args):
    cfg = load()
    day = _parse_day(args.date)
    result = runner.run_job(cfg, args.job, day=day, now=datetime.now(), dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


def cmd_ensure(args):
    cfg = load()
    path, changed = vault.ensure_note(cfg, args.kind, _parse_day(args.date))
    print("%s %s" % ("created" if changed else "ready", path))
    return 0


def cmd_capture(args):
    cfg = load()
    text = (args.text or "").strip() or _capture_text()
    if not text:
        return 0
    token_line = vault.inbox_capture_line(text, datetime.now().date(), os.urandom(3).hex())
    vault.append_under_heading(cfg.vault / cfg.tasks_file, "## Inbox", token_line)
    notify.send("已收入 Inbox", text[:160])
    if not args.no_route:
        _spawn_route()
    print(token_line)
    return 0


def cmd_undo(args):
    cfg = load()
    print(runner.undo(cfg, args.run_id))
    return 0


def cmd_log(_args):
    cfg = load()
    path = Path(cfg.vault) / "Agent" / "Log" / ("%s.md" % datetime.now().date().isoformat())
    if not path.is_file():
        print("no log for today")
        return 0
    lines = path.read_text(encoding="utf-8").splitlines()
    print("\n".join(lines[-40:]))
    return 0


def cmd_pause(_args):
    status.paused_path().write_text("paused\n", encoding="utf-8")
    cfg = load()
    status.write(cfg, paused=True)
    notify.send("Compass", "自动化已暂停")
    return 0


def cmd_resume(_args):
    path = status.paused_path()
    if path.exists():
        path.unlink()
    cfg = load()
    status.write(cfg, paused=False)
    notify.send("Compass", "自动化已恢复")
    return 0


def cmd_when(args):
    paused = status.is_paused()
    if args.state == "running":
        return 0 if not paused else 1
    if args.state == "paused":
        return 0 if paused else 1
    return 2


def cmd_activity(_args):
    cfg = load()
    activity.serve(cfg)
    return 0


def cmd_nudge(args):
    from compass import nudge
    cfg = load()
    delivered = nudge.deliver(cfg, dry_run=args.dry_run)
    print(json.dumps(delivered, ensure_ascii=False, indent=2))
    return 0


def cmd_open(args):
    cfg = load()
    day = _parse_day(None)
    rel = "%s/%s.md" % (cfg.daily_folder, day.isoformat())
    target = Path(cfg.vault) / rel
    if args.what != "today":
        raise SystemExit("compass: only 'open today' is supported")
    vault.ensure_note(cfg, "daily", day)
    uri = "obsidian://open?vault=%s&file=%s" % (quote(cfg.vault.name), quote(rel))
    try:
        subprocess.Popen(["obsidian", uri], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        subprocess.Popen(["xdg-open", str(target)], start_new_session=True)
    return 0


def cmd_agent(_args):
    cfg = load()
    command = "cd %s && exec omarchy-agent" % json.dumps(str(cfg.vault))
    argv = ["omarchy", "launch", "or", "focus", "tui", "--app-id=compass-agent", "bash", "-lc", command]
    try:
        subprocess.Popen(argv, start_new_session=True)
    except OSError as exc:
        raise SystemExit("compass: could not launch the default agent: %s" % exc)
    return 0


def cmd_install(_args):
    cfg = load()
    for note in install.install(Path.home(), cfg.vault):
        print(note)
    print("compass installed for %s" % cfg.vault)
    return 0


def cmd_uninstall(_args):
    for note in install.uninstall(Path.home()):
        print(note)
    print("compass uninstalled")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="compass")
    sub = parser.add_subparsers(dest="cmd", required=True)

    status_cmd = sub.add_parser("status")
    status_cmd.set_defaults(func=cmd_status)

    tick = sub.add_parser("tick")
    tick.add_argument("--dry-run", action="store_true")
    tick.set_defaults(func=cmd_tick)

    run = sub.add_parser("run")
    run.add_argument("job")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--date")
    run.set_defaults(func=cmd_run)

    ensure = sub.add_parser("ensure")
    ensure.add_argument("kind", choices=("daily", "weekly", "quarterly"))
    ensure.add_argument("date", nargs="?")
    ensure.set_defaults(func=cmd_ensure)

    capture = sub.add_parser("capture")
    capture.add_argument("--text")
    capture.add_argument("--no-route", action="store_true")
    capture.set_defaults(func=cmd_capture)

    undo = sub.add_parser("undo")
    undo.add_argument("run_id", nargs="?")
    undo.set_defaults(func=cmd_undo)

    log = sub.add_parser("log")
    log.set_defaults(func=cmd_log)

    pause = sub.add_parser("pause")
    pause.set_defaults(func=cmd_pause)

    resume = sub.add_parser("resume")
    resume.set_defaults(func=cmd_resume)

    when = sub.add_parser("when")
    when.add_argument("state", choices=("running", "paused"))
    when.set_defaults(func=cmd_when)

    activity_cmd = sub.add_parser("activity")
    activity_cmd.set_defaults(func=cmd_activity)

    nudge = sub.add_parser("nudge")
    nudge.add_argument("--dry-run", action="store_true")
    nudge.set_defaults(func=cmd_nudge)

    open_cmd = sub.add_parser("open")
    open_cmd.add_argument("what", choices=("today",))
    open_cmd.set_defaults(func=cmd_open)

    agent = sub.add_parser("agent")
    agent.set_defaults(func=cmd_agent)

    install_cmd = sub.add_parser("install")
    install_cmd.set_defaults(func=cmd_install)

    uninstall_cmd = sub.add_parser("uninstall")
    uninstall_cmd.set_defaults(func=cmd_uninstall)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
