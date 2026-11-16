# Calibration tables

Measured from about 2,000 agent requests and 256 root tasks run through T3 Code between
2026-10-27 and 2026-11-13. All times are active time. Cells read `median [p25–p75]`.

Contents: 1 Models · 2 Turns · 3 Delegated briefs · 4 Whole tasks · 5 Slow commands ·
6 Delegation · 7 Uncertainty

## 1. Models: seconds per step and step count

A step is one tool call. Seconds per step is the model's own thinking and generation time divided
by its tool calls, so it already covers the messages and replies written along the way. It
excludes the time the tools themselves run.

| Model (usual effort) | s/step | Steps taken vs Opus, top-level turns of the same kind |
|---|---|---|
| Claude Opus 5.5 (high) | 8.5 [6.0–11.9] | 1.0× (baseline) |
| Claude Opus 5.5 (xhigh) | 5.8 [4.6–7.3] | ~1.5–2× (it chooses to verify more) |
| GPT 6.1 Sol (xhigh) | 10.3 [8.1–15.0] | ~1.1× reading and investigation; ~1.3–1.6× edits without a build; ~0.8–1.4× with a build gate |
| GPT 6.1 Sol (high) | 7.2 [5.5–13.9] | as above |
| DeepSeek v4.1 flash (max) | 6.5 [5.0–9.2] | ~2–3× on investigation, many-edit and orchestrating turns; ~1.1× on small edits and build turns |
| Crouton alpha (max) | 7.6 [5.2–11.5] | about half of DeepSeek's steps on identical briefs |
| GLM 5.3 flash | 8–11 | ~1.3×, erratic |
| Muse Ember (max) | 3.4 [2.8–3.6] | ~2× |
| Claude Fable 5.2 (high) | use the Opus 5.5 cells (see below) | ~1× or fewer |

Why they differ:

- **Opus 5.5** batches work into few, well-aimed tool calls and writes long replies between them,
  which is why its time per tool call is high while its turns are short.
- **Sol 6.1** carries a hidden reasoning pause on every step, and long runs slow further as
  context grows (about 5 s × steps²/1000 extra: +1 min at 100 steps, +8 min at 300). It reads and
  verifies more before editing, so an edit without a build takes about twice Opus's time; once a
  build gate dominates, the two converge. Writing large files costs it about 12 s per 1,000
  characters.
- **DeepSeek v4.1 flash** has quick steps but, on open-ended work, takes two to three times as
  many, re-reading and editing in small increments with very long reasoning (~2,300 characters
  per step). On the same writing brief it took 207 steps where Crouton took 80.
- **Crouton alpha** reasons tersely and takes few steps; across identical briefs it finished in
  about 0.6× DeepSeek's time.
- **GLM 5.3 flash** has the widest spread; widen the range by half again.
- **Muse Ember** has the fastest steps measured.
- **Fable 5.2** has no cells of its own in the tables below. It generates at Opus 5.5's token
  speed (about 30% faster than Fable 5.1) and spends fewer tokens on the same work, so take the
  Opus 5.5 cell as its figure and lean toward the lower half of the range. This rests on the
  owner's note of 2026-11-15, not on measured runs; the few early samples read about 16 s per
  step and are too thin to scale from.

## 2. Turns (one message to one reply)

Common single turns sent by a person, by model, minutes. Use these first when one fits:

| Turn | Opus 5.5 | Sol 6.1 | DeepSeek |
|---|---|---|---|
| Question opening a thread (explain, why, how does) | 1.5 [0.9–1.9] | 2.3 [1.6–3.3] | 2.4 [2.1–8] |
| Question as a follow-up | 0.9 [0.4–3] | 1.4 [0.6–3.9] | 0.5 [0.3–0.9] |
| Lookup or operation with no file edits, opening a thread | 2.8 [1.6–4.1] | 2.2 [1.0–3.3] | 3.3 [0.4–4.3] |
| Same as a follow-up | 1.1 [0.4–2.4] | 1.1 [0.6–2.3] | 0.5 [0.3–2.7] |
| Small edit or config change, no build | 3.3 [1.9–4.8] | 5.4 [2.1–6.7] | 4.8 [3.8–7.3] |

Answering a question about one named thing (a file, a skill, a setting) is a handful of reads and
a reply, so it sits at these medians even when the subject is large.

Turn shapes across all models, for anything the table above does not cover:

| Shape | Steps | Slow-command time | Active time |
|---|---|---|---|
| A. Answer from context, no tools | 0 | 0 | 18 s [12–49 s]; Sol ~30 s, Opus ~12 s |
| B. Quick lookup, 1–8 tools, no edits | 3 [2–5] | 0 | 50 s [27–84 s] |
| C. Investigation, no edits | 18 [12–30] | 8 s [1–45] | 3.3 min [2–6] |
| D1. Small edit (1–5 edits), no build | 17 [9–26] | 12 s | 3.9 min [1.5–6] |
| D2. Many edits, no build | 61 [29–91] | 1.3 min | 18 min [9–27] |
| D3. Small edit plus build or test | 54 [31–95] | 3 min [1.7–8] | 13 min [8–21] |
| D4. Many edits plus build or test | 127 [84–174] | 5.5 min [2–19] | 33 min [19–55] |
| E. Orchestrating delegates | 104 [50–214] | 3.6 min [1–9] | 25 min [10–57] |

