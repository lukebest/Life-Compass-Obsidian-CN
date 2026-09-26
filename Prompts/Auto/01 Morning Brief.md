---
type: prompt
purpose: "Write today's brief into the daily note: three tasks, what is due or overdue, and the Ideal Week block."
schedule: "07:30"
writes: "append under ## AI 简报 in today's daily note"
risk: "append"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run morning-brief`. The runner already created today's daily note if it was missing.

## Prompt
```
Autonomous mode is on. Do not ask questions and do not wait for approval. Do not delete or rewrite any existing line. Do not set dq_* , habit_* , or wheel_* values.

Job: morning brief for the target-date in the wrapper (default today).
1. Read Meta/Compass Config.md, 08 Tasks/Tasks.md, 03 Planning/Ideal Week.md, and today's note in the daily folder. Read this week's weekly note if it exists, including ## 本周意图. Ignore notes tagged example when quoting a journal. Tasks may still be listed.
2. Pick at most three open tasks for the target date. Prefer overdue, then due or scheduled that day, then high priority (⏫). Do not invent tasks.
3. From the Ideal Week table, list the target date's blocks. Do not treat an example grid as a personal commitment: if Ideal Week.md has example: true, say the grid is still the template.
4. Append a new subsection under ## AI 简报. Heading: ### HH:MM (the current time). Bullets: 三件事, 逾期, 今天到期, 理想一周. If a list is empty, write 无. Leave every other section untouched.
5. Stop. The runner sends the desktop notification.
```
