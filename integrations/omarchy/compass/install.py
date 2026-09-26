"""Install and remove the Omarchy desktop hooks. Paths stay under the user config."""

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
PLUGIN_ID = "luke.compass"

BIND_START = "-- >>> compass"
BIND_END = "-- <<< compass"
BINDINGS = """-- >>> compass
o.bind("SUPER + SHIFT + C", "Compass capture", "compass capture")
o.bind("SUPER + SHIFT + J", "Compass today", "compass open today")
o.bind("SUPER + ALT + A", "Compass agent", "compass agent")
-- <<< compass
"""

MENU_START = "// >>> compass"
MENU_END = "// <<< compass"
MENU = """// >>> compass
  "compass": {"icon":"\uf14e","label":"Compass","description":"Life OS"},
  "compass.today": {"icon":"\uf073","label":"今日笔记","action":"compass open today"},
  "compass.capture": {"icon":"\uf040","label":"捕获","action":"compass capture"},
  "compass.brief": {"icon":"\uf0eb","label":"今日简报","action":"compass run morning-brief"},
  "compass.triage": {"icon":"\uf0ae","label":"立即分拣","action":"compass run triage"},
  "compass.weekly": {"icon":"\uf073","label":"周复盘草稿","action":"compass run weekly-draft"},
  "compass.log": {"icon":"\uf15c","label":"运行日志","action":"compass log"},
  "compass.undo": {"icon":"\uf0e2","label":"撤销上次运行","action":"compass undo"},
  "compass.pause": {"icon":"\uf04c","label":"暂停自动化","action":"compass pause","when":"compass when running"},
  "compass.resume": {"icon":"\uf04b","label":"恢复自动化","action":"compass resume","when":"compass when paused"}
// <<< compass
"""

UNITS = ("compass-tick.service", "compass-tick.timer", "compass-activity.service")


def _backup(path):
    if not path.is_file():
        return
    dest = path.with_name(path.name + ".bak." + str(int(time.time())))
    shutil.copy2(path, dest)


def _replace_marked(text, start, end, block):
    if start not in text or end not in text:
        return None
    pre, rest = text.split(start, 1)
    _old, post = rest.split(end, 1)
    body = block.rstrip("\n")
    if body:
        body += "\n"
    return pre + body + post.lstrip("\n")


def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    return text.strip()


def insert_menu(text, block=MENU):
    replaced = _replace_marked(text, MENU_START, MENU_END, block)
    if replaced is not None:
        return replaced
    idx = text.rfind("}")
    if idx < 0:
        raise SystemExit("compass: menu file has no closing brace")
    prefix = _strip_comments(text[:idx])
    joiner = "\n" if prefix.endswith("{") or prefix.endswith(",") else ",\n"
    return text[:idx].rstrip() + joiner + block.rstrip() + "\n" + text[idx:]


def remove_menu(text):
    replaced = _replace_marked(text, MENU_START, MENU_END, "")
    if replaced is None:
        return text
    return re.sub(r",(\s*\n\s*)}", r"\1}", replaced)


def insert_bindings(text, block=BINDINGS):
    replaced = _replace_marked(text, BIND_START, BIND_END, block)
    if replaced is not None:
        return replaced
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block


def remove_bindings(text):
    replaced = _replace_marked(text, BIND_START, BIND_END, "")
    return text if replaced is None else replaced


def add_widget(data):
    layout = data.setdefault("bar", {}).setdefault("layout", {})
    center = layout.setdefault("center", [])
    if any(isinstance(item, dict) and item.get("id") == PLUGIN_ID for item in center):
        return False
    widget = {"id": PLUGIN_ID}
    for index, item in enumerate(center):
        if isinstance(item, dict) and item.get("id") == "omarchy.clock":
            center.insert(index, widget)
            return True
    center.append(widget)
    return True


def remove_widget(data):
    center = data.get("bar", {}).get("layout", {}).get("center", [])
    kept = [item for item in center if not (isinstance(item, dict) and item.get("id") == PLUGIN_ID)]
    if len(kept) == len(center):
        return False
    data["bar"]["layout"]["center"] = kept
    return True