Shape by model, median active time (median steps), pooled over top-level turns and delegated
briefs. These already include how many steps each model takes:

| Shape | Sol 6.1 | Opus 5.5 | DeepSeek | Crouton |
|---|---|---|---|---|
| C | 3.4 min (22) | 3.1 min (16) | 6 min (36) | 4.2 min (25) |
| D1 | 5.5 min (19) top-level; 10.8 min (47) delegated | 3 min (15) | 3.1 min (17) | 1.7 min (10), delegated |
| D2 | 18 min (78) | 9 min (30) | 11 min (95) | 6.5 min (54) |
| D3 | 13 min (76) | 12 min (56) | 20 min (63) | — |
| D4 | 32 min (161) | 33 min (148) | 27 min (162) | 22 min (91) |
| E | 35 min (159) | 14 min (59) | 67 min (190) | — |

These cells are medians only. For a cell's likely range keep the all-model row's proportions
around the cell's own median: p25 is about 0.4–0.6× the median and p75 about 1.5–2.3×.

A short follow-up message (60 characters or fewer) turns out to be A or B 48% of the time, C or
D1 31%, something larger 21%. A short "go ahead", "fix it" or "PR it" inherits the size of
whatever the thread just agreed to do: "PR it" alone is 2.3 min [1–11]; an instruction to carry
the whole change through unattended to a ready PR is 41 min [18–72] in one turn. An attached
screenshot of a UI problem runs 11 min [5–25].

## 3. Delegated briefs (one child turn)

Minutes, with median steps in parentheses.

| Brief | Sol 6.1 (high effort) | Opus 5.5 | DeepSeek | Crouton |
|---|---|---|---|---|
| Code review, final / acceptance / recheck | 3.7 [2.6–6.0] (42) | 8.6 [6.6–14] (57), few samples | 8.2 [7–13] (87) | 3.4 [3.1–3.9] (48) |
| Code review, first round | 5.9 [4.4–8.3] (55) | 14 [5–21], few samples, as low as 4 | 8 [7–11] (79) | 7.8 [4–11] (50) |
| Rubric or screenshot judgment | 2.5 [2–2.9] (12) | 2.0 [1.9–2.5] | 8.8 [3.4–12] (75) | 3.1 [1.1–7] (23) |
| Research, read-only report | 11.5 [8.7–16] (47) | — | 10.4 [6.8–16] (99), few samples | — |
| Implementation | 34 [25–63] (171) | 14 [11–20] (42) | 18 [10–20] (172) | 11 [6–15] (66) |

The Sol review cells are at high effort. At xhigh or max a Sol code review runs about 14 min in
either round (final 13.7 [11–15], first round 14.1 [10–17.6]); use that figure for those efforts.
Sol research briefs in the table were mostly at xhigh.

A review that also runs the tests roughly doubles: 10 min [4–12.5] for Sol. A brief that says
adversarial, exhaustive or deep sits at or above p75. Review time depends only weakly on diff
size, because reviewers read selectively: a 700-line diff does not take seven times a 100-line
one. A document review that must reproduce evidence (rerun cases, check sources) sits at
12–23 min for DeepSeek. Implementation children that run a build gate sit at the top of their
range. A single image read or transcription by a child is under a minute.

## 4. Whole tasks (first prompt to settled)

Whether the lead delegates is the largest single driver. Merged-PR tasks, minutes of active time:

| Lead model | Works alone | Launches child agents | When it delegates |
|---|---|---|---|
| Opus 5.5 | 20 [8–41]; first turn 6 [3–18] | 113 [67–450], rare | 3% of plain requests; 22% when told to carry the task through unattended |
| Sol 6.1 | 18 [16–29]; first turn 9 [3–13] | 76 [51–136] | about 13% of plain requests; every time some prompt told it to carry the task through unattended |
| DeepSeek v4.1 flash | 49 [11–84]; first turn 36 [11–59] | 122 [91–206] | 21% of plain requests; 78% unattended |

Decide delegation first. An instruction to carry the task through unattended to a ready or merged
PR, in the first prompt or a later one, brings reviewers and, for Sol and DeepSeek, implementation
children, however small the fix. Without that instruction use the solo row; change size and file
count did not predict delegation.

A lead working alone, by size of the final diff (added plus deleted lines, tests included):

