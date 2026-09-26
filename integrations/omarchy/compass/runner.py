"""Run a job: snapshot, invoke, enforce, log, undo."""

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from compass import agent, guard, notify, vault
from compass.config import state_dir
from compass.jobs import JOBS
from compass import scheduler
from compass import status as statusmod


def _jobs_path():
    return state_dir() / "jobs.json"


def load_state():
    path = _jobs_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(data):
    _jobs_path().write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(name, token, ok, now):
    data = load_state()
    rec = {
        "at": now.replace(microsecond=0).isoformat(),
        "ok": bool(ok),
        "target": token,
    }
    if not ok:
        prev = data.get(name) or {}
        fails = int(prev.get("fails") or 0) + 1
        rec["fails"] = fails
        if fails >= 3:
            nxt = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        else:
            nxt = now + timedelta(minutes=45)
        rec["retry_after"] = nxt.replace(microsecond=0).isoformat()
    data[name] = rec
    save_state(data)
    return rec


def _lock():
    path = state_dir() / "lock"
    if path.exists():
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            if pid != os.getpid():
                return None
        except (OSError, ValueError):
            pass
    path.write_text(str(os.getpid()), encoding="utf-8")
    return path


def _unlock(path):
    if path is None:
        return
    try:
        if path.exists() and path.read_text(encoding="utf-8").strip() == str(os.getpid()):
            path.unlink()
    except OSError:
        return


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _changes(vault_path, before, partial=False):
    changes = {}
    if partial:
        for rel, prev in before.items():
            path = Path(vault_path) / rel
            if not path.is_file():
                if prev:
                    changes[rel] = {"before": prev.get("sha"), "after": None, "existed": True}
                continue
            digest = _sha(path.read_bytes())
            if not prev:
                changes[rel] = {"before": None, "after": digest, "existed": False}
            elif prev.get("sha") != digest:
                changes[rel] = {"before": prev.get("sha"), "after": digest, "existed": True}
        return changes
    seen = set()
    for rel, path in guard.iter_files(vault_path):
        seen.add(rel)
        try:
            data = path.read_bytes()
        except OSError:
            continue
        digest = _sha(data)
        prev = before.get(rel)
        if prev is None:
            changes[rel] = {"before": None, "after": digest, "existed": False}
        elif prev.get("sha") != digest:
            changes[rel] = {"before": prev.get("sha"), "after": digest, "existed": True}
    for rel, prev in before.items():
        if rel in seen or not prev:
            continue
        changes[rel] = {"before": prev.get("sha"), "after": None, "existed": True}
    return changes


