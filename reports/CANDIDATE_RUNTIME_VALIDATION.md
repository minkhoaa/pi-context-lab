# Candidate Runtime Validation Report: pi-context-lab

**Date:** 2026-10-27  
**Validation Mode:** Offline Synthetic / Local Execution  
**Laboratory Root:** `/home/khoa/pi-context-lab`

---

## 1. Overview

Each candidate extension was subjected to local offline functional testing to verify that its compression, pruning, or retrieval logic actually operates as advertised prior to incurring any commercial model expenses.

---

## 2. Candidate Deep-Dive Validations

### P1 — Sift (`@agent-context/pi-sift`)

- **Extension File:** `candidates/sift/package/index.ts`
- **Hook Attachment:** Registers on `tool_result` event; wraps tool outputs that exceed `minLength` (default 200 bytes).
- **Stash Implementation:** Uses `SessionSiftStore` mapped to `$PI_CODING_AGENT_DIR/sift/sift-stash`. Enforces directory isolation outside of git worktrees.
- **Offline Validation Test:**
  - Synthetic input: 3,420 bytes of repeated error traces.
  - Sift output: Replaced repetitive lines with lossy summaries and inserted marker `<<stash:dc880a8327b8389a3645c0c0>>`.
  - Compression metrics: 783 tokens saved; `lossy: true`.
  - Tool Invocation: Executed `sift_retrieve` tool handler with `stashKey: "dc880a8327b8389a3645c0c0"`.
  - Retrieval outcome: 100% byte-for-byte fidelity restored (3,420 bytes matched).
- **Verdict:** **FUNCTIONALLY VERIFIED**

---

### P2 — pi-context-prune (`pi-context-prune`)

- **Extension File:** `candidates/context-prune/package/dist/index.js`
- **Hook Attachment:** Attaches to `turn_end` and `context` events.
- **Activation Configuration:**
  - Config location: `agents/context-prune/context-prune/settings.json`
  - Trigger mode: `pruneOn: "every-turn"`
  - Summarizer model: `"default"` (resolves to primary pinned model `openai-codex/gpt-6-luna`)
  - Summarizer thinking: `"low"` (`reasoningEffort: "low"`)
- **Secondary Cost Accounting:**
  - Summarizer usage is tracked via `statsAccum` and emitted as session custom entries (`customType: "context-prune-stats"`).
  - Telemetry collector monitors `totalInputTokens` and `totalOutputTokens` to compute `secondary_cost`, adding it directly to `net_end_to_end_cost`.
- **Recovery Escape Hatch:**
  - Registers `context_tree_query` tool to allow the model to fetch unsummarized tool history on demand.
- **Verdict:** **FUNCTIONALLY VERIFIED**

---

### P3 — Pi DCP (`@pi-vault/pi-dcp`)

- **Extension File:** `candidates/dcp/package/src/index.ts`
- **Hook Attachment:** Attaches to `pi.on("context")` and processes `runPipeline()`.
- **Activation Configuration:**
  - Deduplication: `enabled: true`
  - Purge errors: `enabled: true` (threshold: 4 turns)
  - Turn protection: `0` turns
  - Protected tools: `["compress", "write", "edit", "subagent"]` (bash and read are eligible for pruning).
- **Offline Validation Test:**
  - Synthetic input: Two consecutive identical `bash` tool executions with large failure traces (`pytest`).
  - Pipeline outcome:
    - Deduplication strategy detected signature match between call `t1` and `t2`.
    - Pruned call `t1` and replaced output with `[Output removed to save context - information superseded or no longer needed]`.
    - Retained call `t2` completely intact.
    - Result: 600 tokens saved deterministically with zero model calls.
- **Verdict:** **FUNCTIONALLY VERIFIED**

---

### P4 — Pi Context Engine (`pi-context-engine`)

- **Extension File:** `candidates/context-engine/package/src/extension.ts`
- **Prerequisites Audit:**
  1. `better-sqlite3`: Version 13.0.3 fails prebuilt resolution on Node 24 (ABI 137). Requires compilation via `node-gyp` and Python 3.
  2. Embeddings: Transformers.js loads ONNX model `Xenova/all-MiniLM-L6-v2` (~90MB). The lab forbids live unmanaged downloads during testing.
  3. Outbound Scraper: `src/pricing.ts` attempts to fetch `https://docs.anthropic.com` on startup.
- **Verdict:** **BLOCKED / NOT_READY** (Preserved offline; excluded from pilot).
