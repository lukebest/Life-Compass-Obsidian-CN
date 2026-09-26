---
type: prompt
purpose: "Route one captured line out of the inbox into a task, the daily note, or the projects board."
schedule: "on capture"
writes: "the captured task line, today's journal, or one board card"
risk: "edit"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run capture-route`. The raw line is already in the inbox, so nothing is lost if you stop.

## Prompt
```
Autonomous mode is on. Do not ask questions. Do not delete a captured line. You may check it off, retag it, or copy its text elsewhere.

Job: route open inbox lines that contain 🧭capture:.
1. Read 08 Tasks/Tasks.md. For each open line with 🧭capture:, decide one destination from the text alone:
   - a task: add a date or tag when the text supports it, and remove the 🧭capture token from that line. Leave it open.
   - a journal line: append the person's exact words as one bullet under ## 日记 in the target day's daily note, then check the inbox line off.
   - a project idea: append the exact text as a card under ## Ideas in 04 Projects/Projects Board.md, then check the inbox line off.
   - unsure: leave the open inbox line unchanged.
2. Do not invent dates, projects, or people. Do not edit any other journal section.
3. Stop.
```
