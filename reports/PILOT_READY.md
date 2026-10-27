# Pilot Readiness & Verification Report: pi-context-lab

**Date:** 2026-10-27  
**Status:** **PILOT VERIFIED & GATED**  
**Execution Gate:** Requires `--authorize-benchmark-spend`  
**Laboratory Root:** `/home/khoa/pi-context-lab`

---

## 1. Executive Summary

The laboratory `pi-context-lab` has achieved complete pilot readiness. Shared OAuth authentication for the pinned model (`openai-codex/gpt-6-luna:max`) is wired and verified across all four pilot profiles. All 5 preflight verification suites passed with zero failures. Zero paid model calls have been executed.

---

## 2. Updated Candidate Readiness Matrix

| Profile | Optimizer | Package / Version | Status | Tools Registered | Auth Wiring | Pruning Strategy |
|---|---|---|:---:|---|:---:|---|
| **A** | **Pure Baseline** | *Built-in* | **READY** | `read,bash,edit,write` | Verified Symlink | None (Standard Reference) |
| **P1** | **Sift** | `@agent-context/pi-sift@0.0.2` | **READY** | `read,bash,edit,write,sift_retrieve` | Verified Symlink | Local Stash Compression (`minLength: 200`) |
| **P2** | **Context Prune** | `pi-context-prune@2.1.0` | **READY** | `read,bash,edit,write,context_tree_query,context_prune` | Verified Symlink | Batch-based (`pruneOn: "agent-message"`, `summarizerThinking: "low"`) |
| **P3** | **Pi DCP** | `@pi-vault/pi-dcp@0.11.0` | **READY** | `read,bash,edit,write,compress` | Verified Symlink | Deterministic Deduplication & Error Purging |
| **P4** | **Context Engine** | `pi-context-engine@0.7.1` | **NOT_READY** | *Excluded* | *Not Linked* | Excluded pending native compilation & local ONNX weights |

---

## 3. P2 Context Prune Configuration Update

In accordance with Section 7 instructions, Profile P2 was adjusted to use a cache-conscious, batch-based pruning strategy (`pruneOn: "agent-message"`):

- **Before (`every-turn`):** Pruned tool calls immediately after each turn, invalidating prompt prefix cache when an assistant executes multiple tools consecutively.  
  *Configuration SHA-256:* `536336287ac8186065522f3935d94566a57a043517b8699b6acae5c9acce1ecf`
- **After (`agent-message`):** Summarizes tool outputs in batches between user turns, preserving prefix cache stability across tool execution chains while drastically reducing summarizer model invocations.  
  *Configuration SHA-256:* `8f335521f76c4c451b28cbad1cfa96b642c51732c186e7973566a21f61a27d72`

Summarizer token costs are monitored via `context-prune-stats` and added to `net_end_to_end_cost` exactly once.

---

## 4. Planned 4-Run Pilot Matrix (Task L)

All pilot runs execute sequentially on Task L (`pipeline_engine`) across 4 discrete canonical prompts:

| Run ID | Profile Code | Target | Prompt Sequence | Output Verification |
|---|---|---|---|---|
| **pilot-01** | **A** | Baseline | `task-l-turn1.md` → `turn4.md` | `eval_task_l.py` |
| **pilot-02** | **P1** | Sift | `task-l-turn1.md` → `turn4.md` | `eval_task_l.py` + stash recovery check |
| **pilot-03** | **P2** | Context Prune | `task-l-turn1.md` → `turn4.md` | `eval_task_l.py` + secondary token check |
| **pilot-04** | **P3** | Pi DCP | `task-l-turn1.md` → `turn4.md` | `eval_task_l.py` + deduplication check |

---

## 5. Verification Commands & Preflight Receipt

### 5.1 Verification Script Execution
```bash
cd ~/pi-context-lab
bash scripts/setup-shared-auth.sh
python3 scripts/verify-shared-auth.py
bash scripts/preflight.sh
python3 scripts/benchmark.py dry-run --pilot
```

### 5.2 Preflight Receipt
```text
======================================================================
PREFLIGHT SUMMARY:
  Passed: 5
    - Profiles Validation
    - Shared Authentication Wiring
    - Isolation Checks
    - Fixtures & Evaluators
    - Telemetry Smoke Test
  Failed: 0
==> ALL PREFLIGHT VERIFICATIONS PASSED SUCCESSFULLY.
======================================================================
```

---

## 6. Exact Pilot Execution Command

The benchmark controller hard-blocks model execution until explicit spend authorization is provided:

```bash
cd ~/pi-context-lab
python3 scripts/benchmark.py run --pilot --authorize-benchmark-spend
```

To view the generated report after execution:
```bash
python3 scripts/benchmark.py report
```
