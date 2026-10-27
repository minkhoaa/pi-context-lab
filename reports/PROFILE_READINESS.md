# Profile Readiness Classification Report: pi-context-lab

**Date:** 2026-10-27  
**Benchmark Target:** 5 Profiles (A, P1, P2, P3, P4)  
**Laboratory Root:** `/home/khoa/pi-context-lab`

---

## 1. Classification Definitions

In accordance with Section 15 of the laboratory protocol, every candidate is evaluated against strict readiness criteria and assigned one of the following states:

- **`READY`**: Candidate is fully packaged, requires zero unbundled dependencies, operates offline without undeclared network calls, and functions cleanly within isolated sessions.
- **`READY_WITH_LIMITATIONS`**: Candidate operates properly but requires an isolated local dependency install or operational constraints (e.g. secondary model token tracking).
- **`NOT_READY`**: Candidate cannot execute without manual build steps, local model staging, or unresolved native compilation.
- **`UNSUPPORTED`**: Candidate is incompatible with the installed Pi version or Node.js runtime.
- **`SECURITY_BLOCKED`**: Candidate exhibits unsafe behavior (arbitrary code execution, telemetry leakage, unisolated global writes).

---

## 2. Profile Readiness Matrix

| Profile | Candidate | Classification | Primary Rationale |
|---|---|---|---|
| **A** | Pure Baseline | **READY** | Standard Pi built-in tools (`read,bash,edit,write`). Zero extensions, zero prompt overlays, 100% isolated. |
| **P1** | Sift (`@agent-context/pi-sift`) | **READY_WITH_LIMITATIONS** | Fully operational once `@agent-context/sift@0.0.1` is installed locally. Registers `sift_retrieve` tool. Stash is isolated outside worktrees. |
| **P2** | pi-context-prune (`pi-context-prune`) | **READY** | Pre-bundled standalone ESM (`dist/index.js`). Zero external dependencies. Compatible with Node 24. Secondary summarization tokens must be tracked. |
| **P3** | Pi DCP (`@pi-vault/pi-dcp`) | **READY** | Pure local deterministic pruning. Engine requirement `>=24.15.0` natively satisfied by Node `v24.21.0`. Zero external dependencies. |
| **P4** | Pi Context Engine (`pi-context-engine`) | **NOT_READY** | Uninstalled dependencies: `better-sqlite3` requires Node 24 native build; embedding weights (~80MB) missing locally; attempts outbound pricing HTTP requests. |

---

## 3. Candidate Profiles Detailed Assessment

### Profile A: Pure Baseline
- **Status:** **`READY`**
- **Registered Tools:** `read`, `bash`, `edit`, `write` (4 tools).
- **Extension Flag:** None.
- **Operational Risk:** Zero.

### Profile P1: Sift (`@agent-context/pi-sift`)
- **Status:** **`READY_WITH_LIMITATIONS`**
- **Registered Tools:** `read`, `bash`, `edit`, `write`, `sift_retrieve` (5 tools).
- **Extension Flag:** `-e /home/khoa/pi-context-lab/candidates/sift/package/index.ts`
- **Limitations:**
  1. Requires local installation of core companion package: `@agent-context/sift@0.0.1`.
  2. Stash location must reside outside execution worktree (asserted by code). Redirected to `PI_CODING_AGENT_DIR/sift`.

### Profile P2: pi-context-prune (`pi-context-prune`)
- **Status:** **`READY`**
- **Registered Tools:** `read`, `bash`, `edit`, `write`, `context_tree_query`, `context_prune` (or default builtins + query tools).
- **Extension Flag:** `-e /home/khoa/pi-context-lab/candidates/context-prune/package/dist/index.js`
- **Operational Considerations:**
  - Pruning relies on background summarizer calls through the primary provider interface (`ctx.model`).
  - Telemetry parser must capture both the primary task tokens and any auxiliary summarizer tokens to calculate net end-to-end cost accurately.

### Profile P3: Pi DCP (`@pi-vault/pi-dcp`)
- **Status:** **`READY`**
- **Registered Tools:** `read`, `bash`, `edit`, `write`, `compress` (5 tools, or 4 builtins with auto-pruning pipeline).
- **Extension Flag:** `-e /home/khoa/pi-context-lab/candidates/dcp/package/src/index.ts`
- **Operational Considerations:**
  - Evaluates message deduplication and error purging deterministically.
  - Generates zero external API calls or background model costs during standard deterministic pruning.

### Profile P4: Pi Context Engine (`pi-context-engine`)
- **Status:** **`NOT_READY`**
- **Reason for Exclusion from Immediate Execution:**
  1. **Uncompiled Native Addon:** `better-sqlite3` must be compiled against Node 24 headers (`node-gyp`).
  2. **Model Download Prohibition:** Requires downloading ONNX transformer embedding models (~80MB) from Hugging Face Hub during initialization. The laboratory strictly forbids unisolated network model downloads during benchmark execution.
  3. **Web Polling:** Attempts to poll `https://docs.anthropic.com` for pricing tables.
- **Action Plan to Reach READY:**
  1. Compile native addons within `candidates/context-engine/package` without touching system directories.
  2. Pre-cache local ONNX embedding model weights into `/home/khoa/pi-context-lab/storage/models/` and set `PCE_TRANSFORMERS_CACHE`.
  3. Patch pricing loader to use static configuration instead of live web scraping.
