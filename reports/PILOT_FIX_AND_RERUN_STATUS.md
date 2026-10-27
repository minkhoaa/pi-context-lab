# Pilot telemetry and evaluator repair — status

Base commit: `f1d9f448dbf9c8b2908c548708dd2c9fe198bd4a`.

## Corrections staged on this branch

- `runner/telemetry.py`: keep legacy fixed-price estimates as **scenario only**; use Pi's per-request `usage.cost.total` for primary *reported estimates*. Unknown secondary-model cost now yields `net_end_to_end_cost: null` / `SECONDARY_COST_UNVERIFIED` rather than silently using the primary model's arbitrary model-lock prices. Treat cumulative secondary custom entries as snapshots.
- `scripts/benchmark.py`: create separate session directory for each run and use `-c` only within its own four-turn session; do not repeat historical session data across new repetitions. Report unknown end-to-end costs as UNVERIFIED rather than ranking them.
- `evaluators/eval_task_l.py` and `evaluators/task_l_hidden_checks.py`: run evaluator-owned checks outside mutable workspace, and reject modifications to fixture tests; worker-side `run_tests.py` is no longer the sole correctness oracle.
- `scripts/reconcile-pilot.py`: read-only audit comparing per-request usage, original run summaries, and aggregate results. Historical P2/P3 aggregate mismatch is expected to be flagged, not silently repaired.

## Historical evidence — do not rewrite

Historical pilot (4 sessions) remains under `results/pilot-results.json`. Model-reported primary estimates are:
A $0.011974; P1 $0.013671; P2 $0.012517; P3 $0.010141.
P2 secondary summarizer cost lacks verified provider-reported per-call pricing; a full end-to-end cost ranking is therefore not justified.

Historical `results/runs/pilot-03_P2_task-l/summary.json` says NO secondary/pruning calls, while aggregate reports 4. Historical P3 summary says 0 pruning events while aggregate reports 2. Do not treat the aggregate overrides as proven without independently verified raw extension events.

## What remains to run on the user's Pi/CachyOS host

This ChatGPT execution environment cannot access the user's `~/pi-context-lab`, Pi binary, or shared OAuth credentials. We cannot execute paid model requests remotely merely by modifying a GitHub repo.

1. Pull this branch locally, run `python3 -m compileall -q runner scripts evaluators` and `bash scripts/preflight.sh`.
2. Run `python3 scripts/reconcile-pilot.py`. Expect **FAIL on historical P2/P3 mismatch**; this confirms the audit detects corruption. Do not change historical records.
3. Verify `python3 evaluators/eval_task_l.py fixtures/task-l` fails on the unmodified broken fixture. Test a known-good solution from `workspaces/` and verify all independent checks pass; if not, audit the frozen specification without altering tests to force PASS.
4. Confirm raw extension events/secondary pricing source, version, and exact event schema; capture provider-reported secondary cost directly or keep P2 price UNVERIFIED.
5. Only after green offline checks, perform a **fresh** pilot with *new run IDs*, isolated session directories and a distinct result path (do not overwrite `pilot-results.json`). Use `python3 scripts/benchmark.py run --pilot --repetitions 3 --authorize-benchmark-spend` on the host only after offline checks, with the same pinned model. The controller writes `results/pilot-v2-r3-results.json` and preserves the original report. Do not run this until the P2/P3 extension telemetry provenance gate is complete.
6. Run A/P1/P2/P3 across >=3 repetitions on Task L, preferably with counterbalanced order; isolate and track shared OAuth refresh behavior. Expand to Task S/M only after the corrected pilot.
7. Report correctness, provider-reported primary cost, verified secondary cost or UNVERIFIED, full tokens, peak per-request context, activation-event provenance and status. Never claim the rerun completed unless raw on-host telemetry exists.

## Status

**CODE PATCH PREPARED — LIVE REBENCHMARK NOT EXECUTED.** No fresh model measurements are attached to this branch.
