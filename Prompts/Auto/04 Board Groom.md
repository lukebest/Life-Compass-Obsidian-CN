---
type: prompt
purpose: "Move stale Kanban cards one at a time. Do not rewrite card text."
schedule: "18:00"
writes: "card lines on project and writing boards"
risk: "edit"
notify: true
mode: autonomous
tags:
  - prompt
  - auto
---
Unattended job for `compass run board-groom`.

## Prompt
```
Autonomous mode is on. Do not ask questions. You may move a card by inserting the exact line under the target lane and then removing it from the source lane. Do not rewrite card text. Do not touch the %% kanban:settings block. Do not delete a card outright.

Job: groom the boards.
1. Read Meta/Compass Config.md for board_done_lanes (default Done, Published, Archive).
2. Read 04 Projects/Projects Board.md and the writing boards under 06 Writing if they exist.
3. Move a card to a done lane only when its linked note has status done or published. Leave example seed cards in place. Do not move a card just because it looks old.
4. If a linked note does not exist, leave the card. Do not create notes.
5. Stop. If nothing qualifies, do not edit the boards.
```
