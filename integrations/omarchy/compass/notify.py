"""Desktop notifications. Tests can set `sink` to a list."""

import os
import subprocess

sink = None


def send(title, body):
    title = (title or "Compass")[:80]
    body = (body or "")[:400]
    if sink is not None:
        sink.append((title, body))
        return
    if os.environ.get("COMPASS_NO_NOTIFY") == "1":
        return
    try:
        subprocess.run(
            ["notify-send", "-a", "Compass", title, body],
            check=False,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
