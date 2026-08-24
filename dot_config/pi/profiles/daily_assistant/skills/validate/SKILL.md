---
name: validate
description: Sanity-check the user's Taskwarrior task list against the actual upcoming coursework deadlines — confirm every deliverable has a matching task with the right due date and enough scheduled work to finish before the real deadlines. Use when the user asks to validate, verify, or sanity-check their schedule/plan.
---

# Validate Taskwarrior against real deadlines

Verify that the user's Taskwarrior to-do list will actually get everything
done before the real course deadlines. This requires two inputs: **current
coursework facts** and **the task list**. Do not trust memory for either.

## 1. Get current coursework facts

If a fresh scrape already happened in this conversation (e.g. the user just
ran `/skill:daily`), reuse it. Otherwise, run the same scraping procedure as
`/skill:daily` (sections 1–6: load active courses, read syllabi, scrape
sources, recover from failures, build the evidence list). Getting this wrong
makes validation meaningless, so do not skip it.

## 2. Export the task list

Run `task status:pending export` (or `task export status:pending`) — this
emits one JSON object per line. Parse it (`jq -s` or python) rather than
parsing the human `task list` output. Fields you will need: `description`,
`due`, `scheduled`, `wait`, `tags`, `project`, `annotations`, `status`,
`end`, `depends`.

## 3. Match deliverables to tasks

For each scraped deliverable, find its task(s) by course name, project name,
tags, description keywords, and dates. A deliverable usually maps to:

- a **deliverable task**: the "submit X" task with `due:` = the real deadline;
- zero or more **work-block tasks**: tasks with `scheduled:` set to the day the
  user intends to work (often tagged `+workblock`).

If a mapping is ambiguous (e.g. two tasks could match "Project 2"), ask the
user which is which instead of guessing.

## 4. Checks

Run these checks and record pass/fail per deliverable:

1. **Coverage** — every scraped deliverable has a corresponding pending task;
   conversely, flag pending tasks whose course is not registered or is
   completed/dropped (they may be stale).
2. **Due date match** — the task's `due` matches the scraped deadline. Flag
   mismatches; if a Blackboard/syllabus deadline changed, the task is stale.
3. **Work is scheduled before the deadline** — every deliverable task with an
   upcoming due date has at least one work-block task with `scheduled` before
   `due`. No work-block is scheduled after its `due`.
4. **Sufficiency** — for large projects and exams, is there enough scheduled
   work? Sum scheduled work blocks vs. the project's implied size (from the
   syllabus/assignments). If estimates are absent, say the check is
   qualitative, not conclusive.
5. **Distribution** — no single day is overloaded; large projects are not
   deferred to the last day; exam prep exists ahead of each exam.
6. **Readiness** — tasks with `wait` set should become visible in time; tasks
   that are `scheduled` far out but due soon are at risk.
7. **Overdue** — any pending task already past its `due`.

## 5. Report

One compact section per deliverable:

```
CS 4337 — Project 2  (due 2026-04-12 11:59 PM CDT)
  task "Submit Project 2" due 2026-04-12           ✓ match
  work blocks: 04-05 (2h), 04-08 (3h)              ✓ before due
  remaining estimate ~3h, no block after 04-08     ⚠ tight — consider a block
```

Then a short overall verdict: **plan is sound** / **at risk** / **will miss X**
with the top 3 concrete fixes. If any check could not be evaluated (no
estimates, ambiguous mapping, unscraped source), say so explicitly — never
claim the plan is sufficient when the data isn't there.
