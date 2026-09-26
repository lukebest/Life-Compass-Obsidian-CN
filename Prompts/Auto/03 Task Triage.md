---
type: prompt
purpose: "Route open inbox tasks that have no project, person, or due date."
schedule: "every 3h 09:00-21:00"
writes: "task lines in 08 Tasks/Tasks.md"
risk: "edit"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run triage`. Same routing rules as Prompts/06 Task Triage.md, without the approval wait.

## Prompt
```
Autonomous mode is on. Do not ask questions. You may rewrite task lines in 08 Tasks/Tasks.md. You may move a line to ## Someday only by adding that same line there and then removing it under ## Inbox. Do not delete any other line. Do not invent a project or a person.

Job: triage the inbox.
1. Read 08 Tasks/Tasks.md. Collect every open task under ## Inbox that has no #project/ tag, no #p/ tag, and no 📅 date. Skip lines that contain 🧭capture: (those belong to capture routing).
2. Read 04 Projects and 05 People. Slug = title lowercased, non-alphanumerics to -. Ignore notes tagged example.
3. For each collected line, apply exactly one change: add #project/<slug>, add #p/<slug> (and #discuss if it is something to talk about), add 📅 only when the text names a real date, move the line to ## Someday, or leave it. Keep ➕ and every emoji already on the line.
4. If none of the real projects or people fit, leave the line or move it to Someday. Do not create a project note.
5. Stop after the edits. If there was nothing to route, do not edit the file.
```
