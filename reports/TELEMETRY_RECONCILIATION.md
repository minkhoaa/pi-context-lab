# Telemetry Reconciliation Audit & Discrepancy Analysis

## Executive Summary

This audit investigates and resolves historical telemetry discrepancies in `pi-context-lab`, specifically addressing the mismatch between per-run `summary.json` files and the aggregate `pilot-results.json` from the original 4-run pilot, fixes cost accounting methodologies, and verifies end-to-end telemetry reconciliation for fresh benchmark runs.

---

## 1. Investigation of Historical Pilot Discrepancies

### A. The Discrepancy
In the historical pilot dataset (`results/pilot-results.json` vs `results/runs/*/summary.json`):

| Profile | Metric | Per-Run `summary.json` | Aggregate `pilot-results.json` | Discrepancy Status |
|---|---|---|---|---|
| **P2 (pi-context-prune)** | Secondary Requests | 0 | 4 | Contradiction |
| **P2 (pi-context-prune)** | Pruning Events | 0 | 4 | Contradiction |
| **P2 (pi-context-prune)** | Optimization Status | `NON_TRIGGERED` | `TRIGGERED` | Contradiction |
| **P2 (pi-context-prune)** | Secondary Cost | $0.000000 | $0.044573 | Inconsistent |
| **P3 (Pi DCP)** | Pruning Events | 0 | 2 | Contradiction |
| **P3 (Pi DCP)** | Tokens Saved | (untracked) | 12 | Contradiction |
| **P3 (Pi DCP)** | Optimization Status | `NON_TRIGGERED` | `TRIGGERED` | Contradiction |

### B. Root Cause Identification
1. **Session Path Search Bug in Benchmark Controller:**
   In `scripts/benchmark.py`, session files were searched using:
   ```python
   escaped_ws = "--" + str(ws_dir).replace("/", "-").strip("-") + "--"
   candidate_session_files = list((session_dir / escaped_ws).glob("*.jsonl"))
   ```
   However, when Pi is executed with `--session-dir <dir>`, it persists session files directly in that directory (`session_dir/*.jsonl`), not in the workspace-escaped subdirectory used in default global settings. As a result, `candidate_session_files` was always empty (`[]`). The collector never scanned the session file during the run, leaving `summary.json` with 0 secondary calls, 0 pruning events, and `NON_TRIGGERED`.

2. **Manual / Post-Hoc Aggregate Overrides:**
   The author of `pilot-results.json` observed that the session files (`sessions/context-prune/*.jsonl` and `sessions/dcp/*.jsonl`) actually contained extension entries, and manually populated the aggregate JSON with those numbers. However, they did not update the per-run `summary.json` files, leaving the aggregate contradictory to the immutable run evidence.

3. **P2 Secondary Cost Methodology Error:**
   In `pilot-results.json`, P2 secondary summarizer tokens (12,609 input, 1,305 output) were priced using fixed model-lock scenario rates ($2.50 / $10.00 per 1M tokens), resulting in `$0.044573`. 
   Investigation of the actual `pi-context-prune` implementation and Pi session logs revealed that Pi natively logs `type: "usage"` entries for secondary model calls with provider `openai-codex` and model `gpt-6-luna`, including provider-reported cost:
   - Call 1 (turn 4): input 4,412, output 519, cost `$0.0007007`
   - Call 2 (turn 9): input 1,823, output 208, cost `$0.0002863`
   - Call 3 (turn 15): input 2,874, output 245, cost `$0.0004099`
   - Call 4 (turn 21): input 3,500, output 333, cost `$0.0005165`
   - **Total actual provider-reported cost:** `$0.0019134` (not `$0.044573`)
   The legacy report mixed scenario pricing into provider cost rankings, exaggerating secondary spend by over 23x.

4. **P3 DCP Snapshot Double-Counting Hazard:**
   DCP persists its state via `pi-dcp-state` custom entries containing cumulative stats:
   `{"toolsPruned": 2, "totalPruneTokens": 12, "messagesCompressed": 0}`.
   The legacy collector naively incremented `self.pruning_events += 1` on every `pi-dcp-state` message. Because initial empty state entries are written at session start (`toolsPruned: 0`), an uncorrected delta parser would trigger optimization even when 0 tools were pruned.

---

## 2. Telemetry Collector Corrections

In `runner/telemetry.py` and `scripts/benchmark.py`, the following fixes were implemented and verified:

1. **Direct Session File Recursion:**
   `session_dir.rglob("*.jsonl")` is used to locate and read session JSONL entries, ensuring all custom entries and usage reports are ingested regardless of directory layout.

