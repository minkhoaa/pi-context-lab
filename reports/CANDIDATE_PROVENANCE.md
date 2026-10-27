# Candidate Provenance & Security Audit Report: pi-context-lab

**Date:** 2026-10-27  
**Auditor:** Automated Subagent Specialist (`antigravity/gemini-3.8-flash:low`)  
**Artifact Directory:** `/home/khoa/pi-context-lab/candidates/`

---

## 1. Overview and Security Principles

All candidate extensions were fetched directly from the official npm registry and unpacked locally into `/home/khoa/pi-context-lab/candidates/`. In accordance with laboratory safety requirements:
1. No packages were installed globally.
2. No arbitrary setup scripts or untrusted lifecycle scripts were executed.
3. Every package's entry point, dependency tree, tool schema, filesystem writes, and network calls were statically traced.

---

## 2. Comprehensive Candidate Audits

### Candidate P1: Sift (`@agent-context/pi-sift`)

- **Package Name:** `@agent-context/pi-sift`
- **Resolved Version:** `0.0.2`
- **License:** Apache-2.0
- **Upstream Repository:** `https://github.com/agents-sdk/sift`
- **Publisher / Maintainer:** `liangshuai <509856256@qq.com>`
- **Package Integrity:**
  - Tarball: `agent-context-pi-sift-0.0.2.tgz`
  - Shasum: `d20f274ec1fdee383b35ca95a3915a9efcc0fb12`
  - SHA-512: `sha512-aHjY7r605F1nyciHa7R1PmGLaqyL01/Dr8SU6DrCB29fXioQWahq0XAgGSGLGlghzf1BPpHljyhbIWswp5Uulw==`
- **Entry Point:** `./index.ts`
- **Declared Dependencies:**
  - `@agent-context/sift`: `0.0.1` (unbundled; requires local npm install)
- **Lifecycle Scripts:** None.
- **Registered Tools:**
  - `sift_retrieve`: Allows the model to fetch original text from the local stash when compressed output contains `<<stash:KEY>>`.
- **System Prompt Injections:** None.
- **Filesystem Writes:**
  - Stash files stored in `$PI_CODING_AGENT_DIR/sift`.
  - Isolation enforcement: Package explicitly asserts stash directory is outside the active worktree (`assertOutsideWorktree`).
- **Network Activity:** None. Completely local execution.
- **Provenance Gate Status:** **PASSED** (Ready with dependency limitation).

---

### Candidate P2: pi-context-prune (`pi-context-prune`)

- **Package Name:** `pi-context-prune`
- **Resolved Version:** `2.1.0`
- **License:** MIT
- **Upstream Repository:** `https://github.com/championswimmer/pi-context-prune`
- **Publisher / Maintainer:** `championswimmer <championswimmer@gmail.com>` (via GitHub Actions OIDC)
- **Package Integrity:**
  - Tarball: `pi-context-prune-2.1.0.tgz`
  - Shasum: `426867a25d3f3d5eab855ab2900881350ecc74f3`
  - SHA-512: `sha512-4bCvuma/5kHwAM1lxabXlcOe/FG+FO2XCMhORDlV5sSVKoGV37zM+3H+p4j1EasARqKTrniWWVR4FJaiEVePrg==`
- **Entry Point:** `./dist/index.js` (pre-bundled standalone ESM, zero external runtime dependencies)
- **Declared Dependencies:** None.
- **Lifecycle Scripts:** `prepack` (build time only).
- **Registered Tools:**
  - `context_tree_query`: Queries original tool-call results that have been pruned from active context.
  - `context_prune`: Explicit tool allowing the model to trigger summarization and pruning of preceding tool outputs.
- **System Prompt Injections:**
  - Injects `[Context Prune — Agentic Auto Mode]` instructions into system prompt explaining pruning triggers.
- **Filesystem Writes:**
  - `$PI_CODING_AGENT_DIR/context-prune/settings.json`.
- **Network Activity & Secondary Model Invocations:**
  - **Important:** Does not make external telemetry requests, BUT triggers summarization calls to the primary LLM provider via Pi's native `ctx.model / provider.stream(...)` interface. These secondary token calls must be tracked in telemetry.
- **Provenance Gate Status:** **PASSED** (Ready for benchmarking).

---

### Candidate P3: Pi DCP (`@pi-vault/pi-dcp`)

