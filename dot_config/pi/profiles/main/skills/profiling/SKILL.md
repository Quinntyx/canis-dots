---
name: profiling
description: "Use when investigating slowness, input lag, throughput, CPU or GPU use,
  memory growth, latency, frame time, or measured performance regressions."
metadata:
  type: procedure
---

# Contract

## Input Contract

- A reported symptom, project or process, editing authority, and a reproducible workload.
- A task-local artifact directory and the available profiler or runtime instrumentation.
- Permission for workload side effects and a resource envelope compatible with active desktop work.
- Acceptance targets from the user or project; otherwise establish a baseline without inventing one.

## Output Contract

- Reproducible baseline measurements and raw traces, with workload, environment, and version data.
- CPU, GPU, memory, and latency findings classified as measured, inapplicable, or unavailable.
- A ranked bottleneck explanation tied to captures, plus a verified improvement when requested.
- `performance-report.md` with commands, artifacts, distributions, limits, and remaining decisions.
- Measurements protect active user workflows and distinguish instrumentation cost from app cost.

# Entrypoint

## Stage 1: Define and preflight

1. Resolve the user-visible operation, data size, execution path, runtime, revision, build mode,
   and metric boundaries. Define start and completion events with a monotonic clock.
2. Establish a reproducible fixture. For long-history UI lag, use a local deterministic provider
   or replay with recorded content size, avoiding paid model traffic as the benchmark driver.
3. Inspect current load and available binaries using executable lookup and bounded version queries.
   Record CPU/GPU hardware, active backend, power mode, profiler availability, and capture rights.
4. Select only relevant capture modes from Capture selection. Where a tool is absent, record the
   missing path and use available runtime instrumentation. Treat unavailable evidence as a limit.
5. Choose bounded workload size, repetitions, threads, and GPU allocation that preserve interactive
   use. Keep existing servers and unrelated jobs running unless their owner authorizes a change.
6. If a safe reproducible workload is available, proceed to Stage 2: Baseline. Otherwise proceed to
   Stage 5: Report with the blocking input or capability identified.

## Stage 2: Baseline

1. Record exact command vectors, inputs, environment changes, build flags, hardware, and revision.
   Separate cold startup, warm steady state, and cache state instead of mixing their timings.
2. Resolve the skill root. Run `bin/profile-run` with `--out` set to a fresh artifact directory,
   optional `--label`, optional positive `--repeat`, and `--` followed by the command vector.
   This Linux/Python 3 standard-library helper records wall time, waited child-tree CPU time,
   child peak RSS, exit status, per-run stdout/stderr, and successful-run summary statistics.
   It creates only its output directory.
3. The helper runs sequentially and returns 1 if any command fails, 2 for setup failure, or 130
   for interruption. It adds no workload deadline. Run long captures in an owned background job;
   preserve its handle and wait for the real process result.
4. Capture uninstrumented timings separately from diagnostic traces. Record warmups and each raw
   repetition; report median and spread. Use tail percentiles only with sufficient observations,
   disclose sample count, and separate failed or cancelled runs from successful timing samples.
5. Capture operation-level latency in the application or test harness. Process duration is not
   keystroke latency, frame time, time to first token, or time to first usable result.
6. Proceed to Stage 3: Diagnose.

## Stage 3: Diagnose

1. Collect the smallest CPU, GPU, allocation, or scheduling trace that can distinguish the leading
   hypotheses. Correlate timeline events with the slow user operation and preserve the raw file.
2. Confirm the actual compute device with runtime placement and observed activity. Separate CPU
   preparation, transfer, GPU kernels, synchronization, and idle wait; label fallback explicitly.
3. For memory, compare repeated equal workloads and retained allocations after equivalent cleanup.
   Distinguish process RSS, managed heap, native allocations, and device memory. A high-water mark
   alone establishes a peak, while sustained retained growth requires separate evidence.
4. Rank observed hot stacks, blocking spans, allocation sites, and device stalls by contribution.
   Identify the causal path and measurement gaps rather than inferring causes from aggregate load.
5. If a fix was authorized and the evidence supports one, proceed to Stage 4: Change and compare.
   Otherwise proceed to Stage 5: Report with the measured diagnosis and proposed next action.

## Stage 4: Change and compare

1. Make the smallest causally supported change. Preserve behavior, visual identity, shader output,
   and workload fidelity; compare screenshots where rendering behavior could change.
2. Re-run the same fixture and capture settings on the changed revision. Alternate baseline and
   candidate runs when practical to reduce drift; record changed conditions and profiler overhead.
3. Compute absolute and relative deltas from successful comparable runs. Run relevant correctness
   checks and inspect whether cost moved to another resource or a worse tail.
4. If evidence supports an improvement without a required-behavior regression, proceed to Stage 5.
   Otherwise revise the hypothesis and return to Stage 3, preserving the unsuccessful result.

## Stage 5: Report

1. Load raw capture records in Python and compute the exact values, units, ratios, and tables
   used in the report. Use the capture's `summary` fields when present. Keep derived data and
   diagnostic experiment scripts beside the raw artifacts, with each row tied to its source.
2. Write `performance-report.md` with the symptom, fixture, revision, commands, hardware, profiler
   settings, raw artifact links, sample counts, timing distributions, and measured resource costs.
3. State CPU, GPU, memory, and latency coverage individually. Explain unavailable or inapplicable
   captures and distinguish observation, supported inference, and an untested hypothesis.
4. Report the outcome first, then evidence-backed bottlenecks, before/after deltas, correctness
   checks, changed paths, and remaining limits. Retain captures in the task artifact directory.

# Capture selection

- Browser or Electron UI: discover existing DevTools tools and inspect their schemas; record the
  Performance timeline with relevant screenshots, interactions, main-thread work, frames, and GPU
  tracks. Save the trace and correlate input events with the next visible update.
- JavaScript CPU: invoke Node with `--cpu-prof` and an explicit `--cpu-prof-dir` before the entry
  script. Inspect the emitted `.cpuprofile` by total and self cost; capture event-loop delay when
  responsiveness is the symptom. Keep startup and steady-state windows identified.
- Python CPU: run the selected interpreter with `-m cProfile -o` and the artifact path before the
  script. Read via `pstats`; distinguish call counts, cumulative time, self time, and native work.
- Native or mixed CPU: use installed `perf record` with call stacks for a controlled reproduction.
  Check access first; record permissions as a limitation and use available runtime profiles when
  kernel sampling is unavailable. System settings remain under the user's control.
- Managed memory: use an existing heap snapshot facility or Python `tracemalloc` snapshot deltas.
  Keep snapshots private, since captured objects may contain user data. Capture native or RSS
  growth separately; `tracemalloc` does not establish device or all native allocation costs.
- GPU: use available vendor telemetry for utilization and device memory over time. Use installed
  Nsight Systems, ROCm, graphics debugger, or browser GPU traces for kernel and queue evidence.
  Verify supported flags from that tool's help. Utilization samples establish activity, not the
  duration or cause of individual kernels; synchronize timed GPU work at the chosen boundaries.
- Latency: retain per-operation monotonic durations and input size, queue state, warmup state, and
  completion definition. Analyze distributions in Python and plot when shape or outliers matter.
