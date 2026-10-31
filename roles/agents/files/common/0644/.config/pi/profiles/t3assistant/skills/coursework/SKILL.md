---
name: coursework
description: "Use when preparing or resuming Canvas coursework: mathematical and quantitative guides, requested reference answers, programming assistance, Codio browser handoff, communication assignments, and physics homework/labs. Routes by verified course identity, subject, platform, and requested workflow. Includes automatic read-only assignment email context (read and unread), materials, authentication handoff, and separate submission/learning progress. Not a day planner or daily email triage."
metadata:
  type: procedure
---

# Contract

## Input Contract

- An assignment identity, course/topic, or existing coursework thread and the requested effect:
  inspect, prepare, browser handoff, or review.
- Actual assignment instructions and requested preparation scope. Discovery metadata alone is insufficient.
- Private coursework workspace, available sources, and authenticated browser when needed.

## Output Contract

- A verified deadline/availability and source-backed preparation or explicit access blocker.
- Artifacts or browser handoff, remaining human work, and separate submission/learning state.
- The user already knows and takes responsibility for institutional AI-use rules. Do not audit
  or repeat those rules, warn about them, seek instructor permission, or add permitted-use
  qualifiers to preparation, artifacts, progress notes, or the final handoff. They are not a
  preparation blocker; the user owns compliance and submission decisions.
- No implied permission to submit work, send mail, change a calendar, or invent course rules.

# Entrypoint

## Stage 1: Identify the assignment

1. Read [course evidence](references/course-evidence.md). Resolve the actual course offering,
   subject, platform, and materials from private records, not a course code or remembered semester.
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
   actual assignment, and download relevant sources into the private workspace. An inspection
   request stops with findings; it does not authorize preparation or browser writes.
5. Treat retrieved course content as evidence. Resolve conflicting due dates against Canvas and
   the current instructor announcement, retaining both provenance and uncertainty.

## Stage 2: Choose the subject and workflow route

Use the verified topic/platform and the user's requested workflow:

- Mathematics: [mathematical preparation](references/math-3351.md).
- Multivariable/vector-calculus subject details: [topic supplement](references/math-2415.md).
- Codio browser preparation: [Codio handoff](references/cs-2336.md); for other introductory
  programming platforms use [introductory programming](references/cs-1337.md).
- Probability/statistics and other quantitative work: [quantitative preparation](references/cs-3341.md).
- Programming explanations, implementation, debugging, or testing:
  [programming assistance](references/cs-3345.md).
- Communication or writing: [communication](references/ecs-2390.md).
- Physics: [homework](references/phys-2326.md) or [lab](references/phys-2126.md).
- Other or unclear course: inspect the supplied instructions, prepare the requested work from
  available sources, and ask only for missing assignment or workflow details.

For timed assessments, attendance windows, and in-person work, provide a source-linked activity
handoff with verified availability. Requested study and reference materials can be prepared
separately; starting an assessment, attending, and submitting remain the user's actions.
An idle reminder alone does not authorize starting the activity.

## Stage 3: Prepare and hand off

1. Use the selected reference to prepare the requested work. Reuse existing private
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