- **Package Name:** `@pi-vault/pi-dcp`
- **Resolved Version:** `0.11.0`
- **License:** MIT
- **Upstream Repository:** `https://github.com/pi-vault/pi-dcp`
- **Publisher / Maintainer:** `lanhhoang <lanhhoang.dev@gmail.com>` (via GitHub Actions OIDC)
- **Package Integrity:**
  - Tarball: `pi-vault-pi-dcp-0.11.0.tgz`
  - Shasum: `32af24847913e0933aa244d57a494184f75a18ad`
  - SHA-512: `sha512-wDbFEna6dbNJ43QlediM81EFm2Ikc+4HoFMhG85xEv38t6z5rVqMHt1EHDdbnCv1BZeAOjoAcW31q3Sayu9mlA==`
- **Entry Point:** `./src/index.ts`
- **Runtime Engines:** `node: ">=24.15.0"` (Compatible with installed Node v24.21.0).
- **Declared Dependencies:** None (uses Pi core and Node built-in modules).
- **Lifecycle Scripts:** None.
- **Registered Tools:**
  - `compress`: Compresses conversation messages or ranges into technical summaries.
- **System Prompt Injections:**
  - Injects `sections.dcp` into system prompt options when compression is active.
- **Filesystem Writes:**
  - `$PI_CODING_AGENT_DIR/extensions/dcp.json` and session JSONL custom entries (`pi-dcp-state`).
- **Network Activity:** None. Completely local deterministic rule-based pruning (deduplication, error purging, length trimming).
- **Provenance Gate Status:** **PASSED** (Ready for benchmarking).

---

### Candidate P4: Pi Context Engine (`pi-context-engine`)

- **Package Name:** `pi-context-engine`
- **Resolved Version:** `0.7.1`
- **License:** MIT
- **Registry Record:** `https://pi.dev/packages/pi-context-engine`
- **Authoritative Source Repository:** `https://github.com/pungggi/pi-context-engine` *(Note: Verified published source differs from the unverified legacy ngsoftware URL)*.
- **Publisher / Maintainer:** `ngsoftware <alessandro.pungitore@gmail.com>` (via GitHub Actions OIDC)
- **Package Integrity:**
  - Tarball: `pi-context-engine-0.7.1.tgz`
  - Shasum: `c0227e785fdc8fe1ffca2c1e03fdc34737c523d2`
  - SHA-512: `sha512-+WTIitgpMKC8iVZ/hax0REVVuM2S3k94u0a/DG3MAlw6DuCMeHwMlmTTXw9CLGrVl9dA5+UZht8Jh24UVILauA==`
- **Entry Point:** `./src/extension.ts`
- **Declared Dependencies:**
  - `better-sqlite3`: `^13.0.3` (Requires C++ native compilation / node-gyp for Node 24 ABI 137).
  - `sqlite-vec`: `^0.1.9`
  - `web-tree-sitter`: `^0.22.6`
  - `tree-sitter-wasms`: `^0.1.13`
  - `yaml`: `^2.9.1`
  - `@huggingface/transformers`: `^4.3.1` (optional / embedding runtime)
- **Lifecycle Scripts:** `prepublishOnly`.
- **Registered Tools (10 tools):**
  - `context_search`, `expand_chunk`, `related_context`, `session_recall`, `session_timeline`, `session_event`, `record_decision`, `record_code_area`, `index_status`, `reindex`.
- **System Prompt Injections:**
  - Injects `sections.context_search_guidelines` (~900 tokens) with retrieval instructions.
- **Filesystem Writes:**
  - Writes to `~/.pi-context-engine/` and `./.context-engine.yaml`.
- **Network Activity & External Calls:**
  - Static analysis revealed:
    1. HTTP GET request to `https://docs.anthropic.com/en/docs/about-claude/models` to fetch pricing.
    2. Model weights download (~80MB ONNX) from Hugging Face Hub if using local transformer embeddings.
    3. HTTP requests to `http://localhost:11434` if using Ollama.
    4. Ephemeral HTTP dashboard server on `127.0.0.1`.
- **Provenance Gate Status:** **BLOCKED / NOT_READY**.
  - **Reason:** Missing pre-compiled native binary for Node 24 (`better-sqlite3`), missing local embedding model weights, and unexpected external network polling for pricing. Under laboratory isolation rules, downloading large models or making external web calls is prohibited during benchmark execution.