def _symlink(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        if dest.resolve() == src.resolve():
            return "ok"
        dest.unlink()
    elif dest.exists():
        return "exists"
    dest.symlink_to(src)
    return "ok"


def _write_units(home, bin_path):
    unit_dir = home / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    src = PACKAGE / "systemd"
    for name in UNITS:
        text = (src / name).read_text(encoding="utf-8").replace("@COMPASS@", str(bin_path))
        (unit_dir / name).write_text(text, encoding="utf-8")


def _systemctl(args):
    if os.environ.get("COMPASS_SKIP_SYSTEMCTL") == "1":
        return 0
    try:
        result = subprocess.run(["systemctl", "--user", *args], check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return 1
    return result.returncode


def install(home, vault, reload_hypr=True):
    home = Path(home)
    vault = Path(vault)
    bin_path = PACKAGE / "bin" / "compass"
    plugin_src = PACKAGE / "plugin" / PLUGIN_ID
    notes = []
    bin_link = _symlink(bin_path, home / ".local" / "bin" / "compass")
    if bin_link == "exists":
        notes.append("compass is already on PATH as a regular file; left it in place")
    plugin_link = _symlink(plugin_src, home / ".config" / "omarchy" / "plugins" / PLUGIN_ID)
    if plugin_link == "exists":
        notes.append("plugin directory exists and was left in place")

    shell = home / ".config" / "omarchy" / "shell.json"
    if shell.is_file():
        data = json.loads(shell.read_text(encoding="utf-8"))
        if add_widget(data):
            _backup(shell)
            shell.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        notes.append("shell.json missing; bar widget not added")

    bindings = home / ".config" / "hypr" / "bindings.lua"
    if bindings.is_file():
        original = bindings.read_text(encoding="utf-8")
        updated = insert_bindings(original)
        if updated != original:
            _backup(bindings)
            bindings.write_text(updated, encoding="utf-8")
            if reload_hypr and os.environ.get("COMPASS_SKIP_HYPR") != "1":
                try:
                    subprocess.run(["hyprctl", "reload"], check=False, timeout=15)
                except (OSError, subprocess.TimeoutExpired):
                    notes.append("hyprctl reload failed")
    else:
        notes.append("bindings.lua missing; shortcuts not added")

    menu = home / ".config" / "omarchy" / "extensions" / "omarchy-menu.jsonc"
    if menu.is_file():
        original = menu.read_text(encoding="utf-8")
        updated = insert_menu(original)
        if updated != original:
            _backup(menu)
            menu.write_text(updated, encoding="utf-8")
    else:
        notes.append("omarchy-menu.jsonc missing; menu not added")

    _write_units(home, bin_path)
    code = _systemctl(["daemon-reload"])
    code |= _systemctl(["enable", "--now", "compass-tick.timer", "compass-activity.service"])
    if code != 0:
        notes.append("systemctl --user did not enable the units; run compass install again after login")
    return notes


def uninstall(home, reload_hypr=True):
    home = Path(home)
    notes = []
    _systemctl(["disable", "--now", "compass-tick.timer", "compass-activity.service"])
    unit_dir = home / ".config" / "systemd" / "user"
    for name in UNITS:
        path = unit_dir / name
        if path.is_file():
            path.unlink()
    _systemctl(["daemon-reload"])

    for link in (
        home / ".local" / "bin" / "compass",
        home / ".config" / "omarchy" / "plugins" / PLUGIN_ID,
    ):
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            notes.append("left a non-symlink in place")

    shell = home / ".config" / "omarchy" / "shell.json"
    if shell.is_file():
        data = json.loads(shell.read_text(encoding="utf-8"))
        if remove_widget(data):
            _backup(shell)
            shell.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    bindings = home / ".config" / "hypr" / "bindings.lua"
    if bindings.is_file():
        original = bindings.read_text(encoding="utf-8")
        updated = remove_bindings(original)
        if updated != original:
            _backup(bindings)
            bindings.write_text(updated, encoding="utf-8")
            if reload_hypr and os.environ.get("COMPASS_SKIP_HYPR") != "1":
                try:
                    subprocess.run(["hyprctl", "reload"], check=False, timeout=15)
                except (OSError, subprocess.TimeoutExpired):
                    notes.append("hyprctl reload failed")

    menu = home / ".config" / "omarchy" / "extensions" / "omarchy-menu.jsonc"
    if menu.is_file() and MENU_START in menu.read_text(encoding="utf-8"):
        _backup(menu)
        menu.write_text(remove_menu(menu.read_text(encoding="utf-8")), encoding="utf-8")
    return notes