def _save_run(run, job, day, token, before, changes, summary, reverted, code):
    directory = state_dir() / "runs" / run
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for rel, info in changes.items():
        if rel.startswith("Agent/Log/"):
            continue
        files[rel] = {"before": info["before"], "after": info["after"], "existed": info["existed"]}
        prev = before.get(rel)
        if prev and prev.get("bytes") is not None and info["existed"]:
            dest = directory / "before" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(prev["bytes"])
    manifest = {
        "id": run,
        "job": job,
        "date": day.isoformat(),
        "token": token,
        "exit": code,
        "summary": summary,
        "reverted": reverted,
        "files": files,
        "undone": False,
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (state_dir() / "last-run").write_text(run, encoding="utf-8")
    return manifest


def _log(cfg, day, body):
    path = Path(cfg.vault) / "Agent" / "Log" / ("%s.md" % day.isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("---\ntags:\n  - agent-log\n---\n\n# Agent log %s\n" % day.isoformat(), encoding="utf-8")
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n" + body.rstrip() + "\n")
    return path


def prompt_for(job, day):
    return (
        "Compass autonomous job\n"
        "COMPASS_AUTONOMOUS=1\n"
        "target-date: %s\n"
        "job: %s\n\n"
        "You are unattended. Follow AGENTS.md section \"Autonomous mode\". "
        "Do not ask questions and do not wait for approval. "
        "A snapshot is taken before you write, and compass undo can restore this run. "
        "If you delete or rewrite existing journal, retreat, or planning lines, the runner reverts those files.\n\n"
        "Read %s and follow its ## Prompt section for %s.\n"
        "Write only what that prompt allows.\n"
        "If you cannot do the job safely, stop without editing notes.\n"
    ) % (day.isoformat(), job.name, job.prompt, day.isoformat())


def run_job(cfg, name, day=None, now=None, token=None, dry_run=False, locked=True):
    if name not in JOBS:
        raise SystemExit("compass: unknown job %s" % name)
    job = JOBS[name]
    now = now or datetime.now()
    day = day or now.date()
    token = token or day.isoformat()
    if job.precheck and not job.precheck(cfg, day):
        return {"ok": True, "skipped": True, "job": name, "id": None}
    if dry_run:
        if job.ensure:
            pass
        return {
            "ok": True,
            "dry_run": True,
            "job": name,
            "date": day.isoformat(),
            "prompt": job.prompt,
            "writes": job.writes,
        }
    lock = _lock() if locked else "held"
    if lock is None:
        return {"ok": False, "job": name, "busy": True, "id": None}
    try:
        if job.ensure:
            vault.ensure_note(cfg, job.ensure, day)
        run = now.strftime("%Y%m%dT%H%M%S") + "-" + name + "-" + secrets.token_hex(2)
        if job.kind == "deterministic":
            rel = "%s/%s.md" % (cfg.daily_folder, day.isoformat())
            before = guard.snapshot_paths(cfg.vault, [rel])
            job.fn(cfg, day)
            changes = _changes(cfg.vault, before, partial=True)
            manifest = _save_run(run, name, day, token, before, changes, "deterministic", [], 0)
            record(name, token, True, now)
            _log(cfg, date_for_log(now), _entry(manifest, []))
            return {"ok": True, "job": name, "id": run, "files": list(manifest["files"])}
        before = guard.snapshot(cfg.vault)
        code, summary = agent.run(
            agent.default_agent(),
            cfg.vault,
            prompt_for(job, day),
            env_extra={"COMPASS_JOB": name, "COMPASS_JOB_DATE": day.isoformat()},
        )
        reverted = guard.enforce(cfg.vault, before)
        changes = _changes(cfg.vault, before)
        ok = code == 0 and not reverted
        manifest = _save_run(run, name, day, token, before, changes, summary, reverted, code)
        record(name, token, ok, now)
        _log(cfg, date_for_log(now), _entry(manifest, reverted))
        title = "Compass " + name
        if reverted:
            body = "已撤回越界修改：%s。撤销 id %s" % (", ".join(reverted[:4]), run)
        elif code != 0:
            body = "没有完成（exit %s）。%s" % (code, (summary or "")[:180])
        else:
            files = ", ".join(list(manifest["files"])[:4]) or "没有文件变化"
            body = "已写入 %s。撤销：compass undo %s" % (files, run)
        notify.send(title, body)
        return {"ok": ok, "job": name, "id": run, "reverted": reverted, "summary": summary, "exit": code}
    finally:
        if locked:
            _unlock(lock)


def date_for_log(now):
    return now.date()


def _entry(manifest, reverted):
    lines = [
        "## %s %s" % (manifest["id"], manifest["job"]),
        "",
        "- 日期：%s" % manifest["date"],
        "- 退出码：%s" % manifest["exit"],
    ]
    if manifest["files"]:
        lines.append("- 文件：%s" % ", ".join(manifest["files"]))
    if reverted:
        lines.append("- 已撤回：%s" % ", ".join(reverted))
    if manifest.get("summary"):
        lines.append("- 摘要：%s" % str(manifest["summary"]).replace("\n", " ")[:400])
    lines.append("- 撤销：`compass undo %s`" % manifest["id"])
    return "\n".join(lines)


def _resolve_run(run_id):
    root = state_dir() / "runs"
    if not root.is_dir():
        raise SystemExit("compass: no runs yet")
    if not run_id:
        last = state_dir() / "last-run"
        if not last.is_file():
            raise SystemExit("compass: no runs yet")
        run_id = last.read_text(encoding="utf-8").strip()
    exact = root / run_id
    if exact.is_dir():
        return exact
    matches = [path for path in root.iterdir() if path.is_dir() and (path.name.startswith(run_id) or path.name.endswith(run_id))]
    if len(matches) != 1:
        raise SystemExit("compass: run id matched %d folders" % len(matches))
    return matches[0]


def undo(cfg, run_id=None):
    folder = _resolve_run(run_id)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("undone"):
        raise SystemExit("compass: %s was already undone" % manifest["id"])
    planned = []
    for rel, info in manifest.get("files", {}).items():
        if rel.startswith("Agent/Log/"):
            continue
        path = Path(cfg.vault) / rel
        current = path.read_bytes() if path.is_file() else None
        after = info.get("after")
        if current is None and after is None:
            continue
        current_sha = hashlib.sha256(current).hexdigest() if current is not None else None
        if current_sha != after:
            raise SystemExit("compass: %s changed after the run; not undoing" % rel)
        before_file = folder / "before" / rel
        if info.get("before") is None:
            planned.append((path, None))
        elif before_file.is_file():
            planned.append((path, before_file.read_bytes()))
        else:
            raise SystemExit("compass: missing snapshot for %s" % rel)
    for path, payload in planned:
        if payload is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    manifest["undone"] = True
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _log(cfg, datetime.now().date(), "## undo %s\n\n- 已恢复 %d 个文件\n" % (manifest["id"], len(planned)))
    notify.send("Compass 撤销", "已恢复 %s" % manifest["id"])
    return manifest["id"]


def _due(cfg, now, state):
    due = []
    for name, job in JOBS.items():
        if name not in cfg.jobs or name == "capture-route":
            continue
        spec = scheduler.parse_spec(cfg.jobs[name])
        if spec[0] == "interval":
            continue
        hit = scheduler.target_for(spec, now, state.get(name), job.catchup_hours, job.overnight)
        if not hit:
            continue
        if job.overnight and hit["date"] < now.date():
            note = Path(cfg.vault) / cfg.daily_folder / ("%s.md" % hit["date"].isoformat())
            if not note.is_file():
                continue
        due.append((name, hit))
    return due


def tick(cfg, now=None, dry_run=False):
    from compass import nudge
    now = now or datetime.now()
    statusmod.write(cfg, now.date())
    if not cfg.enabled or statusmod.is_paused():
        return []
    state = load_state()
    due = _due(cfg, now, state)
    if dry_run:
        ran = [{"job": name, "date": hit["date"].isoformat(), "token": hit["token"], "dry_run": True} for name, hit in due]
        planned = nudge.plan(cfg, now, nudge.load_sent(now.date()))
        if planned:
            ran.append({"nudges": [item[0] for item in planned]})
        return ran
    lock = _lock()
    if lock is None:
        return [{"busy": True}]
    ran = []
    try:
        for name, hit in due:
            ran.append(run_job(cfg, name, day=hit["date"], now=now, token=hit["token"], locked=False))
        nudges = nudge.deliver(cfg, now)
        if nudges:
            ran.append({"nudges": [item["key"] for item in nudges]})
        return ran
    finally:
        _unlock(lock)