| Changed lines | Opus 5.5 | Sol 6.1 | DeepSeek |
|---|---|---|---|
| under 100 | 6 [5–8] | 16 [9–28] | 27 [10–49] |
| 100–400 | 30 [16–45] | 17 [17–18], few samples | about 70 |
| 400–1,500 | 33 [19–41] | 29 [25–38] | 110 [91–220] |
| over 1,500 | 42 [25–115] | — | — |

The step from under 100 lines to over 100 is the big one. One affordance that reuses existing
machinery (a button, a menu entry, a styling rule, a guard) with its test stays under 100 lines.
A behaviour that needs new state, a new data path or parity across two client surfaces crosses
it. A new capability with server, contracts and UI is 1,500–3,000 lines.

Other reference points, for cross-checking the row chosen above:

| Task | Active time | Notes |
|---|---|---|
| All merged-PR tasks | 38 [17–76], p90 2.6 h | ~185 steps [98–317] across the thread and its delegates |
| Carried through unattended from one prompt | 67 [41–121] | review, PR and CI repair are all inside the first turn |
| Ordinary interactive | 30 [15–67] | first turn 7 [3–22], then follow-ups |
| First prompt over 800 characters (a full spec) | 110 [42–240] | diffs in the thousands of lines |
| No PR, question-like first prompt | 7 [2–14] | |
| No PR, other | 12.5 [3–43] | |

These whole-task figures already include the usual follow-up prompts: 1 [0–3] of them at 2.9 min
[0.9–12] each (a third of merged tasks needed none), about 4 once the diff passes 800 lines. A
task that will plainly need more (a visual result judged by eye, a vague goal refined in
conversation) sits at p75 or above; six or more prompts ran 73 min [40–220].

Where the tables above have a cell for the lead model and size, use the cell. Only for a lead
model or size with no cell, use a rule fitted across all merged-PR tasks:
`minutes ≈ 3.6 × lines^0.28 × model × delegation`, with model 1.0 for Opus, 1.6 for Sol and 2.6
for DeepSeek, and delegation 2.7 when the lead launches children. Ten times the lines is about
twice the time. Example with no cell: a Sol lead working alone on 3,000 lines is
3.6 × 3000^0.28 × 1.6 ≈ 54 min.

Clock time is much longer than active time. From prompt to merge the median was about 4.5 h
[0.8–13] (Opus-led about 1 h, Sol and DeepSeek 7–10 h). A watched PR's check verdict arrived a
median of about 70 min after the watch was set; quota pauses and waiting for the next prompt add
the rest.

## 5. Slow commands

79% of commands finish in under one second. The 2% that run over a minute are 70% of all command
time, so count only these and multiply by expected runs.

| Command family | Typical | Slow case |
|---|---|---|
| Monorepo changed-files gate (typecheck, lint, tests for the diff) | 35–90 s (20 s for a small diff) | 5–7 min at p90; 10–50 min when the diff reaches shared packages |
| Targeted test files | 13–25 s | 1–4 min |
| Typecheck only | 5–15 s | 30 s–7 min |
| Dependency install in a new checkout | 3–60 s | 3–6 min |
| Rust build, incremental | 1–20 s | 1–10 min cold or release |
| Rust tests | 7–25 s | 1–6 min |
| Android APK build | 4–45 s incremental | 15–25 min cold |
| Whole-configuration check script, all areas | 8 min [4–12] | 15–20 min; one area alone is 1.5–2.5 min |
| Dev server boot before browser checks | 45–120 s | 3 min |
| Rendering, model downloads, emulators, training runs | minutes each | read the task for counts |

Measure rather than guess when the repository states its gate duration or a recent log shows it.

## 6. Delegation

- A parent's own steps do not shrink when it delegates: orchestrating turns take 60 steps with one
  child and about 150 with two or three, because launching, reading results and integrating are
  steps too.
- A child runs 7 min [2.5–14], and the slowest child of a delegating turn 7.6 min [2–25]; take the
  specific figure from table 3. Add the slowest child of each parallel batch to the whole-task
  clock. The parent's own turn usually ends, or it keeps working, while children run, so little of
  that time shows up inside the parent's turn.
- Nine or more children: 80 min [37–240] for the parent turn.
- Each review-and-repair round adds one review child (table 3) plus a repair turn (D1 or D3).

## 7. Uncertainty

- Identical briefs rerun on the same model had p75/p25 ≈ 1.5; half of the runs were within ±20%
  of their group's median.
- Knowing the true step count and command time in advance, steps × seconds per step predicts a
  turn within ±20% about a third of the time and within ±50% about two thirds. Also knowing the
  reply length and the characters written raises that to about half and about 85%. Keep the range
  wide even when the forecast feels sure.
- Outcomes are right-skewed. A blocked gate, a flaky test or a wrong first diagnosis typically
  doubles a turn; nothing halves it.
- In trials of this method on tasks held out from these tables, estimates for delegated briefs
  landed within ±20% about four times in ten. Whole tasks landed within ±20% about three times in
  ten and within ±50% six in ten. Single quick turns landed within ±20% about one time in ten and
  ran about a third shorter than estimated.
