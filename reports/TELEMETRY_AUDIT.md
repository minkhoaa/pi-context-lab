# Telemetry Engine Audit & Metric Specification: pi-context-lab

**Date:** 2026-10-27  
**Module:** `runner/telemetry.py`  
**Test Suite:** `scripts/smoke-local.py`  
**Status:** **ALL TESTS PASSED**

---

## 1. Metric Mathematical Formulations

To provide rigorous, unskewed comparisons across context management extensions, the telemetry engine calculates:

### 1. Per-Request Input Context
$$\text{request\_input\_context}_i = \text{input}_i + \text{cache\_read}_i + \text{cache\_write}_i$$
This metric accurately represents the total volume of context evaluated by the LLM on request $i$, preventing cache-read tokens from being deceptively discounted when evaluating context growth.

### 2. Peak Reported Input Context
$$\text{peak\_input\_context} = \max_{i} (\text{request\_input\_context}_i)$$
Represents the maximum window pressure reached during the entire session.

### 3. Median Input Context
$$\text{median\_input\_context} = \text{median}(\{\text{request\_input\_context}_1, \dots, \text{request\_input\_context}_N\})$$

### 4. Cumulative Input Context
$$\text{cumulative\_input\_context} = \sum_{i=1}^{N} \text{request\_input\_context}_i$$
Reflects total lifetime context ingested by the model across all conversational turns.

### 5. Primary Model Cost
$$\text{cost}_{\text{primary}} = \sum_{i=1}^{N} \left( \frac{\text{input}_i}{10^6} \cdot P_{\text{prompt}} + \frac{\text{cache\_read}_i}{10^6} \cdot P_{\text{cr}} + \frac{\text{cache\_write}_i}{10^6} \cdot P_{\text{cw}} + \frac{\text{output}_i}{10^6} \cdot P_{\text{comp}} \right)$$
Using pinned rates from `config/model-lock.json`:
- $P_{\text{prompt}} = \$2.50$
- $P_{\text{cr}} = \$1.25$
- $P_{\text{cw}} = \$2.50$
- $P_{\text{comp}} = \$10.00$

### 6. Secondary Model Cost (P2 Summarizer)
$$\text{cost}_{\text{secondary}} = \frac{\text{sec\_input}}{10^6} \cdot P_{\text{prompt}} + \frac{\text{sec\_output}}{10^6} \cdot P_{\text{comp}}$$

### 7. Net End-to-End Cost
$$\text{cost}_{\text{net}} = \text{cost}_{\text{primary}} + \text{cost}_{\text{secondary}}$$
Ensures that background summarization is never treated as free context reduction.

---

## 2. Event & Tool Recovery Tracking

The collector parses stream events and extracts:
- `recovery_calls`: Invocations of `sift_retrieve` (P1) or `context_tree_query` (P2).
- `compression_events`: Invocations where Sift stashes output (`siftCompressed: true`).
- `pruning_events`: Batch pruning events emitted by Context Prune or DCP.
- `compaction_events`: Pi native context compactions.
- `optimization_triggered`: Boolean flag ensuring the extension actually altered context. If `false`, the run is labeled `NON_TRIGGERED`.

---

## 3. Synthetic Smoke Test Verification

The telemetry engine was verified using `scripts/smoke-local.py` against a complex multi-turn trace including tool errors, cache hits, secondary model summaries, and recovery calls:

```text
[smoke-local] Starting offline synthetic telemetry test...
PASS: request_input_context per request verified: [1600, 3500, 4000]
PASS: Peak reported input context verified: 4000
PASS: Median input context verified: 3500.0
PASS: Cumulative input context verified: 9100
PASS: Cache-read (4200) and cache-write (400) tokens verified.
PASS: Total cost calculated correctly: $0.026500
PASS: Tool calls and errors verified: {'read': 1, 'edit': 1, 'bash': 1, 'sift_retrieve': 1}, errors: 1
PASS: Recovery calls (1) and optimization trigger verified.
PASS: Secondary model calls (2) and tokens verified.
PASS: Timeout and termination safety correctly handled.

[smoke-local] ALL TELEMETRY SMOKE CHECKS PASSED.
```
