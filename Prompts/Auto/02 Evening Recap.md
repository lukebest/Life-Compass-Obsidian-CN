---
type: prompt
purpose: "Append an evening draft to today's daily note and suggest daily-question scores without writing them."
schedule: "21:30"
writes: "append under ## AI 复盘 in the target daily note"
risk: "append"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run evening-recap`. Overnight catch-up uses the target-date from the wrapper, which may be yesterday.

## Prompt
```
Autonomous mode is on. Do not ask questions and do not wait for approval. Do not delete or rewrite any existing line. Do not set dq_* , habit_* , or wheel_* values. Suggest scores in prose only.

Job: evening recap for the target-date.
1. Read that day's daily note, 08 Tasks/Tasks.md, and ## 今日活动 if the daily note has it. Collect ## 日记, ## 今日成就, ## 感恩, and habit_* values. Quote the person's sentences. Do not grade them. If the note is tagged example, say it is seed data and do not invent a day.
2. List tasks completed that day (a checked line with ✅ on the target date, or a checked line you can tie to that date from the note). If you cannot tell, say so.
3. Append a new subsection under ## AI 复盘, headed ### HH:MM. Include: what the notes actually say, habits still open, and one suggested score per dq_* question with a one-line reason. Label the scores 建议, not 记录.
4. Do not edit the properties. Stop.
```
