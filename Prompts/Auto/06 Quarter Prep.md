---
type: prompt
purpose: "Write a read-only quarter prep report under Agent/Reports."
schedule: "quarter-last-week 20:00"
writes: "a new file in Agent/Reports"
risk: "append"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run quarter-prep`. This job does not edit the journal, the retreat, or the quarterly note.

## Prompt
```
Autonomous mode is on. Do not ask questions. The only file you may create or append is Agent/Reports/<YYYY-QN>-prep.md. Do not edit any other note.

Job: prepare the quarterly retreat for the quarter that contains the target-date.
1. Read Meta/Compass Config.md, the quarterly note if it exists, the previous retreat note if it exists, and the daily notes in that quarter. Skip notes tagged example, and say so if they are all that exists.
2. Follow the substance of Prompts/04 Retreat Prep.md and Prompts/13 Trend Analysis.md: trends for dq_* and habits from the values you actually read, last quarter's intentions, and open questions. Do not invent scores.
3. Write the report with headings: 趋势, 上一次意图, 要回答的问题. Quote the person's words when you use them.
4. Stop.
```
