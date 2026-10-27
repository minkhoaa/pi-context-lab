# Controlled Pilot Execution Plan: pi-context-lab

**Date:** 2026-10-27  
**Target:** Task L (`pipeline_engine`) — 4 Interactive Turns  
**Scope:** Exactly 4 Planned Sessions (Sequential Execution Only)  
**Safety Status:** **HOLD — REQUIRES OPERATOR SPEND AUTHORIZATION**

---

## 1. Experimental Objective

The controlled pilot serves as the empirical gate before authorizing the full 45-session benchmark matrix. It validates that:
1. Candidate extensions activate properly during realistic multi-turn tool pressure.
2. Net end-to-end costs (including summarizer tokens) are accurately reported.
3. Task correctness is maintained without regression.
4. Any run where optimization fails to trigger is transparently classified as `NON_TRIGGERED`.

---

## 2. Planned Pilot Sessions

All runs execute sequentially in isolated workspaces cloned freshly from `fixtures/task-l`:

| Run ID | Profile Code | Candidate | Mode / Flags | Expected Optimization Behavior |
|---|---|---|---|---|
| **pilot-01** | **A** | Pure Baseline | *No extensions* | Reference baseline context growth across 4 turns. |
| **pilot-02** | **P1** | Sift | `-e candidates/sift/package/index.ts` | Stashes pipeline log outputs > 200 bytes; tests `sift_retrieve` recovery. |
| **pilot-03** | **P2** | Context Prune | `-e candidates/context-prune/package/dist/index.js` | Summarizes completed tool batches at `turn_end`; secondary model tokens captured in telemetry. |
| **pilot-04** | **P3** | Pi DCP | `-e candidates/dcp/package/src/index.ts` | Deduplicates repeated test failures and error traces deterministically on context build. |

*(Profile P4 is excluded from the pilot).*

---

## 3. Workload Protocol: Task L (4 Discrete Turns)

Each worker session maintains a persistent session across 4 canonical prompts:
- **Turn 1 (`prompts/task-l-turn1.md`):** Initial inspection of `pipeline_engine`, execution of pipeline, diagnosis of chunk size mismatch in large log dumps.
- **Turn 2 (`prompts/task-l-turn2.md`):** Implementation of initial repair in `buffer.py` and execution of tests.
- **Turn 3 (`prompts/task-l-turn3.md`):** Diagnosis of second error trace under backpressure and repair of `aggregator.py`.
- **Turn 4 (`prompts/task-l-turn4.md`):** Full end-to-end verification and verification that generated log files are cleaned up.

After completion of Turn 4, the independent evaluator (`evaluators/eval_task_l.py`) executes out-of-process in the workspace to score correctness (`passed: bool`, `score: float`).

---

## 4. Telemetry Metrics Measured

For each of the 4 pilot runs:
1. **Task Correctness:** Evaluator score (must equal 1.0 / passed).
2. **Net End-to-End Cost:** Primary model cost + secondary summarizer model cost.
3. **Context Metrics:** Peak input context, median input context, cumulative input context.
4. **Token Breakdown:** Input tokens, output tokens, cache-read tokens, cache-write tokens.
5. **Tool & Recovery Accounting:** Total tool calls, tool errors, recovery calls (`sift_retrieve`, `context_tree_query`).
6. **Activation Verdict:** Classified as `TRIGGERED` or `NON_TRIGGERED`.
7. **Elapsed Duration & Latency:** Total wall-clock time and extension processing overhead.

---

## 5. Execution Prerequisites & Exact Commands

### Prerequisite 1: Authenticate Isolated Profile Directories
Prior to execution, credentials must be populated in the isolated agent directories:
```bash
PI_CODING_AGENT_DIR="/home/khoa/pi-context-lab/agents/baseline" pi auth login --provider openai-codex
PI_CODING_AGENT_DIR="/home/khoa/pi-context-lab/agents/sift" pi auth login --provider openai-codex
PI_CODING_AGENT_DIR="/home/khoa/pi-context-lab/agents/context-prune" pi auth login --provider openai-codex
PI_CODING_AGENT_DIR="/home/khoa/pi-context-lab/agents/dcp" pi auth login --provider openai-codex
```

### Prerequisite 2: Operator Authorization & Execution
Once authenticated, the operator authorizes and launches the sequential pilot run:
```bash
cd ~/pi-context-lab
python3 scripts/benchmark.py run --pilot --authorize-benchmark-spend
```

### Prerequisite 3: Generate and Review Report
```bash
python3 scripts/benchmark.py report
cat reports/BENCHMARK_REPORT.md
```
