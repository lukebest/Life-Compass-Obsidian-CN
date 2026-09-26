---
type: prompt
purpose: "Append an AI draft of the weekly review, in the person's words, under the two review headings."
schedule: "Sun 20:00"
writes: "append under the weekly note review headings"
risk: "append"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run weekly-draft`. The runner already ensured the weekly note exists.

## Prompt
```
Autonomous mode is on. Do not ask questions. Do not delete or rewrite existing lines. Do not set scores. Quote or lightly compress the person's own sentences. Do not grade.

Job: draft the weekly review for the week that contains the target-date.
1. Read the weekly note named gggg-Www in the weekly folder. Read each daily note linked from it, or the seven dates of that ISO week. Skip missing days. If every existing daily note is tagged example, append one bullet under ### 哪些事进展顺利 that says the week is still seed data, and stop.
2. From the real notes, draft 3 to 5 bullets for what went well and 2 to 4 for what did not. Each bullet starts with "AI 草稿：" and ends with the source day in brackets. Use the person's words.
3. Append the first list under ### 哪些事进展顺利 and the second under ### 哪些事没有进展顺利. Do not edit the dataview blocks or ## 本周意图.
4. Stop.
```
