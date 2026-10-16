---
name: eval-triage
description: "Use when streaming benchmark failures into regression diagnosis,
  deduplicating root causes, or publishing a bounded set of evaluated issues."
metadata:
  type: procedure
---

# Contract

## Input Contract

- Evaluation target and revision, dataset revision, case identity and result/artifact locations.
- A working runner, reproducible environment, expected case-failure boundaries and GPU needs.
- Diagnosis scope, authorized issue actions and any requested new-issue cap.
- AgentPool capacity, selected profile, explicit role/model choices and known resource ownership.

## Output Contract

- Durable case outcomes and independently reasoned diagnoses linked to reproducible evidence.
- Deduplicated root-cause groups, verified issue receipts when authorized, and exact cap
  accounting.
- Preserved failed cases, pending work, producer cursor, counters and lease ownership for recovery.
- A concise result stating coverage, distinct confirmed defects, hosted actions and open limits.

# Entrypoint

## Stage 1: Prepare the coordinator

1. Inspect the installed `pi_subagents` API in an explicitly named persistent kernel. Import
   `AgentPool` and `Task`; retain pool, stage and submission handles. Give leaves zero delegation
   fuel. Read `PI_SUBAGENTS_MAX_CONCURRENT` and honor tighter user limits and active resource use.
   Keep inherited admission identity and reservations runtime-owned. If public construction or
   admission is unavailable, retain its original error and go to Stage 5: Drain and retain with
   worker execution blocked. Otherwise continue preparation at step 2.
2. Verify the target revision, dataset revision, dependency environment, runner entrypoint and a
   representative case once. Keep environment preparation in the coordinator so diagnosis agents
   receive ready inputs and a focused objective.
3. Define case keys from target revision, dataset revision, file identity, interpreter/model variant
   and run configuration. Record exact source URLs at immutable revisions and private log paths.
4. Inherit profile models unless the user names them or authorizes role routing. Resolve explicit
   provider/model/effort choices in the live catalog. With authorized routing, use a throughput
   model for bounded diagnosis and a strong reasoner for independent review or implementation.
   Resolve actual models and effort from the live catalog and task context.
5. Declare a finite in-flight diagnosis bound D within C and a buffered-case high-water bound H.
   Default D to available diagnosis capacity and H to 2D cases; persist larger raw output on disk.
   Default the resume threshold to H // 2 and require D >= 1 before admission. Apply backpressure
   before advancing the producer cursor; retain blocked state when capacity is unavailable.
6. Declare expected runner failures and recoverable agent cause types before launch. Default agent
   causes are `SchemaValidationError`, `PiSubagentsTimeoutError` and `PiSockSessionEnded` only
   when confined to one case with intact artifacts and shared inputs. Retain failed handles and
   continue unaffected work. Expected nonzero case exit is a case result; shared environment or
   scheduler failure is a blocker. Any additional attempt needs an explicit recovery decision;
   a dead non-dormant session does not automatically restart.
7. Establish issue authority and any supplied creation cap K. Count confirmed new creations in
   this run separately from reproductions, comments, failed writes and issue reviews. A finite K
   bounds publication; when omitted, the requested evaluation scope bounds the work. Findings stay
   local until publication is authorized.
8. Assign one coordinator writer for the ledger and hosted actions. Record root-cause reservations,
   intended actions, remote receipts and pending independent reviews. Keep a separate `created`
   counter; a supplied K is its upper bound, independently of case or diagnosis counts.
9. Implement Stages 2 through 4 as routes in one completion-driven dispatcher. Keep at most one
   pending `pool.pop()` await, alongside producer I/O. Use `asyncio.wait` with `FIRST_COMPLETED`
   when both are pending. Preserve pending awaitables across routing steps and waiting interrupts.
   Admit ready cases up to D before waiting; route results while the producer is still running.
   Go to Stage 2: Intake.

## Stage 2: Intake

1. Identify the runner's actual shared resources. GPU-backed work continues with the lease steps
   here and at step 2; independent CPU-only work proceeds directly to step 3. Acquire a GPU/model
   lease before loading a variant, using a cooperative lock and recorded process ownership. Inspect
   occupancy and defer conflicting loads. Include GPU-backed diagnosis reproductions in the same
   lease and finish their users before unloading or switching the variant.
2. Keep incompatible model variants mutually exclusive. Evaluate requested variants in alternating
   bounded batches when balanced coverage matters; record coverage and switching cost. Release a
   lease after verified unload or owned process exit, then admit the next variant.
3. Run each case with its own crash boundary and durable output. Preserve exit status, traceback,
   signal, variant, input key and artifacts. Continue after declared confined case crashes. If the
   shared environment becomes uncertain, go to Stage 5: Drain and retain; otherwise continue here.
4. Persist each case event before advancing the durable producer cursor. Record passes and filter
   diagnosis by the user's defect scope. Keep model-quality failures classified separately from
   confirmed implementation logic defects.
5. Bound admitted diagnosis handles by D and buffered cases by H. At the high-water threshold,
   pause producer admission until the buffer falls below its resume threshold. Keep output in
   durable storage and make every pending case discoverable from the cursor or ledger.
