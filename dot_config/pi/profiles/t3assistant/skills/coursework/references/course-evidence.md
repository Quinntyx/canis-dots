# Resolve private course evidence

Course codes are routing hints, not enrollment facts. These references cover reusable subject
and platform procedures; they do not establish which courses the user takes or their current work.

1. Prefer the assignment details returned by the coursework MCP service. Its local configuration
   maps verified course IDs/aliases to subject, platform, workflow, and source-material paths.
2. On the authoritative desktop, deployment-specific source configuration lives privately at
   `~/.local/state/t3assistant/config.private.json`; historical evidence, when needed, is at
   `~/.local/state/t3assistant/course-evidence.private.md`. Use only the relevant course fields.
   On another host, retrieve the configured record through the service rather than assuming paths.
3. Confirm offering, semester, assignment category, platform, and requested deliverables from
   current assignment details. Consult the syllabus for missing course facts, not as a prerequisite
   to preparing the requested work. A stale course title proves none of these facts.
4. Compare Canvas instructions with the record. Keep due dates, unlock/lock times, submission
   evidence, grades, and learning gaps distinct. A missing iCal event is not cancellation.
5. Route preparation by the actual subject, platform, and user workflow. With missing or conflicting
   assignment facts, retain the uncertainty, continue work supported by available sources, and
   identify the exact identity, material, deadline, or access question for the user.

Keep personal enrollment, prior assignment IDs, deadlines, feedback, and course-material inventories
in the private workspace/state. Public procedures and examples use placeholders only.
