# Rebenchmark Execution Results: Four-Profile Task L Pilot (v2)

## Executive Summary

Pursuant to authorization, a controlled fresh benchmark of the four ready context-optimization profiles (**A: Pure Baseline**, **P1: Sift**, **P2: pi-context-prune**, **P3: Pi DCP**) was executed across a 3-repetition Latin Square matrix (12 planned worker sessions) on Task L (`pipeline_engine`, 4 interactive turns per session).

During execution, **Session 1 (Profile A, Repetition 1) completed all four turns successfully**, passing the hardened independent evaluator with a score of 1.0. **Session 2 (Profile P1, Repetition 1) completed Turns 1 and 2 successfully**, but was interrupted in Turn 3 when the commercial API returned a fatal usage limit error (`Codex error: The usage limit has been reached`). All subsequent sessions were blocked by the provider usage limit.

In accordance with safety directives, the controller halted commercial calls, preserved all partial execution telemetry, and reconciled the completed evidence.

---

## 1. Execution Matrix & Protocol

| Parameter | Configuration |
|---|---|
| **Model** | `openai-codex/gpt-6-luna` |
| **Thinking** | `max` |
| **Task** | Task L (`fixtures/task-l`), 4 turns per session |
| **Profiles** | A (Baseline), P1 (Sift 0.0.2), P2 (pi-context-prune 2.1.0), P3 (Pi DCP 0.11.0) |
| **Excluded Profile** | P4 (pi-context-engine: excluded by policy) |
| **Schedule Ordering** | Latin Square Counterbalanced: <br>Rep 1: A -> P1 -> P2 -> P3 <br>Rep 2: P1 -> P2 -> P3 -> A <br>Rep 3: P2 -> P3 -> A -> P1 |
| **Total Planned** | 12 sequential independent worker sessions |
| **Session Isolation** | Unique session directory per run (`sessions/<profile>/<run_id>_<pid>_<tid>_r<rep>`) |
| **Workspace Isolation** | Fresh copy from frozen fixture per run (`workspaces/<run_id>_<pid>_<tid>_r<rep>`) |

---

## 2. Session-by-Session Execution Status

| Run ID | Profile | Rep | Turns Attempted | Exit Status | Provider Status | Independent Evaluator | Reported Primary Cost |
|---|---|---|---|---|---|---|---|
| `pilot-v2-r1-01` | **A (Baseline)** | 1 | 4 / 4 | Completed | `COMPLETED_SUCCESS` | **PASS (1.0)** | **$0.013479** |
| `pilot-v2-r1-02` | **P1 (Sift)** | 1 | 3 / 4 (partial) | Interrupted | `PARTIALLY_COMPLETED_INTERRUPTED_BY_QUOTA` | FAIL (0.2)* | $0.010296 |
| `pilot-v2-r1-03` | **P2 (Context Prune)** | 1 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r1-04` | **P3 (Pi DCP)** | 1 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r2-01` | **P1 (Sift)** | 2 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r2-02` | **P2 (Context Prune)** | 2 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r2-03` | **P3 (Pi DCP)** | 2 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r2-04` | **A (Baseline)** | 2 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r3-01` | **P2 (Context Prune)** | 3 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r3-02` | **P3 (Pi DCP)** | 3 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r3-03` | **A (Baseline)** | 3 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |
| `pilot-v2-r3-04` | **P1 (Sift)** | 3 | 1 / 4 (blocked) | Blocked | `BLOCKED_BY_PROVIDER_QUOTA` | FAIL (0.0)* | $0.000000 |

*\*Note: Runs 2–12 are classified as `provider_quota_exhausted` due to external API limit restrictions, NOT coding capability failures.*

---

## 3. Deep Dive: Completed & Partial Runs

### A. Run `pilot-v2-r1-01` (Profile A: Baseline — Repetition 1)
- **Status:** Fully completed all 4 interactive turns.
- **Duration:** 285.2 seconds wall-clock time.
- **Model Requests:** 25 requests.
- **Token Usage:**
  - Input Tokens: 45,972
  - Output Tokens: 11,509
  - Cache-Read Tokens: 312,704 (87.2% prompt cache hit rate)
  - Cache-Write Tokens: 0
  - Total Lifetime Tokens: 370,185
- **Context Metrics:**
  - Peak Input Context: 24,692 tokens
  - Median Input Context: 16,062 tokens
  - Mean Input Context: 14,347 tokens
  - Cumulative Input Context: 358,676 tokens
- **Cost Metrics:**
  - **Primary Pi-Reported Cost:** **$0.013479**
  - Secondary Cost: $0.000000 (no secondary requests)
  - Net End-to-End Cost: **$0.013479**
  - Scenario Model-Lock Price: $0.6209 (shown for calibration only; not provider billing)
- **Evaluation:**
  - **Passed:** **`True` (Score: 1.0 / 1.0)**
  - Unit Tests: PASS (all unmodified tests passed)
  - Run Standard: PASS (`python3 -m pipeline_engine.run --items 12` succeeded)
  - Run Backpressure: PASS (`python3 -m pipeline_engine.run --items 12 --backpressure` succeeded)
  - Log Volume: PASS (All log files < 50KB; log bloat eliminated)
  - Independent Hidden Checks: **PASS (22/22 hidden tests passed)**
  - Workspace Tests Immutable: `True` (zero tampering)
- **Tool Interactions:**
  - Tool calls: `bash`: 19, `read`: 16, `edit`: 4
  - Tool errors: 2
  - Repeated reads: 6

### B. Run `pilot-v2-r1-02` (Profile P1: Sift — Repetition 1)
- **Status:** Interrupted during Turn 3 by commercial provider quota limit.
- **Turn 1:** Completed in 56.5s (11 requests, diagnosed stream mismatch).
- **Turn 2:** Completed in 95.2s (8 requests, repaired `buffer.py`; `test_stage2_buffer_push_various_sizes` passed).
- **Turn 3:** Commenced backpressure diagnostic (1 request, ran `pipeline_engine.run --backpressure` and read log). At `timestamp: 1793176499140`, API call failed: `Codex error: The usage limit has been reached`.
- **Turn 4:** Attempted invocation immediately returned `Codex error: The usage limit has been reached`.
- **Sift Optimization Evidence:**
  - Compression events: 6 tool outputs compressed by Sift.
  - Recovery calls: 3 invocations of `sift_retrieve`.
  - Optimization Triggered: `True`.
  - Peak context reached: 18,340 tokens.
  - Tokens before interruption: Input 22,175, Output 6,854, Cache Read 141,600, Total 170,629.
  - Reported Cost before interruption: $0.010296.

---

## 4. Verification Evidence of Provider Blocker

To independently confirm that runs 3–12 failed due to provider usage limitations rather than benchmark harness bugs, direct CLI invocations were executed:

```bash
$ pi --provider openai-codex --model gpt-6-luna -p "ping"
Codex error: The usage limit has been reached
Command exited with code 1
```

The error is confirmed upstream at the `openai-codex` OAuth subscription level. Per Section 5 of the benchmark directives:
- No calibration sessions or model substitutions (e.g. falling back to Sonnet or another provider) were performed.
- All completed raw artifacts and session evidence are preserved atomically in `results/runs/` and `results/pilot-v2-r3-results.json`.
- The reconciliation audit (`python3 scripts/reconcile-pilot.py results/pilot-v2-r3-results.json`) passes 100%.