6. For a ready failure or completed diagnosis handle, go to Stage 3: Diagnose. With producer input
   still pending, continue Stage 2: Intake while servicing completion events. At producer end or
   `created == K`, go to Stage 5: Drain and retain; draining still routes admitted outcomes.

## Stage 3: Diagnose

1. Submit only newly admitted case identities. Give each agent the failing case, target source,
   observed behavior and ready environment. Ask for a root-cause hypothesis, source location,
   reproduction evidence and confidence before any issue-list search.
2. Keep initial diagnosis independent of existing issue titles and comments. After the hypothesis
   is recorded, compare the mechanism with existing issues and local accepted root-cause groups.
   Confirm by behavior and source evidence rather than wording similarity.
3. Use the dispatcher's `await pool.pop()` as the single completion-accounting path. After filling
   ready diagnosis slots, return to Stage 2: Intake while awaiting completion events. On a result,
   continue here and record its handle ID once. A cancelled or blocked case holds its dependents.
4. Catch `AgentPoolFailureError` only around the individual pop. Inspect `.result` and `__cause__`;
   recover only exact predeclared cause types with case-local containment and intact artifacts.
   Record that failed result once, block its dependencies and refill unaffected ready work.
   Unexpected causes propagate with the owned pool intact for coordinator inspection.
5. Treat `AgentPoolTimeoutError` and cell interruption as waiting interruptions. Inspect the open
   pool and handles; retain all case accounting and return to collection when ready. A quiescent
   `pop()` is complete only after the producer, buffer and publication queues are also finished.
6. Verify decisive reproduction/source evidence. Build a root-cause fingerprint from the causal
   mechanism, source location and relevant variants. Group same-cause cases while preserving all
   reproductions; keep distinct mechanisms separate even when their symptoms look alike.
7. For an accepted logic defect with authorized publication and remaining budget, go to
   Stage 4: Publish. Otherwise record its state and return to Stage 2: Intake while work remains;
   when admission has stopped, return to Stage 5: Drain and retain.

## Stage 4: Publish

1. Serialize issue decisions in the coordinator, or admit exactly one publisher handle at a time.
   AgentPool stage slots are soft priorities; a one-slot stage does not enforce a mutex. Use the
   repository's cooperative publication lock when multiple participating coordinators may write.
2. Reserve the accepted fingerprint and recheck the remaining confirmed-creation budget under the
   same writer ownership. Refresh remote open issues and relevant comments immediately before
   publication, then compare their actual causes with the independently established diagnosis.
3. For an existing matching issue, add only new reproduction evidence in the exact comment format
   requested by the user. Check for the same case URL/comment first. If already present, record
   its receipt. Both branches finish publication accounting at step 6.
4. For a genuinely new root cause with budget, persist a create intent and content digest, then
   publish a concise issue: observable defect, minimal reproduction, expected versus actual
   behavior and source-backed cause. Include relevant versions and dataset/source links accessible
   to the issue readers.
   On confirmed creation record its remote ID/URL and increment `created` exactly once.
5. For an uncertain network outcome, retain the intent and reconcile remote state before another
   write. A confirmed failed write consumes no creation slot. If a concurrent external writer
   published the same cause, link that issue and finish at step 6 instead of creating another.
6. Record the receipt and release the reservation. Keep issue prose for repository readers;
   private machine paths, session details and workflow bookkeeping stay in the private ledger.
7. When independent issue review is requested, immediately submit one read-only review for each
   confirmed creation and keep polling completions alongside intake. Review checks causal validity
   and issue quality; issue comments use the user's requested brevity and action authority.
8. Admit implementation only when the user requested it, with accepted issue identities and
   separate owned worktrees. Issue creation alone authorizes diagnosis delivery, not source repair.
9. At `created == K`, stop new diagnoses and producer admission, preserve buffered case identities
   and go to Stage 5: Drain and retain. With remaining budget and producer input, return to
   Stage 2: Intake; when admission has stopped, return to Stage 5: Drain and retain.

## Stage 5: Drain and retain

1. On cap, producer end or a blocker, stop admitting affected work. Let active owned case processes
   settle or use the runner's supported graceful stop. Keep draining existing diagnosis and review
   outcomes while enforcing the same publication cap and source authority. At normal producer
   completion, admit persisted buffered cases up to D while budget remains; at cap or a shared
   blocker preserve unadmitted cases instead. Route eligible outcomes through Stage 3: Diagnose
   and Stage 4: Publish, returning here after each route.
2. Persist case cursor, coverage by variant, queued/buffered identities, processed handles, accepted
   fingerprints, unresolved hypotheses, publication intents/receipts and resource ownership.
3. Reconcile uncertain hosted writes before resuming. Inspect live kernel/pool/handle state against
   the ledger before resubmitting any task. Continue retained sessions through
   `stage.submit(task, parent=result, session_handle=result.handle)` and retain the new handle.
4. Release owned GPU/model leases after actual unload or process exit. Keep uncertain resources
   marked blocked until ownership is known. Preserve unrelated workloads and their leases.
5. If follow-up, active work or recovery remains, retain the kernel, open pool and sessions and
   report the next action. Otherwise close only this owned pool after all outcomes are accounted.
6. Report cases evaluated, variant coverage, passes/failures/crashes, distinct confirmed causes,
   confirmed creations against K, existing-issue reproductions, pending reviews and blockers.
