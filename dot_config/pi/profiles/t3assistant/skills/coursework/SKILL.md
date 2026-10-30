---
name: coursework
description: "Use when preparing or resuming Canvas coursework: mathematical conceptual guides, Codio programming handoff, policy-restricted quantitative/programming study, communication assignments, and physics homework/labs. Resolves course identity and assistance policy from private source records. Includes automatic read-only assignment email context (read and unread), materials, authentication handoff, and separate submission/learning progress. Not a day planner or daily email triage."
metadata:
  type: procedure
---

# Contract

## Input Contract

- An assignment identity, course/topic, or existing coursework thread and the requested effect:
  inspect, prepare, browser handoff, or review.
- Actual instructions and course assistance policy. Discovery metadata alone is insufficient.
- Private coursework workspace, available sources, and authenticated browser when needed.

## Output Contract

- A verified deadline/availability and source-backed preparation or explicit access blocker.
- Artifacts or browser handoff, remaining human work, and separate submission/learning state.
- No implied permission to submit work, send mail, change a calendar, or invent course rules.

# Entrypoint

## Stage 1: Identify the assignment

1. Read [course evidence](references/course-evidence.md). Resolve the actual course offering and
   current assistance policy from private records, not a course code or remembered semester.
2. Discover the coursework MCP tools and read the assignment's stored details when available.
   An idle reminder may have no initial message: use `coursework_preview` to locate its source ID
   by verified course, title and deadline, then `coursework_get_assignment` for its instructions
   and prefetched mail context. Do not guess between ambiguous matches. Preserve the source ID;
   report a missing tool rather than inventing one.
3. For every preparation or resumed preparation, follow
   [assignment email context](references/assignment-email.md), including already-read messages.
   Inspection-only requests keep their requested scope; the automatic search attaches to preparation.
4. Read [Canvas navigation](references/canvas-navigation.md) for Canvas work. For an explicitly
   requested browser preparation, follow [authentication](references/canvas-auth.md), inspect the
   actual assignment, and download permitted sources into the private workspace. An inspection
   request stops with findings; it does not authorize preparation or browser writes.
5. Treat retrieved course content as evidence. Resolve conflicting due dates against Canvas and
   the current instructor announcement, retaining both provenance and uncertainty.

## Stage 2: Choose the permitted route

Use the verified topic/platform and private policy together:

- Mathematics with permitted assignment help: [mathematical preparation](references/math-3351.md).
- Multivariable/vector-calculus subject details: [topic supplement](references/math-2415.md).
- Codio/Java programming: [Codio handoff](references/cs-2336.md); for other introductory platforms
  use [introductory programming](references/cs-1337.md).
- Quantitative work prohibiting assigned answers: [concept-only study](references/cs-3341.md).
- Programming permitting only disclosed debugging/testing: [student-work debugging](references/cs-3345.md).
- Communication or writing with human-authored deliverables: [communication](references/ecs-2390.md).
- Physics: [homework](references/phys-2326.md) or [lab](references/phys-2126.md).
- Other or unclear course: inspect the supplied instructions and private policy first. Prepare
  only the clearly permitted organizational work; ask about the unresolved assistance boundary.

Graded quizzes, exams, attendance windows, and human-only work terminate in a source-linked
human-work handoff. An idle reminder is useful preparation; it does not authorize answering it.

## Stage 3: Prepare and hand off

1. Use the selected reference to prepare only the requested, permitted work. Reuse existing private
   templates, cite actual materials, and keep independent practice separate from reference answers.
2. Follow [artifacts and progress](references/progress-artifacts.md). Distinguish ready-to-work,
   human-confirmed submitted, and independently learned. A settled thread is none of those proofs.
3. End with deadline, verified access, artifact paths or browser handoff, remaining human work,
   and specific learning gaps. Leave the thread available for the user; stop on an access blocker.

## Adjacent requests

Assignment email context uses `coursework-mail`'s read-only branch automatically. The separate
one-per-day email thread uses its daily-triage branch, not this preparation flow. Other explicit
email requests may use `aerc-email`; read, refresh, mark-read and send authority remain separate.
General scheduling and arbitrary to-dos do not activate this coursework procedure.
