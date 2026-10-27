---
name: project-plan
description: "Use when making or revising a software project plan, architecture, implementation
  roadmap, ARCHITECTURE.md, or PLAN.md; for agent operating guidance use agent-repo-guidance."
metadata:
  type: procedure
---

# Contract

## Input Contract

- The project or change being planned, intended outcome, and supplied discussion or specification.
- Existing project documents, implementation, interfaces, constraints, and delivery instructions.
- Authority to write planning artifacts; implementation and publication follow the actual request.
- The working project context and any explicit document destinations or naming conventions.

## Output Contract

- A grounded target, explicit architectural decisions, and a dependency-ordered executable plan.
- Requirements/design and execution state in their established documents, normally ARCHITECTURE.md
  and PLAN.md. Update AGENTS.md only when durable agent operating guidance actually changes.
- Consistent distinctions between observed implementation, intended target, decisions, and open
  work.
- A readable summary of the proposed system, important tradeoffs, next milestone, and real
  blockers.
- Checked document paths and references, with substantive uncertainties retained explicitly.

# Entrypoint

## Stage 1: Establish the planning scope

1. Resolve the project and requested result from context. Distinguish project direction from a
   bounded change plan. Read existing planning and repository guidance before choosing files.
2. A project-level direction request uses the three document roles in Document ownership. Existing
   equivalents keep their established names and roles. A bounded change uses the relevant existing
   plan or a scoped plan artifact; retain established project-wide direction unless it changes.
3. A supplied project path owns its documents. Otherwise use the current project context. When
   neither identifies a destination, ask only for the missing project or desired artifact location
   and resume Stage 1 when resolved. With the destination known, continue at step 4.
4. Extract the outcome, acceptance criteria, constraints, existing decisions, and unresolved
   choices.
   Interpret a request for a plan as planning authority. Additional implementation, repository
   creation, publishing, or deployment follows explicit task authority.
5. If a missing decision would materially change the target, authority, or irreversible
   architecture,
   go to Stage 2: Resolve consequential uncertainty. Otherwise record reversible assumptions and
   proceed to Stage 3: Ground the design.

## Stage 2: Resolve consequential uncertainty

1. Inspect available project evidence for the unresolved decision before asking the user.
2. With enough evidence or authorized design discretion, select an option and record its
   rationale,
   uncertainty, and what would falsify it. Continue to Stage 3: Ground the design.
3. When user input is essential, ask focused questions with meaningful alternatives and a
   recommendation. On an answer, return to Stage 1: Establish the planning scope. While blocked,
   complete independent planning sections and go to Stage 6: Deliver with the open decision named.

## Stage 3: Ground the design

1. Read relevant source boundaries, public and internal interfaces, data/state ownership, build
   and
   test entrypoints, dependencies, and deployment or execution constraints.
2. Run proportionate read-only discovery and baseline checks. Record actual commands and results;
   label an unexecuted or unavailable check as pending rather than using it as evidence.
   Bind dated baseline and status entries to the current task timestamp or an observed clock.
3. Reconcile the supplied discussion with observed code and documentation. Mark existing behavior
   separately from the desired target and identify the migration between them.
4. Identify the consequential alternatives, coupling, invariants, failure modes, resource needs,
   compatibility obligations, and verification surfaces. Research uncertain external contracts
   through their authoritative sources when those choices affect the design.
5. Choose the smallest architecture that reaches the target. State why the selected boundaries and
   tradeoffs fit the constraints; retain meaningful unresolved alternatives and decision owners.
6. Proceed to Stage 4: Write coherent documents.

## Stage 4: Write coherent documents

1. Update existing documents in place, preserving relevant human decisions and project vocabulary.
   Use the document roles below to give each kind of information one clear owner.
2. Write the architecture as a coherent system: responsibilities, boundaries, dependency
   direction,
   interfaces, state/data flows, failure handling, resource assumptions, and integration points.
   Distinguish the observed system from target decisions and explain the transition.
3. Keep target product requirements and acceptance criteria in an established specification, or
   ARCHITECTURE.md when no separate specification is warranted. AGENTS.md contains only durable
   operating instructions and conditional pointers. If those instructions change, use
   `../agent-repo-guidance/SKILL.md`; otherwise leave AGENTS.md alone.
4. Write PLAN.md as ordered milestones with deliverables, prerequisite edges, relevant interfaces,
   acceptance checks, integration points, and meaningful completion conditions. Bind known paths
   and commands to the actual project; label proposed artifacts as proposed.
5. Split work at cohesive outcomes. Parallel work requires independent inputs and distinct
   ownership;
   serialize changes sharing an interface or integration resource. Keep the plan independent of a
   particular agent runtime; delegation architecture is an optional execution concern.
6. Record current progress, blockers, pending decisions, and the next executable action in the
   plan.
   Use observed evidence for completion and task-supplied dates for schedule constraints.
7. Place verification in each milestone and include an end-to-end acceptance path for the
   requested
   target. Distinguish implementation, integration, runtime behavior, and delivery checks as
   needed.
8. Proceed to Stage 5: Check the plan.

## Stage 5: Check the plan

1. Read the document set together. Check that target requirements, architecture decisions, and
   milestone acceptance agree, and that every required outcome has an implementation path.
2. Resolve stale or contradictory statements. Keep status and changing tasks in PLAN.md; reference
   durable definitions from their owning document rather than copying diverging descriptions.
3. Check referenced paths, symbols, commands, links, dependencies, and named capabilities against
   the repository and authoritative sources. Retain proposed items and unavailable checks with
   their explicit status; existing commands must be grounded in actual configuration.
4. Check milestone order, interface handoffs, ownership, migration sequence, and the final
   verification
   path. Record a real prerequisite instead of silently inventing available infrastructure.
5. For consequential unresolved defects, return to Stage 3: Ground the design. With a coherent
   executable plan, proceed to Stage 6: Deliver.

## Stage 6: Deliver

1. Summarize the system and chosen direction for a human reader, followed by the key tradeoffs,
   document paths, next milestone, and any decision or prerequisite still blocking execution.
2. A planning-only request finishes with the checked documents and summary. A request also
   authorizing implementation proceeds from the first ready milestone under its existing
   authority.
3. Requested commits or publication follow the repository's task scope. Report planning validation
   separately from implementation, tests, or runtime behavior that has yet to occur.

# Document ownership

- An existing SPEC.md, requirements document, or equivalent owns product behavior and acceptance.
  Without a separate specification, ARCHITECTURE.md owns concise target requirements alongside
  system design, decisions, rationale, interfaces, invariants, and current-versus-target distinctions.
- AGENTS.md owns durable engineering conventions, safety boundaries, actual verification commands,
  and conditional pointers to project knowledge. Product scope and transient plans live elsewhere.
- PLAN.md owns high-churn execution state: milestones, dependencies, progress, blockers, pending
  checks, handoffs, and next actions. Milestone checks reference requirements/design rather than
  maintaining a second competing specification.
- Established project documents can fulfill these roles under different names. Preserve their
  conventions while keeping the roles distinct and references consistent.
- A bounded plan may remain one artifact; the three-role distinction still separates facts,
  decisions, and execution state within the requested scope.

# Source basis

- Claude Code's explore-plan-implement-verify workflow informs the phase ordering.
- https://code.claude.com/docs/en/best-practices
- https://code.claude.com/docs/en/memory
