# Benchmark Protocol & Experimental Specification: pi-context-lab

**Date:** 2026-10-27  
**Controller:** `scripts/benchmark.py`  
**Planned Matrix Scope:** 45 Worker Sessions (5 Profiles × 3 Tasks × 3 Replications)

---

## 1. Primary Research Question

> **Which standalone context-management tool genuinely reduces end-to-end model token usage, peak context size, and estimated task cost without reducing coding correctness or increasing recovery/re-reading overhead?**

---

## 2. Pinned Model & Pricing Configuration

All benchmark runs are strictly locked to:
- **Provider:** `openai-codex`
- **Model:** `gpt-6-luna`
- **Thinking Level:** `max`
- **Pricing Model (`config/model-lock.json`):**
  - Prompt Tokens: `$2.50` per 1M tokens
  - Cache Read Tokens: `$1.25` per 1M tokens
  - Cache Write Tokens: `$2.50` per 1M tokens
  - Completion (Output) Tokens: `$10.00` per 1M tokens

Silent model switching or provider routing overrides are strictly forbidden. If an optimizer requires a different model or provider, it is excluded from the controlled comparison.

---

## 3. Experimental Matrix Design

| Profile Code | Profile Name | Task S (Short) | Task L (Long Multi-Turn) | Task M (Navigation) | Total Runs |
|---|---|:---:|:---:|:---:|:---:|
| **A** | Pure Baseline | 3 | 3 | 3 | 9 |
| **P1** | Sift | 3 | 3 | 3 | 9 |
| **P2** | pi-context-prune | 3 | 3 | 3 | 9 |
| **P3** | Pi DCP | 3 | 3 | 3 | 9 |
| **P4** | Context Engine | 3 | 3 | 3 | 9 |
| **Total** | | **15** | **15** | **15** | **45** |

### Counterbalanced Execution Schedule
To mitigate order effects, time-of-day API latency variances, and remote prompt-cache warm-up bias, runs are sequenced according to a balanced Latin Square schedule rather than running all baseline runs first followed by candidates.

---

## 4. Multi-Turn Execution Protocol

Task L requires true multi-turn interaction over 4 discrete steps:
1. Turn 1: Inspection & diagnosis of pipeline error logs.
2. Turn 2: Initial repair in `buffer.py`.
3. Turn 3: Addressing backpressure error in `aggregator.py`.
4. Turn 4: Final verification and log cleanup.

### Session Continuation Mechanism
- Workers utilize Pi's native session persistence via `--session-dir /home/khoa/pi-context-lab/sessions/<profile>` and `--session-id <run_uuid>`.
- Successive turns pass `--continue` or use the Pi RPC interface with the pinned session UUID, preserving conversation history without concatenating prompts into a artificial one-shot request.
- After each turn, context size is logged into the session telemetry JSONL.

---

## 5. Telemetry Specifications

For every API request within each worker run, the telemetry collector captures:
- Provider, model, request sequence number
- `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`
- **Derived Metric:**  
  $$\text{request\_input\_context} = \text{input} + \text{cache\_read} + \text{cache\_write}$$
- Peak input context: $\max(\text{request\_input\_context})$
- Median input context: $\text{median}(\text{request\_input\_context})$
- Cumulative input context: $\sum \text{request\_input\_context}$
- Wall-clock elapsed duration and tool calls (counts, errors, recovery invocations)
- Financial cost: Calculated using pinned pricing constants. Secondary summarization tokens (e.g. from P2) are explicitly accounted for in net end-to-end cost.

---

## 6. Execution Safety Gates

To prevent accidental commercial API consumption:
- The controller commands `run --pilot` and `run --full` are hard-blocked by an authorization switch.
- Running without `--authorize-benchmark-spend` or setting `BENCHMARK_SPEND_AUTHORIZED=1` aborts immediately with zero network or model calls.
- Initial live testing must always start with a single-repetition pilot across ready profiles before initiating the full 45-run matrix.
