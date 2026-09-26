"""Headless adapter for the Omarchy default coding agent."""

import json
import os
import shlex
import subprocess

HEADLESS = {
    "cursor-agent": "cursor",
    "claude": "claude",
    "codex": "codex",
}


def default_agent():
    forced = os.environ.get("COMPASS_AGENT")
    if forced:
        return forced.strip()
    try:
        result = subprocess.run(
            ["omarchy-default-agent"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "cursor-agent"
    name = (result.stdout or "").strip()
    return name or "cursor-agent"


def command(agent, vault, prompt):
    vault = str(vault)
    if agent in ("cursor-agent", "cursor"):
        return [
            "cursor-agent", "-p", "--output-format", "json",
            "--workspace", vault, "--trust", "--force", "--approve-mcps",
            prompt,
        ]
    if agent == "claude":
        return ["claude", "-p", "--permission-mode", "bypassPermissions", prompt]
    if agent == "codex":
        return ["codex", "exec", "--full-auto", prompt]
    raise SystemExit(
        "compass: no headless mapping for the default agent %r. "
        "Mapped agents: cursor-agent, claude, codex." % agent
    )


def summarize(raw):
    text = (raw or "").strip()
    if not text:
        return ""
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
    if isinstance(parsed, dict):
        for key in ("result", "text", "message"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:800]
    return text[:800]


def run(agent, vault, prompt, env_extra=None, timeout=600):
    override = os.environ.get("COMPASS_AGENT_CMD")
    if override:
        argv = shlex.split(override) + [prompt]
    else:
        argv = command(agent, vault, prompt)
    env = os.environ.copy()
    env["COMPASS_AUTONOMOUS"] = "1"
    env["COMPASS_VAULT"] = str(vault)
    if env_extra:
        env.update(env_extra)
    try:
        result = subprocess.run(
            argv,
            cwd=str(vault),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, "agent timed out after %s seconds" % timeout
    except OSError as exc:
        return 127, "agent failed to start: %s" % exc
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, summarize(output)