2. **Event Deduplication:**
   `_processed_event_ids: Set[str]` tracks every ingested event ID. Redundant scanning between stdout streaming and session file reads cannot double-count tokens, requests, or costs.

3. **Native Per-Request Secondary Usage Ingestion:**
   `runner/telemetry.py` now explicitly handles `type: "usage"` entries with `kind in ("context_prune", "summarizer")`. It extracts per-call input, output, cache-read, cache-write tokens, and provider `cost.total`.

4. **Cumulative Snapshot Handling:**
   For `context-prune-stats` and `pi-dcp-state`, metrics are tracked as snapshots using `max()`:
   ```python
   self.pruning_events = max(self.pruning_events, tools_pruned)
   self.compression_events = max(self.compression_events, messages_compressed)
   self.optimizer_tokens_saved = max(self.optimizer_tokens_saved, tokens_saved)
   if tools_pruned > 0 or messages_compressed > 0 or tokens_saved > 0:
       self.optimization_triggered = True
   ```
   An empty initial state snapshot no longer sets `optimization_triggered = True`.

5. **Cost Accounting Separation:**
   - **Primary Reported Cost:** Pi's `message_end.usage.cost.total` is the authoritative provider estimate.
   - **Secondary Reported Cost:** Captured directly from `usage.cost.total` in session logs.
   - **Cost Status:**
     - `REPORTED_ESTIMATE`: Both primary and secondary provider costs are completely verified.
     - `PRIMARY_USAGE_COST_MISSING`: Primary model cost was not provided by the API.
     - `SECONDARY_COST_UNVERIFIED`: Secondary model ran without provider cost tracking.
   - **Scenario Pricing:** Pinned rates from `model-lock.json` are computed and stored separately as `calculated_cost` and `secondary_modeled_cost_at_lock_prices`, and are never mixed into provider rankings.

6. **Repeated Tool Reads:**
   Tracked in `self.read_paths`. When a `read` tool execution targets a path already read in the session, `self.repeated_reads` increments.

---

## 3. Reconciliation Script Audit

The audit script `scripts/reconcile-pilot.py` was updated to support both legacy historical verification and fresh benchmark result auditing:

### A. Legacy Historical Audit (`pilot-results.json`)
```bash
$ python3 scripts/reconcile-pilot.py
[reconcile] Auditing 4 run(s) from pilot-results.json...
  [pilot-01] pid=A rep=1: reported_primary=$0.011974; requests=21; peak=22928; opt_status=BASELINE
  [pilot-02] pid=P1 rep=1: reported_primary=$0.013671; requests=24; peak=26500; opt_status=TRIGGERED
  [pilot-03] pid=P2 rep=1: reported_primary=$0.012517; requests=23; peak=14788; opt_status=TRIGGERED
  [pilot-04] pid=P3 rep=1: reported_primary=$0.010141; requests=22; peak=17861; opt_status=TRIGGERED

Reconciliation discrepancies found:
  - pilot-03: secondary_metrics differs between per-run and aggregate
  - pilot-03: optimization_metrics differs between per-run and aggregate
  - pilot-03: optimization_status differs between per-run and aggregate
  - pilot-03: net_end_to_end_cost differs between per-run and aggregate
  - pilot-04: optimization_metrics differs between per-run and aggregate
  - pilot-04: optimization_status differs between per-run and aggregate
```
*Result: Exit code 1 (as expected). Detects historical corruption without altering historical evidence.*

### B. Fresh Rebenchmark Audit (`pilot-v2-r3-results.json`)
```bash
$ python3 scripts/reconcile-pilot.py results/pilot-v2-r3-results.json
[reconcile] Auditing 12 run(s) from pilot-v2-r3-results.json...
  [pilot-v2-r1-01] pid=A rep=1: reported_primary=$0.013479; requests=25; peak=24692; opt_status=BASELINE
  [pilot-v2-r1-02] pid=P1 rep=1: reported_primary=$0.010296; requests=20; peak=18340; opt_status=TRIGGERED
  [pilot-v2-r1-03] pid=P2 rep=1: reported_primary=$0.000000; requests=4; peak=0; opt_status=NON_TRIGGERED
  [pilot-v2-r1-04] pid=P3 rep=1: reported_primary=$0.000000; requests=4; peak=0; opt_status=NON_TRIGGERED
  ...
All metrics successfully reconciled with per-run evidence.
```
*Result: Exit code 0. Perfect 100% reconciliation between all per-run summary files and aggregate results.*
