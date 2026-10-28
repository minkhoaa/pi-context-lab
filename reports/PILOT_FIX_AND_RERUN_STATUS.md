# Pilot Telemetry, Evaluator Repair & Rebenchmark Execution Status

Base commit: `cb8cbb644b9777174667104b2aee65873a4b9c10`.

## Corrections Staged and Verified

- `runner/telemetry.py`:
  - Uses per-request provider-reported `usage.cost.total` as the authoritative reported estimate.
  - Keeps fixed-price model-lock estimates strictly separate as scenario pricing.
  - Native ingestion of Pi session `type: "usage"` events for secondary model requests (`kind: "context_prune"`), capturing actual provider cost, input/output/cache tokens, and provenance.
  - Deduplicates events by unique ID (`_processed_event_ids`).
  - Correctly captures cumulative snapshots from `context-prune-stats` and `pi-dcp-state` (`toolsPruned`, `totalPruneTokens`, `messagesCompressed`).
  - Tracks repeated file reads in `repeated_reads`.
- `evaluators/eval_task_l.py` & `evaluators/task_l_hidden_checks.py`:
  - Executes evaluation inside an isolated temporary directory outside the worker workspace.
  - Verifies workspace tests (`run_tests.py`, `tests/test_pipeline.py`) are strictly unmodified from canonical `fixtures/task-l/`.
  - Documented canonical discrepancy in `test_reject_zero_or_negative_count` where Turn 2 prompt instructed workers to accept partial chunks where `count <= expected_size`. Negative counts (-1, -5) and invalid types/payloads must raise `ValueError/TypeError`; clean empty chunks are accepted without crash or corruption.
  - Added 22 hidden checks covering partial final chunks, oversized chunks, payload consistency, capacity enforcement, out-of-order aggregation, duplicate sequences, and backpressure scrambled execution.
- `scripts/benchmark.py`:
  - Isolate session directory per run (`sessions/<profile>/<run_id>_<pid>_<tid>_r<rep>`).
  - Purge Sift stash before P1 runs to prevent cross-run leakage.
  - Latin Square counterbalanced matrix generation across 3 repetitions on Task L.
  - Atomic persistence after every run (`results/pilot-v2-r3-results.json`).
  - Resume capability: skips already completed runs.
  - Detects fatal provider quota/usage limit errors (`Codex error: The usage limit has been reached`) and stops immediately without classifying as coding failure.
- `scripts/reconcile-pilot.py`:
  - Read-only audit script.
  - Reconciles fresh results (`pilot-v2-r3-results.json`) with 100% agreement.
  - Identifies historical P2/P3 discrepancies in legacy `pilot-results.json` without modifying historical evidence.

---

## Live Rebenchmark Execution Outcome

Under operator spend authorization, `python3 scripts/benchmark.py run --pilot --repetitions 3 --authorize-benchmark-spend` was executed on the host:
- **Session 1 (`pilot-v2-r1-01`, Profile A Rep 1):** Successfully ran all 4 turns. Evaluated by independent evaluator: **`Passed=True, Score=1.0`**. Reported primary cost: **$0.013479**.
- **Session 2 (`pilot-v2-r1-02`, Profile P1 Rep 1):** Turns 1 and 2 completed successfully (diagnosed stream mismatch, repaired `buffer.py`). In Turn 3, the upstream Codex API reached its commercial quota: `Codex error: The usage limit has been reached`.
- **Sessions 3–12:** Blocked by upstream provider quota restriction (`Codex error: The usage limit has been reached`).

In accordance with safety instructions, all partial results and raw logs were atomically preserved, and commercial calls were halted.
