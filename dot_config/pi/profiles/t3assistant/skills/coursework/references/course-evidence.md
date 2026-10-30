# Resolve private course evidence

Course codes are routing hints, not enrollment facts. These references cover reusable subject
and platform procedures; they do not establish which courses the user takes or their current rules.

1. Prefer the assignment details returned by the coursework MCP service. Its local configuration
   maps verified course IDs/aliases to topic, assistance policy, and source-material paths.
2. On the authoritative desktop, deployment-specific source configuration lives privately at
   `~/.local/state/t3assistant/config.private.json`; historical evidence, when needed, is at
   `~/.local/state/t3assistant/course-evidence.private.md`. Use only the relevant course fields.
   On another host, retrieve the configured record through the service rather than assuming paths.
3. Open the relevant current syllabus/instructor policy. Confirm offering, semester, assignment
   category, permitted assistance, and disclosure requirements. A stale course title proves none.
4. Compare Canvas instructions with the record. Keep due dates, unlock/lock times, submission
   evidence, grades, and learning gaps distinct. A missing iCal event is not cancellation.
5. Carry the effective policy into preparation. With missing or conflicting evidence, prepare the
   organizational handoff and identify the exact policy/access question for the user.

Keep personal enrollment, prior assignment IDs, deadlines, feedback, and course-material inventories
in the private workspace/state. Public procedures and examples use placeholders only.
