# Pilot Benchmark Analysis & Optimization Audit: pi-context-lab

**Date:** 2026-10-27  
**Workload:** Task L (`pipeline_engine`) — 4 Interactive Turns  
**Model:** `openai-codex/gpt-6-luna` (thinking: `max`)  
**Execution Mode:** Sequential Pilot (4 independent runs: A, P1, P2, P3)  

---

## 1. Executive Summary

The 4-run pilot was executed sequentially under strict isolation to evaluate whether modern Pi context optimizers genuinely reduce token consumption, peak window context, and monetary costs during heavy multi-turn log debugging without compromising correctness.

## 2. Pilot Performance & Telemetry Comparison Table

| Metric | Profile A (Baseline) | Profile P1 (Sift) | Profile P2 (Context Prune) | Profile P3 (Pi DCP) |
|---|:---:|:---:|:---:|:---:|
| **Task Correctness** | PASS (score: 1.0) | PASS (score: 1.0) | PASS (score: 1.0) | PASS (score: 1.0) |
| **Optimization Status** | `BASELINE` | `TRIGGERED` | `TRIGGERED` | `TRIGGERED` |
| **Peak Input Context** | 22,928 | 26,500 | 14,788 | 17,861 |
| **Cumulative Input Context** | 315,161 | 386,707 | 199,602 | 242,949 |
| **Model Requests** | 21 | 24 | 23 | 22 |
| **Total Input Tokens** | 47,769 | 31,635 | 66,738 | 31,749 |
| **Total Output Tokens** | 9,047 | 13,914 | 9,030 | 9,708 |
| **Cache-Read Tokens** | 267,392 | 355,072 | 132,864 | 211,200 |
| **Cache-Write Tokens** | 0 | 0 | 0 | 0 |
| **Secondary Requests (Summarizer)** | 0 | 0 | 4 | 0 |
| **Secondary Tokens** | 0 | 0 | In: 12,609, Out: 1,305 | 0 |
| **Secondary Cost** | $0.000000 | $0.000000 | $0.044573 | $0.000000 |
| **Primary Model Cost** | $0.544133 | $0.662068 | $0.423225 | $0.440453 |
| **Net End-to-End Cost** | **$0.544133** | **$0.662068** | **$0.467798** | **$0.440453** |
| **Wall Duration (s)** | 161.11s | 215.43s | 164.7s | 160.76s |
| **Recovery / Retrieve Calls** | 0 | 6 | 0 | 0 |

---

## 3. Deep-Dive Profile Comparisons

### 3.1 Profile A vs Profile P1 (Sift)
- Sift compresses tool outputs exceeding 200 bytes using heuristic pattern recognition and stashes original full text in the isolated stash.
- Net financial impact is evaluated by comparing baseline cumulative token ingestion against compressed output tokens plus retrieval latency.
- In this pilot, P1 achieved Peak Context of 26,500 vs Baseline 22,928.

### 3.2 Profile A vs Profile P2 (pi-context-prune)
- Context Prune uses a batch-based summarizer (`agent-message`) with thinking `low`.
- Secondary summarizer requests: 4 calls, incurring $0.044573 extra model spend.
- Net end-to-end cost: $0.467798 vs Baseline $0.544133.

### 3.3 Profile A vs Profile P3 (Pi DCP)
- Pi DCP applies dynamic deduplication and error purging on `context` events without secondary model calls.
- In this pilot, P3 achieved Peak Context of 17,861 and Cumulative Context of 242,949.
- Net end-to-end cost: $0.440453 vs Baseline $0.544133.

---

## 4. Multi-Criteria Pilot Rankings

Ranking of candidates across 7 primary evaluation criteria based on this pilot repetition:

1. **Task Correctness:**
   - **baseline (A):** Score 1.0 (Passed)
   - **sift (P1):** Score 1.0 (Passed)
   - **context-prune (P2):** Score 1.0 (Passed)
   - **dcp (P3):** Score 1.0 (Passed)

2. **Net End-to-End Cost:**
   - **dcp (P3):** $0.440453
   - **context-prune (P2):** $0.467798
   - **baseline (A):** $0.544133
   - **sift (P1):** $0.662068

3. **Peak Input Context (Lowest Window Pressure):**
   - **context-prune (P2):** 14,788 tokens
   - **dcp (P3):** 17,861 tokens
   - **baseline (A):** 22,928 tokens
   - **sift (P1):** 26,500 tokens

4. **Cumulative Input Context (Total Lifetime Context):**
   - **context-prune (P2):** 199,602 tokens
   - **dcp (P3):** 242,949 tokens
   - **baseline (A):** 315,161 tokens
   - **sift (P1):** 386,707 tokens

5. **Model Requests:**
   - **baseline (A):** 21 requests
   - **dcp (P3):** 22 requests
   - **context-prune (P2):** 23 requests
   - **sift (P1):** 24 requests

6. **Wall-Clock Duration (Fastest to Slowest):**
   - **dcp (P3):** 160.76s
   - **baseline (A):** 161.11s
   - **context-prune (P2):** 164.7s
   - **sift (P1):** 215.43s

7. **Optimization Reliability & Recovery Overhead:**
   - **baseline (A):** Status `BASELINE`, 0 recovery calls, 4 tool errors
   - **sift (P1):** Status `TRIGGERED`, 6 recovery calls, 4 tool errors
   - **context-prune (P2):** Status `TRIGGERED`, 0 recovery calls, 5 tool errors
   - **dcp (P3):** Status `TRIGGERED`, 0 recovery calls, 4 tool errors

---

## 5. Post-Pilot Shared Authentication Verification

Symlinks connecting `agents/*/auth.json` to `~/.pi/agent/auth.json` were audited immediately following pilot execution to verify that automatic OAuth token refresh operations did not corrupt or decouple the symbolic links.

## 6. Recommendations for Full Benchmark Matrix

1. **Single-Repetition Caveat:** These results represent repetition 1 on Task L. Statistical variance across network latency and model reasoning paths requires the full 3-repetition Latin Square matrix before declaring absolute efficiency.

2. **Secondary Model Budgeting:** The secondary model costs in P2 must remain explicitly accounted for in all reporting to prevent masking summarizer overhead.

3. **Proceed to Full Matrix:** All ready candidates (A, P1, P2, P3) demonstrated runtime compatibility and stability under heavy tool pressure.
