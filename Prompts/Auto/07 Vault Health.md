---
type: prompt
purpose: "Write a structural health report under Agent/Reports. Do not fix anything."
schedule: "Sun 19:00"
writes: "a new file in Agent/Reports"
risk: "read-only"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run vault-health`.

## Prompt
```
Autonomous mode is on. Do not ask questions. The only file you may create is Agent/Reports/<target-date>-health.md. Do not edit, move, or delete anything else.

Job: vault health check, same checks as Prompts/15 Vault Health Check.md.
1. List notes tagged example.
2. Flag an empty birthdate, template text still in Life Theme or Core Values, example: true on Ideal Week, and the Setup task if it is still open.
3. List wikilink targets that do not resolve. Date-shaped links (YYYY-MM-DD, gggg-Www, YYYY-QN) that are not created yet are expected: list them apart from broken links.
4. Write the report in three short sections. Do not fix the findings. Stop.
```
